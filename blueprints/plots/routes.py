from flask import request, jsonify
import uuid
import json
import re
from pathlib import Path
from datetime import datetime
import plotly.io as pio
from . import plots_bp
from blueprints.plots.builder import build_chart
from blueprints.plots.plot_style import apply_plot_style
import blueprints.data_processing.routes as data_routes

CHART_STATE = {
    "active_chart_id": None,
    "charts": [],
}

REPORTS_DIR = Path(__file__).resolve().parents[2] / "generated_reports"


def _slugify_key(raw_value):
    candidate = re.sub(r"[^a-zA-Z0-9_-]", "_", str(raw_value or "").strip())
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    return candidate


def _derive_chart_key(chart_config, index=1, used_keys=None):
    used = used_keys if used_keys is not None else set()

    preferred = chart_config.get("chart_key")
    title = chart_config.get("title")
    chart_type = chart_config.get("chart_type")

    base = _slugify_key(preferred) or _slugify_key(title) or _slugify_key(chart_type) or f"chart_{index}"
    candidate = base
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{suffix}"
        suffix += 1

    used.add(candidate)
    return candidate


def _parse_plot_style(raw):
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _parse_counts_mode(raw):
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip().lower()
    return s in ("1", "true", "yes", "on")


def _validate_chart_key_uniqueness(chart_id, chart_key):
    for chart in CHART_STATE.get("charts", []):
        if chart.get("id") == chart_id:
            continue
        if chart.get("chart_key") == chart_key:
            raise ValueError(f"chart_key '{chart_key}' already exists")


def _render_chart_config(df, chart_config):
    traces, layout = build_chart(
        chart_config["chart_type"],
        df,
        chart_config["columns"],
        chart_config.get("title", ""),
        counts_mode=chart_config.get("counts_mode", False),
        font_size=chart_config.get("font_size", 12),
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

        df_for_chart.columns = sanitized_labels
        plot_columns = sanitized_labels

    plot_style = _parse_plot_style(chart_config.get("plot_style"))
    try:
        font_size = int(chart_config.get("font_size", 12))
    except (TypeError, ValueError):
        font_size = 12

    chart_payload = {
        "id": chart_config.get("id"),
        "chart_key": chart_config.get("chart_key"),
        "source_id": source_id,
        "range": range_str,
        "chart_type": chart_config.get("chart_type"),
        "columns": columns,
        "column_labels": column_labels,
        "title": chart_config.get("title", ""),
        "plot_style": plot_style,
        "counts_mode": bool(chart_config.get("counts_mode")),
        "font_size": font_size,
    }
    render_payload = {
        "chart_type": chart_payload["chart_type"],
        "columns": plot_columns,
        "title": chart_payload["title"],
        "counts_mode": chart_payload["counts_mode"],
        "font_size": font_size,
    }
    traces, layout = _render_chart_config(df_for_chart, render_payload)
    traces, layout = apply_plot_style(traces, layout, plot_style, chart_payload["chart_type"])
    return chart_payload, traces, layout


def _upsert_chart(chart_config):
    global CHART_STATE

    chart_key = _slugify_key(chart_config.get("chart_key"))
    if not chart_key:
        used_keys = {
            chart.get("chart_key")
            for chart in CHART_STATE.get("charts", [])
            if chart.get("id") != chart_config.get("id") and chart.get("chart_key")
        }
        chart_key = _derive_chart_key(chart_config, len(CHART_STATE.get("charts", [])) + 1, used_keys)
    _validate_chart_key_uniqueness(chart_config["id"], chart_key)
    chart_config["chart_key"] = chart_key

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
    chart_key = request.form.get("chart_key", "").strip()
    columns = json.loads(request.form.get("columns", "[]"))
    column_labels = json.loads(request.form.get("column_labels", "[]"))
    plot_style = _parse_plot_style(request.form.get("plot_style"))
    counts_mode = _parse_counts_mode(request.form.get("counts_mode"))
    try:
        font_size = int(request.form.get("font_size", 12))
    except (TypeError, ValueError):
        font_size = 12

    try:
        payload = {
            "id": request.form.get("chart_id", "preview"),
            "chart_key": _slugify_key(chart_key) or "preview",
            "source_id": source_id,
            "range": range_str,
            "chart_type": chart_type,
            "columns": columns,
            "column_labels": column_labels,
            "title": title,
            "plot_style": plot_style,
            "counts_mode": counts_mode,
            "font_size": font_size,
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
    chart_key = request.form.get("chart_key", "").strip()
    columns = json.loads(request.form.get("columns", "[]"))
    column_labels = json.loads(request.form.get("column_labels", "[]"))
    plot_style = _parse_plot_style(request.form.get("plot_style"))
    counts_mode = _parse_counts_mode(request.form.get("counts_mode"))
    try:
        font_size = int(request.form.get("font_size", 12))
    except (TypeError, ValueError):
        font_size = 12

    if not chart_type:
        return jsonify({"error": "chart_type is required"}), 400
    if not source_id:
        return jsonify({"error": "source_id is required"}), 400

    chart_id = request.form.get("chart_id") or str(uuid.uuid4())
    payload = {
        "id": chart_id,
        "chart_key": _slugify_key(chart_key),
        "source_id": source_id,
        "range": range_str,
        "chart_type": chart_type,
        "columns": columns,
        "column_labels": column_labels,
        "title": title,
        "plot_style": plot_style,
        "counts_mode": counts_mode,
        "font_size": font_size,
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
    known_sources = {
        source.get("source_id")
        for source in data_routes.get_data_state_snapshot().get("sources", [])
    }

    for chart in CHART_STATE.get("charts", []):
        chart_payload = dict(chart)
        source_id = chart_payload.get("source_id")
        if source_id not in known_sources:
            chart_payload["traces"] = []
            chart_payload["layout"] = {}
            chart_payload["error"] = f"Source unavailable for chart: {source_id}. Reload sources from disk or load your saved configuration again."
            rendered_charts.append(chart_payload)
            continue

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
    used_keys = set()
    for chart in charts:
        if not isinstance(chart, dict):
            continue
        if not chart.get("chart_type"):
            continue
        if not chart.get("source_id"):
            continue
        chart_key = _derive_chart_key(chart, len(valid_charts) + 1, used_keys)
        try:
            hydrate_font_size = int(chart.get("font_size", 12))
        except (TypeError, ValueError):
            hydrate_font_size = 12
        valid_charts.append(
            {
                "id": chart.get("id") or str(uuid.uuid4()),
                "chart_key": chart_key,
                "source_id": chart.get("source_id"),
                "range": chart.get("range"),
                "chart_type": chart.get("chart_type"),
                "columns": chart.get("columns", []),
                "column_labels": chart.get("column_labels", []),
                "title": chart.get("title", ""),
                "plot_style": _parse_plot_style(chart.get("plot_style")),
                "counts_mode": bool(chart.get("counts_mode")),
                "font_size": int(chart.get("font_size") or 12),
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


def export_charts_to_pngs(output_root=None, width=1400, height=800, scale=2):
    charts = CHART_STATE.get("charts", [])
    if not charts:
        return {
            "output_dir": None,
            "exported": [],
            "warnings": ["No charts to export"],
            "errors": [],
            "image_map": {},
        }

    if output_root is None:
        output_root = REPORTS_DIR / datetime.utcnow().strftime("%Y%m%d_%H%M%S") / "charts"
    else:
        output_root = Path(output_root)

    output_root.mkdir(parents=True, exist_ok=True)

    exported = []
    warnings = []
    errors = []
    image_map = {}

    used_keys = set()
    for index, chart in enumerate(charts, start=1):
        chart_copy = dict(chart)
        chart_key = _derive_chart_key(chart_copy, index, used_keys)
        chart_copy["chart_key"] = chart_key

        try:
            _, traces, layout = _render_from_source(chart_copy)
            image_name = f"{index:02d}_{chart_key}.png"
            image_path = output_root / image_name
            figure = {
                "data": traces,
                "layout": layout,
            }
            pio.write_image(figure, str(image_path), width=width, height=height, scale=scale)
            exported.append(
                {
                    "chart_id": chart_copy.get("id"),
                    "chart_key": chart_key,
                    "path": str(image_path),
                }
            )
            image_map[chart_key] = str(image_path)
        except Exception as exc:
            errors.append(
                {
                    "chart_id": chart_copy.get("id"),
                    "chart_key": chart_key,
                    "error": str(exc),
                }
            )

    if not exported and not errors:
        warnings.append("No charts were exported")

    return {
        "output_dir": str(output_root),
        "exported": exported,
        "warnings": warnings,
        "errors": errors,
        "image_map": image_map,
    }


@plots_bp.post("/charts/export-png")
def export_charts_png():
    payload = request.get_json(silent=True) or {}
    width = int(payload.get("width", 1400))
    height = int(payload.get("height", 800))
    scale = int(payload.get("scale", 2))

    export_result = export_charts_to_pngs(width=width, height=height, scale=scale)
    return jsonify({"success": True, **export_result})
