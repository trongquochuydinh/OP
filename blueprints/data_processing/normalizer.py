import pandas as pd


def normalize_xlsx(df):
    cleaned_df = df.replace(r"^\s*$", pd.NA, regex=True)
    cleaned_df = cleaned_df.dropna(axis=1, how="all")
    cleaned_df = cleaned_df.dropna(axis=0, how="all")
    cleaned_df = cleaned_df.reset_index(drop=True)

    return cleaned_df


def parse_number(value):
    if value in ("n.a.", "-", "", None):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        value_str = str(value).replace(" ", "").replace(",", ".")
        try:
            return float(value_str)
        except (TypeError, ValueError):
            return None


def normalize_yaml(data):
    records = []

    if not isinstance(data, list):
        return pd.DataFrame(records)

    for entry in data:
        if not isinstance(entry, dict):
            continue

        country = entry.get("country")

        for position in ("phd", "postdoc", "prof"):
            levels = entry.get(position)
            if not isinstance(levels, list):
                continue

            for level_index, level_value in enumerate(levels, start=1):
                low = None
                high = None

                if isinstance(level_value, (int, float)):
                    low = float(level_value)
                else:
                    values = [parse_number(part.strip()) for part in str(level_value).split(",")]
                    numeric_values = [value for value in values if value is not None]

                    if len(numeric_values) == 1:
                        low = numeric_values[0]
                    elif len(numeric_values) >= 2:
                        low = numeric_values[0]
                        high = numeric_values[1]

                records.append(
                    {
                        "country": country,
                        "position": position,
                        "level": level_index,
                        "low": low,
                        "high": high,
                    }
                )

    return pd.DataFrame(records)


def normalize_parsed_payload(parsed_file):
    file_type = parsed_file["type"]
    raw_data = parsed_file["data"]

    if file_type == "xlsx":
        normalized_df = normalize_xlsx(raw_data)
    elif file_type == "yaml":
        normalized_df = normalize_yaml(raw_data)
    else:
        raise ValueError(f"Unsupported parsed type: {file_type}")

    return {
        "type": file_type,
        "dataframe": normalized_df,
        "columns": list(normalized_df.columns),
        "row_count": len(normalized_df),
        "preview": normalized_df.head(5).fillna("").to_dict(orient="records"),
    }
