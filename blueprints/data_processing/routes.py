from flask import request, jsonify
import pandas as pd

from blueprints.data_processing.parser import parse_file
from blueprints.data_processing.normalizer import normalize_yaml, normalize_xlsx

from . import date_processing_bp

DATA_STORAGE = {}

@date_processing_bp.route("/upload", methods=["POST"])
def upload():
    global DATA_STORAGE

    # load uploaded file from frontend
    file = request.files["file"]

    # parse the file data
    parsed = parse_file(file)

    if parsed["type"] == "xlsx":
        df = normalize_xlsx(parsed["data"])

    else:
        records = normalize_yaml(parsed["data"])
        df = pd.DataFrame(records)

    # define preview of the 
    preview = df.head(5).fillna("").to_dict(orient="records")

    # save the file data into a global variable -> avoid loading the file multiple times
    DATA_STORAGE = df

    return jsonify({
        "type": parsed["type"],
        "columns": list(df.columns),
        "preview": preview,
        "row_count": len(df)
    })

