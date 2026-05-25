from flask import (
    jsonify,
    render_template,
    request,
)
from datetime import datetime
from pathlib import Path
import json
import os
import re
import importlib
from io import BytesIO

from . import core_bp
from blueprints.core.config import CHART_TYPES
import blueprints.data_processing.routes as data_routes
import blueprints.plots.routes as plot_routes

TEMPLATE_STORAGE_DIR = Path(__file__).resolve().parents[2] / "saved_templates"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "generated_reports"
CHART_PLACEHOLDER_PATTERN = re.compile(r"\{\{CHART:([A-Za-z0-9_-]+)\}\}")

@core_bp.route("/", methods=['GET'])
def init_main():
    return render_template(
        "main_template.html",
        chart_types=CHART_TYPES
    )


def _slugify_template_name(name):
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", (name or "").strip())
    clean_name = re.sub(r"_+", "_", clean_name).strip("_")
    return clean_name or f"template_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


def _template_path(template_name):
    safe_name = _slugify_template_name(template_name)
    return TEMPLATE_STORAGE_DIR / f"{safe_name}.json", safe_name


def _build_application_state():
    return {
        "saved_at": datetime.utcnow().isoformat() + "Z",
        "data": data_routes.get_data_state_snapshot(),
        "chart": plot_routes.get_chart_state_snapshot(),
    }


def _paragraphs_in_tables(tables):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph
                yield from _paragraphs_in_tables(cell.tables)


def _all_docx_paragraphs(document):
    for paragraph in document.paragraphs:
        yield paragraph
    yield from _paragraphs_in_tables(document.tables)


def _replace_chart_placeholders(document, image_map, image_width_inches=6.5):
    docx_shared = importlib.import_module("docx.shared")
    inches_ctor = getattr(docx_shared, "Inches")

    replaced = []
    used_keys = []
    missing_images = []

    for paragraph in _all_docx_paragraphs(document):
        text = paragraph.text or ""
        matches = CHART_PLACEHOLDER_PATTERN.findall(text)
        if not matches:
            continue

        new_text = text
        for key in matches:
            token = f"{{{{CHART:{key}}}}}"
            new_text = new_text.replace(token, "")
        paragraph.text = new_text

        for key in matches:
            image_path = image_map.get(key)
            if not image_path:
                missing_images.append(key)
                continue
            paragraph.add_run().add_picture(image_path, width=inches_ctor(image_width_inches))
            replaced.append({"chart_key": key, "image_path": image_path})
            used_keys.append(key)

    return {
        "replaced": replaced,
        "used_keys": used_keys,
        "missing_images": sorted(set(missing_images)),
    }


@core_bp.route("/create_template", methods=['POST'])
def create_template():
    template_name = request.form.get("template_name")
    if request.is_json:
        json_payload = request.get_json(silent=True) or {}
        template_name = json_payload.get("template_name", template_name)

    template_path, safe_name = _template_path(template_name)
    TEMPLATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    state = _build_application_state()
    with open(template_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)

    return jsonify({
        "success": True,
        "template_name": safe_name,
        "path": str(template_path),
        "saved_at": state["saved_at"],
    })


@core_bp.route("/templates", methods=['GET'])
def list_templates():
    TEMPLATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    templates = sorted(path.stem for path in TEMPLATE_STORAGE_DIR.glob("*.json"))
    return jsonify({"templates": templates})


@core_bp.route("/load_template", methods=['GET'])
def load_template():
    template_name = request.args.get("template_name", "")
    if not template_name:
        return jsonify({"error": "template_name is required"}), 400

    template_path, safe_name = _template_path(template_name)
    if not template_path.exists():
        return jsonify({"error": f"Saved configuration '{safe_name}' not found"}), 404

    with open(template_path, "r", encoding="utf-8") as handle:
        state = json.load(handle)

    return jsonify({"success": True, "template_name": safe_name, "state": state})


@core_bp.route("/report/generate-docx", methods=["POST"])
def generate_docx_report():
    try:
        docx_module = importlib.import_module("docx")
        Document = getattr(docx_module, "Document")
    except ModuleNotFoundError:
        return jsonify({"error": "python-docx is not installed. Run: pip install python-docx"}), 500

    docx_file = request.files.get("docx_template")
    docx_template_path = request.form.get("docx_template_path", "").strip()
    output_name = request.form.get("output_name", "").strip()

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        docx_template_path = payload.get("docx_template_path", docx_template_path)
        output_name = payload.get("output_name", output_name)

    if not docx_file and not docx_template_path:
        return jsonify({"error": "Provide docx_template file or docx_template_path"}), 400

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    png_dir = REPORTS_DIR / timestamp
    png_dir.mkdir(parents=True, exist_ok=True)

    # Interpret output_name: full path (contains separator) vs plain name vs empty
    is_path = output_name and (os.sep in output_name or '/' in output_name)
    if is_path:
        p = Path(output_name).expanduser().resolve()
        if p.suffix.lower() == '.docx':
            output_dest = p.parent
            explicit_stem = p.stem
        else:
            output_dest = p
            explicit_stem = None
    else:
        if docx_template_path:
            output_dest = Path(docx_template_path).expanduser().resolve().parent
        else:
            output_dest = REPORTS_DIR / timestamp
        explicit_stem = _slugify_template_name(output_name) if output_name else None

    output_dest.mkdir(parents=True, exist_ok=True)

    try:
        export_result = plot_routes.export_charts_to_pngs(output_root=png_dir / "charts")
    except Exception as exc:
        return jsonify({"error": f"Chart export failed: {str(exc)}"}), 400

    image_map = export_result.get("image_map", {})
    if not image_map:
        return jsonify({"error": "No chart images available for report generation", "export": export_result}), 400

    try:
        if docx_file:
            document = Document(BytesIO(docx_file.read()))
            template_stem = Path(docx_file.filename or "report_template.docx").stem
        else:
            template_path = Path(docx_template_path).expanduser().resolve()
            if not template_path.exists() or not template_path.is_file():
                return jsonify({"error": f"DOCX template not found: {template_path}"}), 404
            document = Document(str(template_path))
            template_stem = template_path.stem
    except Exception as exc:
        return jsonify({"error": f"Failed to read DOCX template: {str(exc)}"}), 400

    replace_result = _replace_chart_placeholders(document, image_map)
    used_keys = set(replace_result["used_keys"])
    exported_keys = set(image_map.keys())
    missing_placeholders = sorted(exported_keys - used_keys)

    safe_output_name = explicit_stem or f"{_slugify_template_name(template_stem)}_generated_{timestamp}"
    output_path = output_dest / f"{safe_output_name}.docx"

    try:
        document.save(str(output_path))
    except Exception as exc:
        return jsonify({"error": f"Failed to save generated DOCX: {str(exc)}"}), 400

    return jsonify(
        {
            "success": True,
            "output_docx_path": str(output_path),
            "report_dir": str(png_dir),
            "replaced": replace_result["replaced"],
            "missing_images": replace_result["missing_images"],
            "missing_placeholders": missing_placeholders,
            "export": {
                "output_dir": export_result.get("output_dir"),
                "exported": export_result.get("exported", []),
                "warnings": export_result.get("warnings", []),
                "errors": export_result.get("errors", []),
            },
        }
    )
