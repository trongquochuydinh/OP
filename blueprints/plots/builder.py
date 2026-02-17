from collections import Counter
import plotly.colors as pc

def build_linechart(records, columns):
    traces = []

    for col in columns:
        traces.append({
            "x": list(range(len(records))),
            "y": [r.get(col) for r in records],
            "type": "scatter",
            "mode": "lines",
            "name": col
        })

    layout = {
        "title": "Line Chart",
        "xaxis": {"title": "Index"},
        "yaxis": {"title": "Value"}
    }

    return traces, layout


def build_boxplot(records, columns):
    traces = []

    for col in columns:
        traces.append({
            "y": [r.get(col) for r in records],
            "type": "box",
            "name": col
        })

    layout = {
        "title": "Box Plot"
    }

    return traces, layout



def build_barchart(records, column, title):

    values = [r.get(column) for r in records]
    counter = Counter(values)

    sorted_items = sorted(counter.items(), key=lambda x: x[1], reverse=True)

    x_vals = [str(k) for k, _ in sorted_items]
    y_vals = [v for _, v in sorted_items]

    # Use built-in qualitative palette
    colors = pc.qualitative.Plotly

    # Repeat colors if more bars than palette size
    color_list = [colors[i % len(colors)] for i in range(len(x_vals))]

    traces = [{
        "x": x_vals,
        "y": y_vals,
        "type": "bar",
        "name": column,
        "marker": {
            "color": color_list
        }
    }]

    layout = {
        "title": title,
        "xaxis": {"type": "category"},
        "yaxis": {"title": "Count"},
        "bargap": 0.05
    }

    return traces, layout

def build_piechart(records, column):
    values = [r.get(column) for r in records]

    traces = [{
        "labels": [f"Item {i}" for i in range(len(values))],
        "values": values,
        "type": "pie"
    }]

    layout = {
        "title": f"Pie Chart - {column}"
    }

    return traces, layout

def build_stacked_barchart():
    return

def build_horizontal_clustered_barchart():
    return

def build_dumbbellchart(records, _, title):

    labels = [r["label"] for r in records]
    lows = [r["low"] for r in records]
    highs = [r["high"] for r in records]

    traces = []

    # connecting lines
    for i in range(len(records)):
        traces.append({
            "x": [lows[i], highs[i]],
            "y": [labels[i], labels[i]],
            "mode": "lines",
            "line": {"color": "gray"},
            "showlegend": False
        })

    # low points
    traces.append({
        "x": lows,
        "y": labels,
        "mode": "markers",
        "marker": {"color": "blue", "size": 8},
        "name": "Lower bound"
    })

    # high points
    traces.append({
        "x": highs,
        "y": labels,
        "mode": "markers",
        "marker": {"color": "orange", "size": 8},
        "name": "Upper bound"
    })

    layout = {
        "title": title,
        "xaxis": {"title": "Salary"},
        "yaxis": {"automargin": True},
        "height": max(600, len(records) * 25)
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

def build_chart(chart_type, records, column, title):
    if chart_type not in CHART_BUILDERS:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    return CHART_BUILDERS[chart_type](records, column, title)
