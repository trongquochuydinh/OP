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
                if isinstance(level, list):
                    values = level
                else:
                    # handle "65328, n.a."
                    values = [v.strip() for v in str(level).split(",")]

                # filter numeric values
                nums = []
                for v in values:
                    try:
                        nums.append(float(v))
                    except:
                        continue

                if len(nums) >= 2:
                    records.append({
                        "label": f"{country} - {position}{i+1}",
                        "low": nums[0],
                        "high": nums[1]
                    })

    return records

def parse_number(val):
    if val in ("n.a.", "-", None):
        return None
    try:
        return float(val)
    except:
        return None
