from flask import json, request, jsonify
from . import plots_bp
from blueprints.plots.builder import build_chart

@plots_bp.post("/generate")
def generate():

    records = json.loads(request.form["records"])
    column = request.form.get("column")
    chart_type = request.form["chart_type"]
    title = request.form.get("title", "Title")

    try:
        traces, layout = build_chart(chart_type, records, column, title)

        return jsonify({
            "traces": traces,
            "layout": layout
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400
