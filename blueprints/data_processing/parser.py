import pandas as pd
import yaml
import os

def parse_file(file):
    filename = file.filename.lower()

    if filename.endswith(".xlsx"):
        df = pd.read_excel(file)
        return {"type": "xlsx", "data": df}

    elif filename.endswith((".yml", ".yaml")):
        data = yaml.safe_load(file)
        return {"type": "yaml", "data": data}

    else:
        raise ValueError("Unsupported file type")
