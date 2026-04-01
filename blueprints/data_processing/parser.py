import pandas as pd
import yaml
from pathlib import Path

# TODO: Allow to parse multiple data sources and multiple sheets within Excel files

DEFAULT_SHEET_NAME = "Retention rate RU & UAS"


def _parse_from_name_and_reader(filename, excel_reader, yaml_reader):
    lowered = filename.lower()

    if lowered.endswith(".xlsx"):
        df = excel_reader()
        return {
            "type": "xlsx",
            "data": df,
            "file_name": filename,
            "sheet_name": DEFAULT_SHEET_NAME,
        }

    if lowered.endswith((".yml", ".yaml")):
        data = yaml_reader()
        return {"type": "yaml", "data": data, "file_name": filename}

    raise ValueError("Unsupported file type")

def parse_file(file):
    return _parse_from_name_and_reader(
        filename=file.filename,
        excel_reader=lambda: pd.read_excel(file, sheet_name=DEFAULT_SHEET_NAME),
        yaml_reader=lambda: yaml.safe_load(file),
    )


def parse_path(file_path):
    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")

    return _parse_from_name_and_reader(
        filename=path.name,
        excel_reader=lambda: pd.read_excel(path, sheet_name=DEFAULT_SHEET_NAME),
        yaml_reader=lambda: yaml.safe_load(path.read_text(encoding="utf-8")),
    )
