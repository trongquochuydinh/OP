def normalize_xlsx(df):
    import pandas as pd
    df = df.replace(r'^\s*$', pd.NA, regex=True)
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")

    return df


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
        country = entry.get("country")

        for position in ["phd", "postdoc", "prof"]:
            if position not in entry:
                continue

            levels = entry[position]

            for i, level in enumerate(levels, start=1):

                low = None
                high = None

                # Case 1: already numeric
                if isinstance(level, (int, float)):
                    low = float(level)

                # Case 2: string like "65328, n.a."
                else:
                    parts = [p.strip() for p in str(level).split(",")]

                    nums = []
                    for p in parts:
                        try:
                            nums.append(float(p))
                        except:
                            continue

                    if len(nums) == 1:
                        low = nums[0]

                    elif len(nums) >= 2:
                        low = nums[0]
                        high = nums[1]

                records.append({
                    "country": country,
                    "position": position,
                    "level": i,
                    "low": low,
                    "high": high
                })

    return records

def parse_number(val):
    if val in ("n.a.", "-", None):
        return None
    try:
        return float(val)
    except:
        return None
