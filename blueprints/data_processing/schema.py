def detect_schema(records):
    if not records:
        return {"dimensions": [], "measures": []}

    sample = records[0]
    dimensions = []
    measures = []

    for key, value in sample.items():
        if isinstance(value, (int, float)) or value is None:
            measures.append(key)
        else:
            dimensions.append(key)

    return {
        "dimensions": dimensions,
        "measures": measures
    }
