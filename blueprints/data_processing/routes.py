from flask import request, jsonify
from blueprints.data_processing.parser import parse_file
from blueprints.data_processing.normalizer import normalize_xlsx, normalize_yaml
from blueprints.data_processing.schema import detect_schema

from . import date_processing_bp

@date_processing_bp.route("/upload", methods=["POST"])
def upload():
    file = request.files["file"]

    parsed = parse_file(file)

    if parsed["type"] == "xlsx":
        records = normalize_xlsx(parsed["data"])
        schema = detect_schema(records)
    
        return jsonify({
            "schema": schema,
            "records": records
        })
    else:
        records = normalize_yaml(parsed["data"])
        return jsonify({
            "records": records
        })
