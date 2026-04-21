import pandas as pd
import yaml
from io import BytesIO
from pathlib import Path

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
    workbook = pd.ExcelFile(excel_buffer)
    available_sheets = list(workbook.sheet_names)
    if not available_sheets:
        raise ValueError("Workbook has no sheets")

    target_sheet = selected_sheet or available_sheets[0]
    if target_sheet not in available_sheets:
        raise ValueError(f"Sheet '{target_sheet}' not found. Available sheets: {', '.join(available_sheets)}")

    dataframe = pd.read_excel(workbook, sheet_name=target_sheet)
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
