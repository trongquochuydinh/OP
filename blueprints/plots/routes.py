from flask import request, jsonify
import json
from . import plots_bp
from blueprints.plots.builder import build_chart
import blueprints.data_processing.routes as data_routes

CHART_STATE = {
    "chart_type": None,
    "columns": [],
    "title": "",
    "layout": {},
}

@plots_bp.post("/generate")
def generate():
    global CHART_STATE

    if data_routes.DATA_STORAGE is None:
        return jsonify({"error": "No dataset uploaded"}), 400

    df = data_routes.DATA_STORAGE
    columns = json.loads(request.form.get("columns", "[]"))
    chart_type = request.form["chart_type"]
    title = request.form.get("title", "Title")

    try:
        traces, layout = build_chart(chart_type, df, columns, title)

        CHART_STATE = {
            "chart_type": chart_type,
            "columns": columns,
            "title": title,
            "layout": layout,
        }

        return jsonify({
            "traces": traces,
            "layout": layout
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@plots_bp.post("/new_chart")
def new_chart():
    # TODO: Implement the logic for creating a new chart
    # Maybe a class for each chart that can store its own state and be manipulated independently of other charts?
    # This will allow the user to manage multiple charts independently, including saving and loading their configurations, and applying different templates to each chart.
    return jsonify({"error": "Not implemented yet"}), 501


def get_chart_state_snapshot():
    return dict(CHART_STATE)
