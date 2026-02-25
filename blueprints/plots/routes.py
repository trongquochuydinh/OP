from flask import request, jsonify
import json
from . import plots_bp
from blueprints.plots.builder import build_chart
import blueprints.data_processing.routes as data_routes

@plots_bp.post("/generate")
def generate():

    if data_routes.DATA_STORAGE is None:
        return jsonify({"error": "No dataset uploaded"}), 400

    df = data_routes.DATA_STORAGE
    columns = json.loads(request.form.get("columns", "[]"))
    chart_type = request.form["chart_type"]
    title = request.form.get("title", "Title")

    try:
        traces, layout = build_chart(chart_type, df, columns, title)

        return jsonify({
            "traces": traces,
            "layout": layout
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

