from flask import request, jsonify
import pandas as pd
from pathlib import Path
from typing import Any, Dict

from blueprints.data_processing.parser import parse_file, parse_path
from blueprints.data_processing.normalizer import normalize_xlsx, normalize_parsed_payload
from blueprints.data_processing.excel_utils import (
    parse_excel_range, apply_range_to_dataframe, get_range_preview,
    parse_multiple_excel_ranges, apply_multiple_ranges_to_dataframe
)

from . import date_processing_bp

DATA_STORAGE = {}
RAW_DATA_STORAGE = {}  # Store raw data for range operations
DATA_CONTEXT: Dict[str, Any] = {
    "file_type": None,
    "file_name": None,
    "source_path": None,
    "source_path_relative": None,
    "sheet_name": None,
    "range_applied": None,
}


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


def _build_data_context(parsed, source_path, source_path_relative):
    file_type = parsed["type"]
    return {
        "file_type": file_type,
        "file_name": parsed.get("file_name"),
        "source_path": source_path,
        "source_path_relative": source_path_relative,
        "sheet_name": parsed.get("sheet_name") if file_type == "xlsx" else None,
        "range_applied": None,
    }


def _upload_from_parsed_payload(parsed, source_path, source_path_relative):
    global DATA_STORAGE, RAW_DATA_STORAGE, DATA_CONTEXT

    normalized = normalize_parsed_payload(parsed)
    df = normalized["dataframe"]

    if parsed["type"] == "xlsx":
        RAW_DATA_STORAGE = parsed["data"]
    else:
        RAW_DATA_STORAGE = df

    DATA_CONTEXT = _build_data_context(parsed, source_path, source_path_relative)
    DATA_STORAGE = df

    response_data = {
        "type": normalized["type"],
        "columns": normalized["columns"],
        "preview": normalized["preview"],
        "row_count": normalized["row_count"],
        "source_path": source_path,
        "source_path_relative": source_path_relative,
    }

    if parsed["type"] == "xlsx":
        response_data["total_rows"] = len(RAW_DATA_STORAGE)
        response_data["total_cols"] = len(RAW_DATA_STORAGE.columns)

    return response_data

@date_processing_bp.route("/upload", methods=["POST"])
def upload():
    # load uploaded file from frontend
    file = request.files["file"]
    requested_source_path = request.form.get("source_path", "")
    source_path, source_path_relative = _normalize_source_path(requested_source_path)

    # parse the file data
    parsed = parse_file(file)
    response_data = _upload_from_parsed_payload(parsed, source_path, source_path_relative)
    return jsonify(response_data)


@date_processing_bp.route("/upload-from-path", methods=["POST"])
def upload_from_path():
    source_path_input = request.form.get("source_path", "")
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        source_path_input = payload.get("source_path", source_path_input)

    source_path, source_path_relative = _normalize_source_path(source_path_input)
    effective_path = source_path or source_path_relative
    if not effective_path:
        return jsonify({"error": "source_path is required"}), 400

    try:
        parsed = parse_path(effective_path)
        response_data = _upload_from_parsed_payload(parsed, source_path, source_path_relative)
        return jsonify(response_data)
    except Exception as exc:
        return jsonify({"error": f"Path upload failed: {str(exc)}"}), 400


@date_processing_bp.route("/apply-range", methods=["POST"])
def apply_range():
    """Apply Excel range selection to the uploaded XLSX data"""
    global DATA_STORAGE, RAW_DATA_STORAGE, DATA_CONTEXT
    
    if RAW_DATA_STORAGE is None or len(RAW_DATA_STORAGE) == 0:
        return jsonify({"error": "No Excel data uploaded"}), 400
    
    range_str = request.form.get("range", "").strip()
    
    if not range_str:
        return jsonify({"error": "Range parameter is required"}), 400
    
    try:
        # Check if multiple ranges (contains comma)
        if ',' in range_str:
            # Multiple ranges
            ranges = parse_multiple_excel_ranges(range_str)
            subset_df, excel_columns = apply_multiple_ranges_to_dataframe(RAW_DATA_STORAGE, ranges)
            
            # Calculate combined range info
            all_cols = []
            all_rows = []
            for r in ranges:
                all_cols.extend(range(r['start_col'], r['end_col'] + 1))
                all_rows.extend(range(r['start_row'], r['end_row'] + 1))
            
            min_col, max_col = min(all_cols), max(all_cols)
            min_row, max_row = min(all_rows), max(all_rows)
            
            range_display = f"Multiple ranges: {range_str}"
            total_cols = len(excel_columns)
            total_rows = len(subset_df)
            
        else:
            # Single range
            range_info = parse_excel_range(range_str)
            subset_df = apply_range_to_dataframe(RAW_DATA_STORAGE, range_info)
            range_display = f"{range_info['start_col_str']}{range_info['start_row_str']}:{range_info['end_col_str']}{range_info['end_row_str']}"
            total_cols = range_info['end_col'] - range_info['start_col'] + 1
            total_rows = range_info['end_row'] - range_info['start_row'] + 1
        
        # Normalize the subset
        normalized_df = normalize_xlsx(subset_df)
        
        # Update the global storage
        DATA_STORAGE = normalized_df
        DATA_CONTEXT = {**DATA_CONTEXT, "range_applied": range_str}
        
        # Generate preview
        preview = normalized_df.head(5).fillna("").to_dict(orient="records")
        
        return jsonify({
            "success": True,
            "range_applied": range_str,
            "columns": list(normalized_df.columns),
            "preview": preview,
            "row_count": len(normalized_df),
            "range_info": {
                "display": range_display,
                "total_rows": total_rows,
                "total_cols": total_cols
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Range application failed: {str(e)}"}), 400


def get_data_state_snapshot():
    dataframe = DATA_STORAGE if isinstance(DATA_STORAGE, pd.DataFrame) else pd.DataFrame()
    return {
        "source": dict(DATA_CONTEXT),
        "columns": list(dataframe.columns),
        "row_count": len(dataframe),
        "preview": dataframe.head(5).fillna("").to_dict(orient="records"),
    }


@date_processing_bp.route("/preview-range", methods=["POST"])
def preview_range():
    """Preview what data would be selected by an Excel range without applying it"""
    
    if RAW_DATA_STORAGE is None or len(RAW_DATA_STORAGE) == 0:
        return jsonify({"error": "No Excel data uploaded"}), 400
    
    range_str = request.form.get("range", "").strip()
    
    if not range_str:
        return jsonify({"error": "Range parameter is required"}), 400
    
    try:
        # Check if multiple ranges (contains comma)
        if ',' in range_str:
            # Multiple ranges
            ranges = parse_multiple_excel_ranges(range_str)
            subset_df, excel_col_letters = apply_multiple_ranges_to_dataframe(RAW_DATA_STORAGE, ranges)
            
            if subset_df.empty:
                return jsonify({
                    "success": True,
                    "preview": [],
                    "excel_columns": [],
                    "range_info": {
                        "display": f"Multiple ranges: {range_str}",
                        "total_rows": 0,
                        "total_cols": 0
                    }
                })
            
            # Get preview (first 5 rows)
            preview_df = subset_df.head(5).fillna("")
            
            # Create display column names
            display_columns = []
            original_to_display_mapping = {}
            actual_columns = list(preview_df.columns)
            
            for i, col_name in enumerate(actual_columns):
                excel_col = excel_col_letters[i] if i < len(excel_col_letters) else f"Col{i+1}"
                
                if str(col_name).startswith("Unnamed:") or pd.isna(col_name) or str(col_name).strip() == "":
                    display_name = f"({excel_col})"
                else:
                    display_name = f"{col_name} ({excel_col})"
                
                display_columns.append(display_name)
                original_to_display_mapping[col_name] = display_name
            
            # Rename columns
            preview_df_renamed = preview_df.rename(columns=original_to_display_mapping)
            preview = preview_df_renamed.to_dict(orient="records")
            
            return jsonify({
                "success": True,
                "preview": preview,
                "excel_columns": display_columns,
                "range_info": {
                    "display": f"Multiple ranges: {range_str}",
                    "total_rows": len(subset_df),
                    "total_cols": len(actual_columns)
                }
            })
            
        else:
            # Single range
            range_info = parse_excel_range(range_str)
            subset_df = apply_range_to_dataframe(RAW_DATA_STORAGE, range_info)
            
            # Get preview (first 5 rows)
            preview_df = subset_df.head(5).fillna("")
            
            # Create display column names showing original names with Excel mapping in brackets
            display_columns = []
            original_to_display_mapping = {}
            
            # Use the actual number of columns in the subset, not the range calculation
            actual_columns = list(preview_df.columns)
            
            for i, col_idx in enumerate(range(range_info['start_col'], range_info['end_col'] + 1)):
                # Make sure we don't exceed the actual number of columns
                if i >= len(actual_columns):
                    break
                    
                from blueprints.data_processing.excel_utils import number_to_excel_column
                excel_col = number_to_excel_column(col_idx)
                original_col_name = str(actual_columns[i])
                
                # Check if column is unnamed (starts with "Unnamed:" or similar)
                if original_col_name.startswith("Unnamed:") or pd.isna(actual_columns[i]) or original_col_name.strip() == "":
                    display_name = f"({excel_col})"
                else:
                    display_name = f"{original_col_name} ({excel_col})"
                
                display_columns.append(display_name)
                original_to_display_mapping[actual_columns[i]] = display_name
            
            # Rename columns to show original names with Excel mapping
            preview_df_renamed = preview_df.rename(columns=original_to_display_mapping)
            preview = preview_df_renamed.to_dict(orient="records")
            
            return jsonify({
                "success": True,
                "preview": preview,
                "excel_columns": display_columns,
                "range_info": {
                    "start_cell": f"{range_info['start_col_str']}{range_info['start_row_str']}",
                    "end_cell": f"{range_info['end_col_str']}{range_info['end_row_str']}",
                    "total_rows": range_info['end_row'] - range_info['start_row'] + 1,
                    "total_cols": range_info['end_col'] - range_info['start_col'] + 1
                }
            })
        
    except Exception as e:
        return jsonify({"error": f"Range preview failed: {str(e)}"}), 400
