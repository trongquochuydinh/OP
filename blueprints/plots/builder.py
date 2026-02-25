from collections import Counter
import plotly.colors as pc
import pandas as pd

def build_linechart(df, x_col, y_col, title):

    traces = [{
        "x": df[x_col].tolist(),
        "y": df[y_col].tolist(),
        "type": "scatter",
        "mode": "lines",
        "name": f"{y_col} vs {x_col}"
    }]

    layout = {
        "title": title,
        "xaxis": {"title": x_col},
        "yaxis": {"title": y_col}
    }

    return traces, layout


def build_boxplot(df, x_col, y_col, title):

    traces = [{
        "y": df[y_col].tolist(),
        "type": "box",
        "name": y_col
    }]

    layout = {
        "title": title,
        "yaxis": {"title": y_col}
    }

    return traces, layout



def build_barchart(df, x_col, y_col, title):

    traces = [{
        "x": df[x_col].astype(str).tolist(),
        "y": df[y_col].tolist(),
        "type": "bar"
    }]

    layout = {
        "title": title,
        "xaxis": {"type": "category", "title": x_col},
        "yaxis": {"title": y_col},
        "bargap": 0.05
    }

    return traces, layout


def build_piechart(df, x_col, y_col, title):

    traces = [{
        "labels": df[x_col].astype(str).tolist(),
        "values": df[y_col].tolist(),
        "type": "pie"
    }]

    layout = {
        "title": title
    }

    return traces, layout

def build_stacked_barchart(df, x_col, y_col, title):

    # Group by x_col
    grouped = df.groupby(x_col)[y_col].sum().reset_index()

    traces = [{
        "x": grouped[x_col].astype(str).tolist(),
        "y": grouped[y_col].tolist(),
        "type": "bar",
        "name": y_col
    }]

    layout = {
        "title": title,
        "barmode": "stack",
        "xaxis": {"title": x_col},
        "yaxis": {"title": y_col}
    }

    return traces, layout

def build_horizontal_clustered_barchart(df, x_col, y_col, title):

    traces = [{
        "x": df[y_col].tolist(),
        "y": df[x_col].astype(str).tolist(),
        "type": "bar",
        "orientation": "h",
        "name": y_col
    }]

    layout = {
        "title": title,
        "barmode": "group",
        "xaxis": {"title": y_col},
        "yaxis": {"title": x_col, "automargin": True}
    }

    return traces, layout


def build_dumbbellchart(records, _, title):

    traces = []

    labels = [r["label"] for r in records]

    # Draw connecting lines only if high exists
    for r in records:
        if r["high"] is not None:
            traces.append({
                "x": [r["low"], r["high"]],
                "y": [r["label"], r["label"]],
                "mode": "lines",
                "line": {"color": "gray"},
                "showlegend": False
            })

    # Low points
    traces.append({
        "x": [r["low"] for r in records],
        "y": labels,
        "mode": "markers",
        "marker": {"color": "blue", "size": 8},
        "name": "Low"
    })

    # High points (only where exists)
    traces.append({
        "x": [r["high"] for r in records if r["high"] is not None],
        "y": [r["label"] for r in records if r["high"] is not None],
        "mode": "markers",
        "marker": {"color": "orange", "size": 8},
        "name": "High"
    })

    layout = {
        "title": title,
        "yaxis": {
            "automargin": True,
            "categoryorder": "array",
            "categoryarray": labels
        },
        "height": max(800, len(records) * 20)
    }

    return traces, layout

CHART_BUILDERS = {
    "linechart": build_linechart,
    "boxplot": build_boxplot,
    "barchart": build_barchart,
    "piechart": build_piechart,
    "stackedbarchart": build_stacked_barchart,
    "horizonvalclusteredbarchart": build_horizontal_clustered_barchart,
    "dumbbellchart": build_dumbbellchart
}

def build_chart(chart_type, df, columns, title):

    if chart_type not in CHART_BUILDERS:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    if not columns:
        raise ValueError("No columns selected")

    df = df.copy()

    df = df.where(pd.notnull(df), None)

    # CASE 1: single column → grouping + count
    if len(columns) == 1:
        col = columns[0]

        # drop rows where selected column is null
        df = df[df[col].notna()]

        grouped = df[col].value_counts().reset_index()
        grouped.columns = [col, "count"]

        return CHART_BUILDERS[chart_type](
            grouped,
            x_col=col,
            y_col="count",
            title=title
        )

    # CASE 2: two columns → X/Y
    else:
        x_col = columns[0]
        y_col = columns[1]

        # 🔥 Drop rows where either column is null
        df = df[[x_col, y_col]].dropna()

        return CHART_BUILDERS[chart_type](
            df,
            x_col=x_col,
            y_col=y_col,
            title=title
        )
