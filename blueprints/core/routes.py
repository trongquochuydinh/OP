from flask import (
    jsonify,
    render_template,
    request,
)
from datetime import datetime
from pathlib import Path
import json
import re

from . import core_bp
from blueprints.core.config import CHART_TYPES
import blueprints.data_processing.routes as data_routes
import blueprints.plots.routes as plot_routes

TEMPLATE_STORAGE_DIR = Path(__file__).resolve().parents[2] / "saved_templates"

# TODO: Parse all the elements of the template and apply them to the current state of the application, including data, chart types, and layout configurations.
#   1) I need to remember which chart types were selected
#   2) I need to remember the adjustments made to the layout (e.g., title, axis labels, colors)
#   3) I need to remember the data sources (path to the source and which sheet was used if it's an Excel file)

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


# TODO: Allow to take the current state of the application and save it as a template for future use.
@core_bp.route("/create_template", methods=['POST'])
def create_template():
    template_name = request.form.get("template_name")
    source_path = request.form.get("source_path", "")
    if request.is_json:
        json_payload = request.get_json(silent=True) or {}
        template_name = json_payload.get("template_name", template_name)
        source_path = json_payload.get("source_path", source_path)

    template_path, safe_name = _template_path(template_name)
    TEMPLATE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    state = _build_application_state()
    if source_path:
        current_source = state.setdefault("data", {}).setdefault("source", {})
        current_source["source_path"] = source_path
        current_source["source_path_relative"] = source_path
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


# TODO: Allow users to load a previously saved template and apply it to the current data or visualization.
@core_bp.route("/load_template", methods=['GET'])
def load_template():
    template_name = request.args.get("template_name", "")
    if not template_name:
        return jsonify({"error": "template_name is required"}), 400

    template_path, safe_name = _template_path(template_name)
    if not template_path.exists():
        return jsonify({"error": f"Template '{safe_name}' not found"}), 404

    with open(template_path, "r", encoding="utf-8") as handle:
        state = json.load(handle)

    return jsonify({"success": True, "template_name": safe_name, "state": state})
