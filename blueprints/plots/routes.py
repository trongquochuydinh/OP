from flask import request, jsonify
import uuid
import json
from . import plots_bp
from blueprints.plots.builder import build_chart
import blueprints.data_processing.routes as data_routes

CHART_STATE = {
    "active_chart_id": None,
    "charts": [],
}


def _render_chart_config(df, chart_config):
    traces, layout = build_chart(
        chart_config["chart_type"],
        df,
        chart_config["columns"],
        chart_config.get("title", ""),
    )
    return traces, layout


def _render_from_source(chart_config):
    source_id = chart_config.get("source_id")
    range_str = chart_config.get("range")
    if not source_id:
        raise ValueError("source_id is required")

    df = data_routes.get_dataframe_for_chart(source_id, range_str)
    if df is None or len(df) == 0:
        raise ValueError("No rows available for selected source/range")

    columns = chart_config.get("columns") or list(df.columns)
    if not columns:
        raise ValueError("No columns available to render chart")

    missing_columns = [col for col in columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Columns not found in source data: {missing_columns}")

    column_labels = chart_config.get("column_labels") or []
    if column_labels and len(column_labels) != len(columns):
        raise ValueError("column_labels must match the number of selected columns")

    df_for_chart = df[columns].copy()
    plot_columns = list(columns)

    if column_labels:
        sanitized_labels = []
        seen = {}
        for idx, label in enumerate(column_labels):
            candidate = str(label).strip() if label is not None else ""
            if not candidate:
                candidate = str(columns[idx])

            if candidate in seen:
                seen[candidate] += 1
                candidate = f"{candidate}_{seen[candidate]}"
            else:
                seen[candidate] = 1

            sanitized_labels.append(candidate)

        rename_mapping = dict(zip(columns, sanitized_labels))
        df_for_chart = df_for_chart.rename(columns=rename_mapping)
        plot_columns = sanitized_labels

    chart_payload = {
        "id": chart_config.get("id"),
        "source_id": source_id,
        "range": range_str,
        "chart_type": chart_config.get("chart_type"),
        "columns": columns,
        "column_labels": column_labels,
        "title": chart_config.get("title", ""),
    }
    render_payload = {
        "chart_type": chart_payload["chart_type"],
        "columns": plot_columns,
        "title": chart_payload["title"],
    }
    traces, layout = _render_chart_config(df_for_chart, render_payload)
    return chart_payload, traces, layout


def _upsert_chart(chart_config):
    global CHART_STATE

    updated = False
    charts = CHART_STATE.get("charts", [])
    for index, existing_chart in enumerate(charts):
        if existing_chart["id"] == chart_config["id"]:
            charts[index] = chart_config
            updated = True
            break

    if not updated:
        charts.append(chart_config)

    CHART_STATE = {
        "active_chart_id": chart_config["id"],
        "charts": charts,
    }

@plots_bp.post("/generate")
def generate():
    source_id = request.form.get("source_id", "")
    chart_type = request.form.get("chart_type", "")
    title = request.form.get("title", "")
    range_str = request.form.get("range", "").strip() or None
    columns = json.loads(request.form.get("columns", "[]"))
    column_labels = json.loads(request.form.get("column_labels", "[]"))

    try:
        payload = {
            "id": request.form.get("chart_id", "preview"),
            "source_id": source_id,
            "range": range_str,
            "chart_type": chart_type,
            "columns": columns,
            "column_labels": column_labels,
            "title": title,
        }
        chart_config, traces, layout = _render_from_source(payload)

        return jsonify({
            "chart": chart_config,
            "traces": traces,
            "layout": layout
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

@plots_bp.post("/new_chart")
def new_chart():
    source_id = request.form.get("source_id", "")
    chart_type = request.form.get("chart_type", "")
    title = request.form.get("title", "")
    range_str = request.form.get("range", "").strip() or None
    columns = json.loads(request.form.get("columns", "[]"))
    column_labels = json.loads(request.form.get("column_labels", "[]"))

    if not chart_type:
        return jsonify({"error": "chart_type is required"}), 400
    if not source_id:
        return jsonify({"error": "source_id is required"}), 400

    chart_id = request.form.get("chart_id") or str(uuid.uuid4())
    payload = {
        "id": chart_id,
        "source_id": source_id,
        "range": range_str,
        "chart_type": chart_type,
        "columns": columns,
        "column_labels": column_labels,
        "title": title,
    }

    try:
        chart_config, traces, layout = _render_from_source(payload)
        _upsert_chart(chart_config)
        return jsonify({
            "success": True,
            "chart": chart_config,
            "traces": traces,
            "layout": layout,
            "chart_state": CHART_STATE,
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@plots_bp.get("/charts")
def list_charts():
    return jsonify({"chart_state": CHART_STATE})


@plots_bp.delete("/charts/<chart_id>")
def delete_chart(chart_id):
    global CHART_STATE
    charts = [chart for chart in CHART_STATE.get("charts", []) if chart["id"] != chart_id]
    active_chart_id = CHART_STATE.get("active_chart_id")

    if active_chart_id == chart_id:
        active_chart_id = charts[-1]["id"] if charts else None

    CHART_STATE = {
        "active_chart_id": active_chart_id,
        "charts": charts,
    }
    return jsonify({"success": True, "chart_state": CHART_STATE})


@plots_bp.post("/charts/reorder")
def reorder_chart():
    global CHART_STATE

    payload = request.get_json(silent=True) or {}
    chart_id = payload.get("chart_id")
    target_index = payload.get("target_index")

    if not chart_id:
        return jsonify({"error": "chart_id is required"}), 400
    if not isinstance(target_index, int):
        return jsonify({"error": "target_index must be an integer"}), 400

    charts = CHART_STATE.get("charts", [])
    current_index = next((idx for idx, chart in enumerate(charts) if chart.get("id") == chart_id), None)
    if current_index is None:
        return jsonify({"error": "Chart not found"}), 404

    clamped_index = max(0, min(target_index, len(charts) - 1))
    chart = charts.pop(current_index)
    charts.insert(clamped_index, chart)

    CHART_STATE = {
        "active_chart_id": chart_id,
        "charts": charts,
    }
    return jsonify({"success": True, "chart_state": CHART_STATE})


@plots_bp.post("/render_charts")
def render_charts():
    rendered_charts = []

    for chart in CHART_STATE.get("charts", []):
        chart_payload = dict(chart)
        try:
            _, traces, layout = _render_from_source(chart)
            chart_payload["traces"] = traces
            chart_payload["layout"] = layout
            chart_payload["error"] = None
        except Exception as exc:
            chart_payload["traces"] = []
            chart_payload["layout"] = {}
            chart_payload["error"] = str(exc)
        rendered_charts.append(chart_payload)

    return jsonify({"charts": rendered_charts, "chart_state": CHART_STATE})


@plots_bp.post("/hydrate_charts")
def hydrate_charts():
    global CHART_STATE
    payload = request.get_json(silent=True) or {}
    state = payload.get("chart_state", payload)

    charts = state.get("charts")
    if not isinstance(charts, list):
        charts = []

    valid_charts = []
    for chart in charts:
        if not isinstance(chart, dict):
            continue
        if not chart.get("chart_type"):
            continue
        if not chart.get("source_id"):
            continue
        valid_charts.append(
            {
                "id": chart.get("id") or str(uuid.uuid4()),
                "source_id": chart.get("source_id"),
                "range": chart.get("range"),
                "chart_type": chart.get("chart_type"),
                "columns": chart.get("columns", []),
                "column_labels": chart.get("column_labels", []),
                "title": chart.get("title", ""),
            }
        )

    active_chart_id = state.get("active_chart_id")
    if active_chart_id not in {chart["id"] for chart in valid_charts}:
        active_chart_id = valid_charts[-1]["id"] if valid_charts else None

    CHART_STATE = {
        "active_chart_id": active_chart_id,
        "charts": valid_charts,
    }
    return jsonify({"success": True, "chart_state": CHART_STATE})


@plots_bp.post("/charts/reset")
def reset_charts():
    global CHART_STATE
    CHART_STATE = {
        "active_chart_id": None,
        "charts": [],
    }
    return jsonify({"success": True, "chart_state": CHART_STATE})


def get_chart_state_snapshot():
    return {
        "active_chart_id": CHART_STATE.get("active_chart_id"),
        "charts": [dict(chart) for chart in CHART_STATE.get("charts", [])],
    }
