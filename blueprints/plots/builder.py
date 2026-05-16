from collections import Counter
import plotly.colors as pc
import pandas as pd


def _parse_cell_to_float(v):
    """Parse a scalar to float; align with _multi_series_melt_chart numeric rules (% and comma decimals)."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if pd.isna(v):
            return None
        return float(v)
    s = str(v).strip()
    if s == "":
        return None
    was_percent = "%" in s
    s_clean = s.replace("%", "").replace("\xa0", "").strip()
    if "," in s_clean and "." not in s_clean:
        s_try = s_clean.replace(".", "").replace(",", ".")
    else:
        s_try = s_clean.replace(",", "")
    try:
        num = float(s_try)
        if was_percent:
            num = num / 100.0
        return num
    except Exception:
        return None


def _dumbbell_records(df, label_col, low_col, high_col):
    records = []
    for _, row in df.iterrows():
        label = row[label_col]
        if label is None or (isinstance(label, float) and pd.isna(label)):
            continue
        low = _parse_cell_to_float(row[low_col])
        high = _parse_cell_to_float(row[high_col]) if high_col is not None else None
        if low is None:
            continue
        records.append({"label": str(label), "low": low, "high": high})
    return records


def _build_dumbbell_chart(df, columns, title, counts_mode):
    if counts_mode:
        if len(columns) < 2:
            raise ValueError("Counts aggregation requires at least two columns")
        return _counts_combo_chart(df, columns, "dumbbellchart", title)

    if len(columns) < 2:
        raise ValueError(
            "Dumbbell chart needs 2 or 3 columns: label, low values, optional high values"
        )

    label_col = columns[0]
    low_col = columns[1]
    high_col = columns[2] if len(columns) > 2 else None

    cols = [label_col, low_col]
    if high_col is not None:
        cols.append(high_col)
    df_sub = df[cols].copy()
    records = _dumbbell_records(df_sub, label_col, low_col, high_col)
    if not records:
        raise ValueError("No rows with a parseable low value for dumbbell chart")

    if not title:
        if high_col:
            title = f"{low_col}–{high_col} vs {label_col}"
        else:
            title = f"{low_col} vs {label_col}"

    return build_dumbbellchart(records, None, title)

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
        "type": "bar",
        "name": y_col
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

    work = df[[x_col, y_col]].copy()
    work[y_col] = pd.to_numeric(work[y_col], errors="coerce")
    work = work.dropna(subset=[y_col])
    if work.empty:
        raise ValueError("No numeric values in Y column for stacked bar chart")

    grouped = work.groupby(x_col)[y_col].sum().reset_index()

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

_COUNT_COMBO_SEP = " — "


def _counts_combo_chart(df, columns, chart_type, title):
    """
    Group by all selected columns and plot row counts per distinct combination.
    Used when counts_mode is True with exactly two columns (joint combinations).
    """
    if len(columns) < 2:
        raise ValueError("Counts aggregation requires at least two columns")

    df_sel = df[list(columns)].dropna(how="any")
    if df_sel.empty:
        raise ValueError("No complete rows for count aggregation")

    grouped = df_sel.groupby(list(columns), dropna=False).size().reset_index(name="count")

    combo = grouped[columns[0]].astype(str)
    for col in columns[1:]:
        combo = combo + _COUNT_COMBO_SEP + grouped[col].astype(str)
    grouped["combination"] = combo

    categorical_builders = ("barchart", "stackedbarchart", "horizonvalclusteredbarchart", "piechart")
    builder_key = chart_type if chart_type in categorical_builders else "barchart"

    cols_label = ", ".join(str(c) for c in columns)
    default_title = title or f"Row counts by ({cols_label})"

    return CHART_BUILDERS[builder_key](
        grouped,
        x_col="combination",
        y_col="count",
        title=default_title,
    )


def _multi_series_melt_chart(df, columns, chart_type, title, *, counts_only=False):
    """Three or more columns: first column is shared X; each remaining column is its own trace.

    counts_only: counts of non-null cells per (first column, source column)—same grouped layout as
    the automatic categorical multi-series path. Otherwise numeric vs categorical rules apply.
    """
    id_col = columns[0]
    value_cols = columns[1:]
    df_sub = df[[id_col] + value_cols].dropna(how="all")

    if df_sub.empty:
        x_col = columns[0]
        y_col = columns[1] if len(columns) > 1 else columns[0]
        df_sub2 = df[[x_col, y_col]].dropna()
        return CHART_BUILDERS[chart_type](
            df_sub2,
            x_col=x_col,
            y_col=y_col,
            title=title or f"{y_col} vs {x_col} (using first 2 of {len(columns)} columns)",
        )

    df_melt = df_sub.melt(
        id_vars=[id_col], value_vars=value_cols, var_name="variable", value_name="value"
    )

    if counts_only:
        counts = (
            df_melt.dropna(subset=["value"])
            .groupby([id_col, "variable"])
            .size()
            .reset_index(name="count")
        )
        pivot = counts.pivot(index=id_col, columns="variable", values="count").fillna(0).reset_index()
        default_title = title or f"Count of values by {id_col}"
        value_label = "count"
    else:
        import os

        def _parse_value(v):
            if v is None:
                return (None, False, False)
            # numeric types
            if isinstance(v, (int, float)):
                return (float(v), True, False)
            s = str(v).strip()
            if s == "":
                return (None, False, False)
            was_percent = "%" in s
            # remove percent and whitespace/non-breaking spaces
            s_clean = s.replace("%", "").replace("\xa0", "").strip()
            # If it looks like European decimal (comma but no dot) convert
            if "," in s_clean and "." not in s_clean:
                s_try = s_clean.replace(".", "").replace(",", ".")
            else:
                s_try = s_clean.replace(",", "")
            try:
                num = float(s_try)
                if was_percent:
                    num = num / 100.0
                return (num, True, was_percent)
            except Exception:
                return (None, False, False)

        parsed = df_melt["value"].apply(_parse_value)
        df_melt["numeric_value"] = parsed.apply(lambda t: t[0])
        df_melt["is_numeric"] = parsed.apply(lambda t: t[1])
        df_melt["was_percent"] = parsed.apply(lambda t: t[2])

        # Decide numeric vs categorical path (threshold configurable)
        frac_numeric = df_melt["is_numeric"].mean() if len(df_melt) > 0 else 0.0

        # Aggregation selection (default 'mean'); frontend should set OP_MULTI_AGG env or we can extend API later
        agg = os.environ.get("OP_MULTI_AGG", "mean").lower()
        if agg not in ("mean", "sum", "median"):
            agg = "mean"

        # Build pivoted table either with aggregated numeric values or counts for categorical
        if frac_numeric >= 0.6:
            if agg == "mean":
                aggfunc = "mean"
            elif agg == "sum":
                aggfunc = "sum"
            else:
                aggfunc = "median"

            grouped = (
                df_melt[df_melt["is_numeric"]]
                .groupby([id_col, "variable"])["numeric_value"]
                .agg(aggfunc)
                .reset_index()
            )

            pivot = grouped.pivot(index=id_col, columns="variable", values="numeric_value").fillna(0).reset_index()
            default_title = title or f"{aggfunc} of selected series by {id_col}"
            value_label = "Value"
        else:
            counts = df_melt.dropna(subset=["value"]).groupby([id_col, "variable"]).size().reset_index(name="count")
            pivot = counts.pivot(index=id_col, columns="variable", values="count").fillna(0).reset_index()
            default_title = title or f"Count of values by {id_col}"
            value_label = "count"

    # Reuse CHART_BUILDERS for each series: build a tiny df per series and call the builder
    vars_list = [c for c in pivot.columns if c != id_col]
    traces = []
    used_layout = None

    builder = CHART_BUILDERS.get(chart_type)

    if builder is None:
        # fallback: grouped bars
        for var in vars_list:
            traces.append(
                {
                    "x": pivot[id_col].astype(str).tolist(),
                    "y": pivot[var].tolist(),
                    "type": "bar",
                    "name": var,
                }
            )
        layout = {
            "title": default_title,
            "xaxis": {"title": id_col},
            "yaxis": {"title": value_label},
            "barmode": "group",
        }
        return traces, layout

    for var in vars_list:
        df_series = pivot[[id_col, var]].rename(columns={id_col: id_col, var: var}).copy()

        # Call the single-series builder; pass None for title to avoid overriding
        try:
            series_traces, series_layout = builder(df_series, x_col=id_col, y_col=var, title=None)
        except Exception:
            # If a builder fails for this series, skip it
            continue

        # collect traces
        traces.extend(series_traces)

        # capture a layout from the first successful builder to reuse/merge
        if used_layout is None:
            used_layout = series_layout

    # Compose unified layout
    layout = used_layout or {}
    layout.setdefault("title", default_title)

    multi_series = len(vars_list) > 1

    # Ensure axis titles are sensible for common types
    if chart_type in ("barchart", "stackedbarchart", "linechart", "boxplot"):
        if multi_series:
            layout["xaxis"] = {**(layout.get("xaxis") or {}), "title": id_col}
            layout["yaxis"] = {**(layout.get("yaxis") or {}), "title": value_label}
        else:
            layout.setdefault("xaxis", {"title": id_col})
            layout.setdefault("yaxis", {"title": value_label})
    elif chart_type == "horizonvalclusteredbarchart":
        if multi_series:
            layout["xaxis"] = {**(layout.get("xaxis") or {}), "title": value_label}
            layout["yaxis"] = {
                **(layout.get("yaxis") or {}),
                "title": id_col,
                "automargin": True,
            }
        else:
            layout.setdefault("yaxis", {"title": id_col, "automargin": True})
            layout.setdefault("xaxis", {"title": value_label})
    elif chart_type == "piechart":
        # pie charts typically include titles only
        pass

    # For bar builders set barmode appropriately
    if chart_type == "stackedbarchart":
        layout["barmode"] = "stack"
    elif chart_type in ("barchart", "horizonvalclusteredbarchart"):
        layout.setdefault("barmode", "group")

    return traces, layout


def build_chart(chart_type, df, columns, title, counts_mode=False):

    if chart_type not in CHART_BUILDERS:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    if not columns:
        raise ValueError("No columns selected")

    df = df.copy()

    df = df.where(pd.notnull(df), None)

    if chart_type == "dumbbellchart":
        return _build_dumbbell_chart(df, columns, title, counts_mode)

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

    # CASE 2: two columns → default X vs Y; optional counts across both columns
    elif len(columns) == 2:
        x_col = columns[0]
        y_col = columns[1]

        df_clean = df[[x_col, y_col]].dropna(how="any")

        if counts_mode:
            return _counts_combo_chart(df, columns, chart_type, title)

        return CHART_BUILDERS[chart_type](
            df_clean,
            x_col=x_col,
            y_col=y_col,
            title=title or f"{y_col} vs {x_col}",
        )

    # CASE 3: multiple columns → melt wide → multi-series (counts_mode forces count pivot per column)
    else:
        if counts_mode:
            return _multi_series_melt_chart(df, columns, chart_type, title, counts_only=True)
        return _multi_series_melt_chart(df, columns, chart_type, title, counts_only=False)
