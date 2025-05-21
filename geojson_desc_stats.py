import json
import pandas as pd
from pathlib import Path

PROPERTIES = [
    "pothole",
    "pothole_confidence",
    "alligator_cracking",
    "alligator_cracking_confidence",
    "line_cracking",
    "line_cracking_confidence",
    "debris",
    "debris_confidence",
    "road_health_index",
]


"""
Given a GeoJSON file, flatten it to CSV and return quick stats.
"""

def summarize_geojson(in_geojson: str | Path, out_csv: str | Path) -> dict:
    """Flatten GeoJSON → CSV and return quick stats."""
    with open(in_geojson, "r", encoding="utf-8") as f:
        features = json.load(f)["features"]
        records = [{k: feat["properties"].get(k) for k in PROPERTIES} for feat in features]

    df = pd.DataFrame(records)
    # normalize data types
    bool_cols = ["pothole", "alligator_cracking", "line_cracking", "debris"]
    num_cols = [
        "pothole_confidence",
        "alligator_cracking_confidence",
        "line_cracking_confidence",
        "debris_confidence",
        "road_health_index",
    ]

    for col in bool_cols:
        df[col] = df[col].astype(str).str.lower().isin({"yes", "true", "1"})

    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    df.to_csv(out_csv, index=False)

    stats = {"points_total": len(df)}
    for col in bool_cols:
        stats[f"{col}_count"] = df[col].sum()
        stats[f"{col}_rate"] = df[col].mean()

    for col in num_cols:
        stats[f"{col}_mean"] = df[col].mean()

    return stats

# example
if __name__ == "__main__":
    stats = summarize_geojson("all_files.geojson", "all_points_flat.csv")
    print(stats)