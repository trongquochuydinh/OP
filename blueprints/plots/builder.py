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
            title=title or f"Frequency of {col}"
        )

    # CASE 2: two columns → Check if both are categorical for grouping, otherwise X/Y
    elif len(columns) == 2:
        x_col = columns[0]
        y_col = columns[1]

        # Drop rows where either column is null
        df_clean = df[[x_col, y_col]].dropna()
        
        # Check if both columns appear to be categorical (strings or limited unique values)
        x_is_categorical = df_clean[x_col].dtype == 'object' or df_clean[x_col].nunique() <= 20
        y_is_categorical = df_clean[y_col].dtype == 'object' or df_clean[y_col].nunique() <= 20
        
        if x_is_categorical and y_is_categorical:
            # Both categorical: group by combination and count
            grouped = df_clean.groupby([x_col, y_col]).size().reset_index(name='count')
            
            # Create a combined label for x-axis
            grouped['combination'] = grouped[x_col].astype(str) + " - " + grouped[y_col].astype(str)
            
            return CHART_BUILDERS[chart_type](
                grouped,
                x_col='combination',
                y_col='count',
                title=title or f"Count of {x_col} by {y_col}"
            )
        else:
            # At least one is numeric: treat as X vs Y
            return CHART_BUILDERS[chart_type](
                df_clean,
                x_col=x_col,
                y_col=y_col,
                title=title or f"{y_col} vs {x_col}"
            )
    
    # CASE 3: multiple columns → use first two with same categorical logic
    else:
        x_col = columns[0]
        y_col = columns[1]
        
        # Drop rows where the first two columns are null
        df_clean = df[[x_col, y_col]].dropna()
        
        # Check if both columns appear to be categorical
        x_is_categorical = df_clean[x_col].dtype == 'object' or df_clean[x_col].nunique() <= 20
        y_is_categorical = df_clean[y_col].dtype == 'object' or df_clean[y_col].nunique() <= 20
        
        if x_is_categorical and y_is_categorical:
            # Both categorical: group by combination and count
            grouped = df_clean.groupby([x_col, y_col]).size().reset_index(name='count')
            grouped['combination'] = grouped[x_col].astype(str) + " - " + grouped[y_col].astype(str)
            
            return CHART_BUILDERS[chart_type](
                grouped,
                x_col='combination',
                y_col='count',
                title=title or f"Count of {x_col} by {y_col} (using first 2 of {len(columns)} columns)"
            )
        else:
            # At least one is numeric: treat as X vs Y
            return CHART_BUILDERS[chart_type](
                df_clean,
                x_col=x_col,
                y_col=y_col,
                title=title or f"{y_col} vs {x_col} (using first 2 of {len(columns)} columns)"
            )
