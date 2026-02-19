def normalize_xlsx(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df.fillna(0)
    records = df.to_dict(orient="records")
    return records

def parse_salary_value(value):
    if value in ("n.a.", "-", None):
        return None

    if isinstance(value, str) and "," in value:
        parts = value.split(",")
        return float(parts[0].strip()), float(parts[1].strip())

    return float(value), None


def normalize_yaml(data):
    records = []

    for entry in data:
        country = entry["country"]

        for position in ["phd", "postdoc", "prof"]:
            if position not in entry:
                continue

            levels = entry[position]

            for i, level in enumerate(levels):

                # Split comma values if needed
                values = [v.strip() for v in str(level).split(",")]

                numeric_values = []
                for v in values:
                    try:
                        numeric_values.append(float(v))
                    except:
                        continue

                if len(numeric_values) == 1:
                    # Single point
                    records.append({
                        "label": f"{country} - {position}{i+1}",
                        "low": numeric_values[0],
                        "high": None
                    })

                elif len(numeric_values) >= 2:
                    # Dumbbell
                    records.append({
                        "label": f"{country} - {position}{i+1}",
                        "low": numeric_values[0],
                        "high": numeric_values[1]
                    })

    return records

def parse_number(val):
    if val in ("n.a.", "-", None):
        return None
    try:
        return float(val)
    except:
        return None
