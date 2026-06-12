import pandas as pd
import yaml
from io import BytesIO
from pathlib import Path


def _format_excel_read_error(exc):
    message = str(exc)
    lowered = message.lower()

    if "not a zip file" in lowered or ("zip" in lowered and "not" in lowered and "archiv" in lowered):
        return ValueError(
            "File is not a valid .xlsx workbook. If this is an older .xls file, a CSV, "
            "or a corrupted download, open it in Excel and save as .xlsx, then try again."
        )

    if "not supported between instances of 'int' and 'str'" in message:
        return ValueError(
            "Could not read the Excel file because of inconsistent cell types in the sheet. "
            "Try re-saving the file from Excel or narrowing the selected range."
        )

    return exc


def _parse_from_name_and_reader(filename, excel_reader, yaml_reader, sheet_name=None):
    lowered = filename.lower()

    if lowered.endswith(".xlsx"):
        df, selected_sheet, available_sheets = excel_reader(sheet_name)
        return {
            "type": "xlsx",
            "data": df,
            "file_name": filename,
            "sheet_name": selected_sheet,
            "available_sheets": available_sheets,
        }

    if lowered.endswith((".yml", ".yaml")):
        data = yaml_reader()
        return {"type": "yaml", "data": data, "file_name": filename}

    raise ValueError("Unsupported file type")

def _read_excel_from_bytes(content_bytes, selected_sheet=None):
    excel_buffer = BytesIO(content_bytes)
    try:
        workbook = pd.ExcelFile(excel_buffer)
    except Exception as exc:
        raise _format_excel_read_error(exc) from exc

    available_sheets = list(workbook.sheet_names)
    if not available_sheets:
        raise ValueError("Workbook has no sheets")

    target_sheet = selected_sheet or available_sheets[0]
    if target_sheet not in available_sheets:
        raise ValueError(f"Sheet '{target_sheet}' not found. Available sheets: {', '.join(available_sheets)}")

    try:
        dataframe = pd.read_excel(workbook, sheet_name=target_sheet, header=None)
    except Exception as exc:
        raise _format_excel_read_error(exc) from exc

    return dataframe, target_sheet, available_sheets


def parse_file(file, sheet_name=None):
    filename = file.filename
    lowered = filename.lower()

    if lowered.endswith(".xlsx"):
        content_bytes = file.read()
        parsed = _parse_from_name_and_reader(
            filename=filename,
            excel_reader=lambda selected_sheet: _read_excel_from_bytes(content_bytes, selected_sheet),
            yaml_reader=lambda: None,
            sheet_name=sheet_name,
        )
        parsed["content_bytes"] = content_bytes
        return parsed

    return _parse_from_name_and_reader(
        filename=filename,
        excel_reader=lambda selected_sheet: _read_excel_from_bytes(file.read(), selected_sheet),
        yaml_reader=lambda: yaml.safe_load(file),
        sheet_name=sheet_name,
    )


def parse_path(file_path, sheet_name=None):
    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    lowered = path.name.lower()
    if lowered.endswith(".xlsx"):
        content_bytes = path.read_bytes()
        return _parse_from_name_and_reader(
            filename=path.name,
            excel_reader=lambda selected_sheet: _read_excel_from_bytes(content_bytes, selected_sheet),
            yaml_reader=lambda: None,
            sheet_name=sheet_name,
        )

    return _parse_from_name_and_reader(
        filename=path.name,
        excel_reader=lambda selected_sheet: _read_excel_from_bytes(path.read_bytes(), selected_sheet),
        yaml_reader=lambda: yaml.safe_load(path.read_text(encoding="utf-8")),
        sheet_name=sheet_name,
    )


def parse_excel_bytes(content_bytes, file_name, sheet_name=None):
    return _parse_from_name_and_reader(
        filename=file_name,
        excel_reader=lambda selected_sheet: _read_excel_from_bytes(content_bytes, selected_sheet),
        yaml_reader=lambda: None,
        sheet_name=sheet_name,
    )
