"""Apply user plot_style dict to Plotly traces/layout after builder output."""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence


def _legend_layout(position: str) -> Dict[str, Any]:
    position = (position or "default").strip().lower()
    if position == "bottom":
        return {"orientation": "h", "yanchor": "top", "y": -0.25, "xanchor": "center", "x": 0.5}
    if position == "top":
        return {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5}
    if position == "left":
        return {"xanchor": "right", "x": -0.02, "yanchor": "middle", "y": 0.5}
    if position == "right":
        return {"xanchor": "left", "x": 1.02, "yanchor": "middle", "y": 0.5}
    if position == "inside_bottom_right":
        return {"x": 0.99, "y": 0.01, "xanchor": "right", "yanchor": "bottom"}
    return {}


def _normalize_style(style: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not style or not isinstance(style, dict):
        return {}
    return deepcopy(style)


def _styleable_trace_indices(traces: List[Dict[str, Any]], chart_type: str) -> List[int]:
    """Indices of traces that participate in per-series color/line styling."""
    indices = []
    for i, trace in enumerate(traces):
        t = trace.get("type")
        if t == "pie":
            continue
        if chart_type == "dumbbellchart" and trace.get("showlegend") is False:
            continue
        if t in ("scatter", "bar", "box"):
            indices.append(i)
    return indices


_DEFAULT_PIE_SLICE_COLORS = (
    "#636EFA",
    "#EF553B",
    "#00CC96",
    "#AB63FA",
    "#FFA15A",
    "#19D3F3",
    "#FF6692",
    "#B6E880",
    "#FF97FF",
    "#FECB52",
)


def _apply_pie_series_colors(trace: Dict[str, Any], series_styles: List[Any]) -> None:
    """One color per slice from style.series[i].color, padding with defaults."""
    labels = trace.get("labels") or []
    values = trace.get("values") or []
    n = len(labels) if isinstance(labels, list) and labels else (len(values) if isinstance(values, list) else 0)
    if n == 0:
        return
    colors: List[str] = []
    for i in range(n):
        c = None
        if i < len(series_styles):
            ent = series_styles[i]
            if isinstance(ent, dict):
                raw = ent.get("color")
                if raw is not None and str(raw).strip():
                    c = str(raw).strip()
        if not c:
            c = _DEFAULT_PIE_SLICE_COLORS[i % len(_DEFAULT_PIE_SLICE_COLORS)]
        colors.append(c)
    trace.setdefault("marker", {})["colors"] = colors


def _apply_series_entry(trace: Dict[str, Any], entry: Dict[str, Any]) -> None:
    """Merge one series style dict onto a trace."""
    if not isinstance(entry, dict):
        return

    color = entry.get("color")
    line_width = entry.get("line_width")
    line_dash = entry.get("line_dash")

    t = trace.get("type")

    if color:
        if t == "scatter":
            trace.setdefault("line", {})["color"] = color
            trace.setdefault("marker", {})["color"] = color
        elif t == "bar" or t == "box":
            trace.setdefault("marker", {})["color"] = color

    line_kw: Dict[str, Any] = {}
    if line_width is not None:
        try:
            lw = float(line_width)
            if lw > 0:
                line_kw["width"] = lw
        except (TypeError, ValueError):
            pass
    if line_dash and isinstance(line_dash, str) and line_dash.strip().lower() != "solid":
        dash_norm = line_dash.strip().lower()
        plotly_dash = dash_norm if dash_norm in ("dot", "dash", "longdash", "dashdot", "longdashdot") else "solid"
        if plotly_dash != "solid":
            line_kw["dash"] = plotly_dash

    if not line_kw:
        return

    if t == "scatter":
        ln = trace.setdefault("line", {})
        ln.update(line_kw)
    elif t == "bar":
        ml = trace.setdefault("marker", {}).setdefault("line", {})
        ml.update({k: line_kw[k] for k in ("width", "dash") if k in line_kw})


def apply_plot_style(
    traces: List[Dict[str, Any]],
    layout: Dict[str, Any],
    style: Optional[Dict[str, Any]],
    chart_type: str,
) -> tuple:
    """Return mutated copies of traces and layout."""
    traces = deepcopy(traces)
    layout = deepcopy(layout or {})
    style = _normalize_style(style)
    if not style:
        return traces, layout

    if style.get("title_visible") is False:
        layout["title"] = ""

    leg = style.get("legend") or {}
    if isinstance(leg, dict):
        if leg.get("visible") is False:
            layout["showlegend"] = False
        else:
            layout["showlegend"] = True
            pos = leg.get("position") or "default"
            legend_extra = _legend_layout(str(pos))
            if legend_extra:
                existing = layout.get("legend") or {}
                layout["legend"] = {**existing, **legend_extra}

    if style.get("markers_visible") is True:
        for trace in traces:
            if trace.get("type") != "scatter":
                continue
            mode = trace.get("mode") or ""
            if mode == "lines":
                trace["mode"] = "lines+markers"
                mk = trace.setdefault("marker", {})
                mk.setdefault("size", 7)

    idx_map = _styleable_trace_indices(traces, chart_type or "")
    colors: Sequence[Any] = style.get("colors") or []
    series_styles = style.get("series") or []

    if isinstance(colors, list) and colors:
        pie_done = False
        for trace in traces:
            if trace.get("type") == "pie":
                trace.setdefault("marker", {})["colors"] = list(colors)
                pie_done = True
                break
        if not pie_done:
            for slot, trace_idx in enumerate(idx_map):
                trace = traces[trace_idx]
                t = trace.get("type")
                c = colors[slot % len(colors)]
                if t == "scatter":
                    trace.setdefault("line", {})["color"] = c
                    trace.setdefault("marker", {})["color"] = c
                elif t == "bar":
                    trace.setdefault("marker", {})["color"] = c
                elif t == "box":
                    trace.setdefault("marker", {})["color"] = c

    if isinstance(series_styles, list) and series_styles:
        for slot, trace_idx in enumerate(idx_map):
            if slot >= len(series_styles):
                break
            entry = series_styles[slot]
            if not isinstance(entry, dict):
                continue
            _apply_series_entry(traces[trace_idx], entry)

        for trace in traces:
            if trace.get("type") == "pie":
                _apply_pie_series_colors(trace, series_styles)
                break

    ref_lines = style.get("ref_lines") or []
    if isinstance(ref_lines, list) and ref_lines:
        shapes = list(layout.get("shapes") or [])
        for rl in ref_lines:
            if not isinstance(rl, dict):
                continue
            axis = str(rl.get("axis", "x")).lower()
            val = rl.get("value")
            if val is None:
                continue
            line_style = rl.get("line") if isinstance(rl.get("line"), dict) else {}
            color = line_style.get("color", "#888")
            dash = line_style.get("dash", "dash")
            line_kw = {"color": color, "width": line_style.get("width", 1)}
            if dash:
                line_kw["dash"] = dash
            if axis == "y":
                shapes.append(
                    {
                        "type": "line",
                        "xref": "paper",
                        "yref": "y",
                        "x0": 0,
                        "y0": val,
                        "x1": 1,
                        "y1": val,
                        "line": line_kw,
                    }
                )
            else:
                shapes.append(
                    {
                        "type": "line",
                        "xref": "x",
                        "yref": "paper",
                        "x0": val,
                        "y0": 0,
                        "x1": val,
                        "y1": 1,
                        "line": line_kw,
                    }
                )
        layout["shapes"] = shapes

    return traces, layout
