from flask import request, jsonify
import pandas as pd
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


def _normalize_source_path(source_path):
    if not source_path:
        return None, None

    raw = source_path.strip()
    if not raw:
        return None, None

    candidate = Path(raw).expanduser()
    if candidate.is_absolute() or raw.startswith(("./", "../", "~/")):
        absolute_path = candidate.resolve() if candidate.is_absolute() else (Path.cwd() / candidate).resolve()
        try:
            relative_path = str(absolute_path.relative_to(Path.cwd()))
        except ValueError:
            relative_path = None
        return str(absolute_path), relative_path

    return None, raw


def _get_source(source_id):
    source = SOURCES.get(source_id)
    if source is None:
        raise KeyError(f"Unknown source_id: {source_id}")
    return source


def _build_source_payload(source_id, source):
    normalized_df = source["normalized_df"]
    payload = {
        "source_id": source_id,
        "file_type": source["file_type"],
        "file_name": source.get("file_name"),
        "sheet_name": source.get("sheet_name"),
        "available_sheets": source.get("available_sheets", []),
        "source_path": source.get("source_path"),
        "source_path_relative": source.get("source_path_relative"),
        "columns": list(normalized_df.columns),
        "row_count": len(normalized_df),
        "preview": normalized_df.head(5).fillna("").to_dict(orient="records"),
    }
    if source["file_type"] == "xlsx":
        payload["total_rows"] = len(source["raw_df"])
        payload["total_cols"] = len(source["raw_df"].columns)
    return payload


def _register_parsed_source(parsed, source_path, source_path_relative, source_id=None):
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
        "source_path": source_path,
        "source_path_relative": source_path_relative,
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
                "source_path_relative": source.get("source_path_relative"),
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
    source_path, source_path_relative = _normalize_source_path(requested_source_path)

    parsed = parse_file(file, sheet_name=sheet_name)
    payload = _register_parsed_source(parsed, source_path, source_path_relative, source_id=source_id)
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

    source_path, source_path_relative = _normalize_source_path(source_path_input)
    effective_path = source_path or source_path_relative
    if not effective_path:
        return jsonify({"error": "source_path is required"}), 400

    try:
        parsed = parse_path(effective_path, sheet_name=sheet_name)
        payload = _register_parsed_source(parsed, source_path, source_path_relative, source_id=source_id)
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
            source.get("source_path"),
            source.get("source_path_relative"),
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

    try:
        subset_df = get_dataframe_for_chart(source_id, range_str)
        preview_df = subset_df.head(5).fillna("")
        return jsonify(
            {
                "success": True,
                "preview": preview_df.to_dict(orient="records"),
                "excel_columns": [str(col) for col in preview_df.columns],
                "range_info": {
                    "display": range_str,
                    "total_rows": len(subset_df),
                    "total_cols": len(subset_df.columns),
                },
            }
        )
    except Exception as exc:
        return jsonify({"error": f"Range preview failed: {str(exc)}"}), 400
