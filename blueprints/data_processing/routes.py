from flask import request, jsonify
from pathlib import Path
from typing import Any, Dict
import uuid

from blueprints.data_processing.parser import parse_excel_bytes, parse_file, parse_path
from blueprints.data_processing.normalizer import normalize_xlsx, normalize_parsed_payload
from blueprints.data_processing.excel_utils import (
    apply_multiple_ranges_to_dataframe,
    apply_range_to_dataframe,
    parse_excel_range,
    parse_multiple_excel_ranges,
)

from . import date_processing_bp

SOURCES: Dict[str, Dict[str, Any]] = {}
ACTIVE_SOURCE_ID = None

PIE_STYLE_MAX_SLICES = 100


def _pie_style_meta(subset_df):
    """Slice count and labels for pie styling UI (matches build_chart frequency / two-col pie order)."""
    try:
        if subset_df is None or getattr(subset_df, "empty", True):
            return {"slice_count": 0, "slice_labels": []}
        cols = list(subset_df.columns)
        if not cols:
            return {"slice_count": 0, "slice_labels": []}
        if len(cols) >= 2:
            c0, c1 = cols[0], cols[1]
            df2 = subset_df[[c0, c1]].dropna(how="any")
            labels = df2[c0].astype(str).tolist()
        else:
            c0 = cols[0]
            vc = subset_df[c0].dropna().value_counts()
            labels = vc.index.astype(str).tolist()
        n = len(labels)
        if n == 0:
            return {"slice_count": 0, "slice_labels": []}
        cap = min(n, PIE_STYLE_MAX_SLICES)
        return {"slice_count": cap, "slice_labels": labels[:cap]}
    except Exception:
        return {"slice_count": 0, "slice_labels": []}


def _normalize_source_path(source_path):
    if not source_path:
        return {
            "path_mode": None,
            "path_value": None,
            "source_path": None,
            "source_path_relative": None,
        }

    raw = source_path.strip()
    if not raw:
        return {
            "path_mode": None,
            "path_value": None,
            "source_path": None,
            "source_path_relative": None,
        }

    candidate = Path(raw).expanduser()
    workspace_root = Path.cwd().resolve()
    absolute_path = candidate.resolve() if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
    try:
        relative_path = str(absolute_path.relative_to(workspace_root))
    except ValueError:
        relative_path = None

    # Desktop-first contract: canonical persistence always stores absolute path.
    return {
        "path_mode": "absolute",
        "path_value": str(absolute_path),
        "source_path": str(absolute_path),
        "source_path_relative": relative_path,
    }


def _resolve_effective_source_path(explicit_source_path, path_mode, path_value, source_path, source_path_relative):
    explicit = (explicit_source_path or "").strip()
    if explicit:
        return str(Path(explicit).expanduser().resolve())

    mode = (path_mode or "").strip().lower()
    value = (path_value or "").strip()
    if mode == "absolute" and value:
        return str(Path(value).expanduser().resolve())

    canonical_saved = (source_path or "").strip()
    if canonical_saved:
        return str(Path(canonical_saved).expanduser().resolve())

    # Compatibility fallback for older template snapshots.
    if mode == "relative" and value:
        return str((Path.cwd() / Path(value)).resolve())
    if source_path_relative:
        return str((Path.cwd() / Path(source_path_relative)).resolve())
    return None


def _get_source(source_id):
    source = SOURCES.get(source_id)
    if source is None:
        raise KeyError(f"Unknown source_id: {source_id}")
    return source


def _build_source_payload(source_id, source):
    normalized_df = source["normalized_df"]
    canonical_path = source.get("source_path")
    payload = {
        "source_id": source_id,
        "file_type": source["file_type"],
        "file_name": source.get("file_name"),
        "sheet_name": source.get("sheet_name"),
        "available_sheets": source.get("available_sheets", []),
        "source_path": canonical_path,
        "source_path_canonical": canonical_path,
        "source_path_relative": source.get("source_path_relative"),
        "path_mode": source.get("path_mode"),
        "path_value": source.get("path_value"),
        "columns": list(normalized_df.columns),
        "row_count": len(normalized_df),
        "preview": normalized_df.head(5).fillna("").to_dict(orient="records"),
    }
    if source["file_type"] == "xlsx":
        payload["total_rows"] = len(source["raw_df"])
        payload["total_cols"] = len(source["raw_df"].columns)
    return payload


def _register_parsed_source(parsed, path_metadata, source_id=None):
    global ACTIVE_SOURCE_ID

    normalized = normalize_parsed_payload(parsed)
    normalized_df = normalized["dataframe"]

    file_type = parsed["type"]
    if file_type == "xlsx":
        raw_df = parsed["data"]
    else:
        raw_df = normalized_df

    source_id = source_id or str(uuid.uuid4())
    SOURCES[source_id] = {
        "file_type": file_type,
        "file_name": parsed.get("file_name"),
        "sheet_name": parsed.get("sheet_name") if file_type == "xlsx" else None,
        "available_sheets": parsed.get("available_sheets", []) if file_type == "xlsx" else [],
        "source_path": path_metadata.get("source_path"),
        "source_path_relative": path_metadata.get("source_path_relative"),
        "path_mode": path_metadata.get("path_mode"),
        "path_value": path_metadata.get("path_value"),
        "raw_df": raw_df,
        "normalized_df": normalized_df,
        "content_bytes": parsed.get("content_bytes") if file_type == "xlsx" else None,
    }
    ACTIVE_SOURCE_ID = source_id
    return _build_source_payload(source_id, SOURCES[source_id])


def get_dataframe_for_chart(source_id, range_str=None):
    source = _get_source(source_id)
    if source["file_type"] != "xlsx":
        return source["normalized_df"]

    if not range_str:
        return source["normalized_df"]

    if "," in range_str:
        ranges = parse_multiple_excel_ranges(range_str)
        subset_df, _ = apply_multiple_ranges_to_dataframe(source["raw_df"], ranges)
    else:
        range_info = parse_excel_range(range_str)
        subset_df = apply_range_to_dataframe(source["raw_df"], range_info)

    return normalize_xlsx(subset_df)


def get_data_state_snapshot():
    return {
        "active_source_id": ACTIVE_SOURCE_ID,
        "sources": [
            {
                "source_id": source_id,
                "file_type": source.get("file_type"),
                "file_name": source.get("file_name"),
                "sheet_name": source.get("sheet_name"),
                "available_sheets": source.get("available_sheets", []),
                "source_path": source.get("source_path"),
                "source_path_canonical": source.get("source_path"),
                "source_path_relative": source.get("source_path_relative"),
                "path_mode": source.get("path_mode"),
                "path_value": source.get("path_value"),
            }
            for source_id, source in SOURCES.items()
        ],
    }


@date_processing_bp.route("/sources/upload", methods=["POST"])
@date_processing_bp.route("/upload", methods=["POST"])
def upload_source():
    file = request.files["file"]
    requested_source_path = request.form.get("source_path", "")
    sheet_name = request.form.get("sheet_name") or None
    source_id = request.form.get("source_id") or None
    path_metadata = _normalize_source_path(requested_source_path)

    parsed = parse_file(file, sheet_name=sheet_name)
    payload = _register_parsed_source(parsed, path_metadata, source_id=source_id)
    return jsonify(payload)


@date_processing_bp.route("/sources/load-path", methods=["POST"])
@date_processing_bp.route("/upload-from-path", methods=["POST"])
def load_source_from_path():
    source_path_input = request.form.get("source_path", "")
    sheet_name = request.form.get("sheet_name") or None
    source_id = request.form.get("source_id") or None
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        source_path_input = payload.get("source_path", source_path_input)
        sheet_name = payload.get("sheet_name", sheet_name)
        source_id = payload.get("source_id", source_id)

    path_mode = request.form.get("path_mode", "")
    path_value = request.form.get("path_value", "")
    source_path_saved = request.form.get("source_path_saved", "")
    source_path_relative_saved = request.form.get("source_path_relative_saved", "")

    if request.is_json:
        payload = request.get_json(silent=True) or {}
        path_mode = payload.get("path_mode", path_mode)
        path_value = payload.get("path_value", path_value)
        source_path_saved = payload.get("source_path_saved", source_path_saved)
        source_path_relative_saved = payload.get("source_path_relative_saved", source_path_relative_saved)

    normalized = _normalize_source_path(source_path_input)
    if not normalized.get("path_value") and path_value:
        normalized = {
            "path_mode": path_mode or None,
            "path_value": path_value or None,
            "source_path": source_path_saved or None,
            "source_path_relative": source_path_relative_saved or None,
        }

    effective_path = _resolve_effective_source_path(
        source_path_input,
        normalized.get("path_mode"),
        normalized.get("path_value"),
        normalized.get("source_path"),
        normalized.get("source_path_relative"),
    )
    if not effective_path:
        return jsonify({"error": "source_path is required"}), 400

    try:
        parsed = parse_path(effective_path, sheet_name=sheet_name)
        if not normalized.get("path_value"):
            normalized = _normalize_source_path(effective_path)
        payload = _register_parsed_source(parsed, normalized, source_id=source_id)
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"Path load failed: {str(exc)}"}), 400


@date_processing_bp.route("/sources/select-sheet", methods=["POST"])
def select_source_sheet():
    source_id = request.form.get("source_id", "")
    sheet_name = request.form.get("sheet_name", "")
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        source_id = payload.get("source_id", source_id)
        sheet_name = payload.get("sheet_name", sheet_name)

    if not source_id:
        return jsonify({"error": "source_id is required"}), 400
    if not sheet_name:
        return jsonify({"error": "sheet_name is required"}), 400

    try:
        source = _get_source(source_id)
    except KeyError:
        return jsonify({"error": "Unknown source_id"}), 404

    if source.get("file_type") != "xlsx":
        return jsonify({"error": "Sheet selection is only available for xlsx sources"}), 400

    try:
        if source.get("content_bytes"):
            reparsed = parse_excel_bytes(source["content_bytes"], source.get("file_name") or "uploaded.xlsx", sheet_name=sheet_name)
            reparsed["content_bytes"] = source["content_bytes"]
        else:
            effective_path = source.get("source_path") or source.get("source_path_relative")
            if not effective_path:
                return jsonify({"error": "Cannot change sheet without source path"}), 400
            reparsed = parse_path(effective_path, sheet_name=sheet_name)

        payload = _register_parsed_source(
            reparsed,
            {
                "path_mode": source.get("path_mode"),
                "path_value": source.get("path_value"),
                "source_path": source.get("source_path"),
                "source_path_relative": source.get("source_path_relative"),
            },
            source_id=source_id,
        )
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"Sheet selection failed: {str(exc)}"}), 400


@date_processing_bp.route("/sources", methods=["GET"])
def list_sources():
    sources = [
        _build_source_payload(source_id, source)
        for source_id, source in SOURCES.items()
    ]
    return jsonify({"active_source_id": ACTIVE_SOURCE_ID, "sources": sources})


@date_processing_bp.route("/sources/reset", methods=["POST"])
def reset_sources():
    global ACTIVE_SOURCE_ID
    SOURCES.clear()
    ACTIVE_SOURCE_ID = None
    return jsonify({"success": True})


@date_processing_bp.route("/preview-range", methods=["POST"])
def preview_range():
    source_id = request.form.get("source_id", "")
    range_str = request.form.get("range", "").strip()
    payload = {}
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        source_id = payload.get("source_id", source_id)
        range_str = payload.get("range", range_str)

    if not source_id:
        return jsonify({"error": "source_id is required"}), 400

    try:
        source = _get_source(source_id)
    except KeyError:
        return jsonify({"error": "Unknown source_id"}), 404

    if source["file_type"] != "xlsx":
        return jsonify({"error": "Range preview is only supported for xlsx sources"}), 400

    if not range_str:
        return jsonify({"error": "Range parameter is required"}), 400

    max_rows = 500
    max_cols = 50
    try:
        max_rows = min(int(payload.get("max_rows", max_rows)), 2000)
        max_cols = min(int(payload.get("max_cols", max_cols)), 200)
    except (TypeError, ValueError):
        max_rows = 500
        max_cols = 50

    try:
        subset_df = get_dataframe_for_chart(source_id, range_str)
        total_rows = len(subset_df)
        total_cols = len(subset_df.columns)
        excel_columns = [str(col) for col in subset_df.columns]
        row_slice = min(total_rows, max_rows)
        col_slice = min(total_cols, max_cols)
        preview_df = subset_df.iloc[:row_slice, :col_slice].fillna("")
        pie_style = _pie_style_meta(subset_df)
        return jsonify(
            {
                "success": True,
                "preview": preview_df.to_dict(orient="records"),
                "excel_columns": excel_columns,
                "pie_style": pie_style,
                "range_info": {
                    "display": range_str,
                    "total_rows": total_rows,
                    "total_cols": total_cols,
                },
                "truncation": {
                    "rows_truncated": total_rows > row_slice,
                    "cols_truncated": total_cols > col_slice,
                    "preview_rows": row_slice,
                    "preview_cols": col_slice,
                    "max_rows": max_rows,
                    "max_cols": max_cols,
                },
            }
        )
    except Exception as exc:
        return jsonify({"error": f"Range preview failed: {str(exc)}"}), 400
