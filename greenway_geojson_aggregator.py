import json
import os
from glob import glob

def classify_cracking_ratio(ratio):
    if ratio == 0:
        return "none"
    elif ratio < 0.25:
        return "low"
    elif ratio < 0.5:
        return "medium"
    else:
        return "high"

def analyze_geojson_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    features = data.get("features", [])
    total_points = len(features)
    if total_points == 0:
        return None

    alligator_cracking_count = 0
    line_cracking_count = 0
    health_index_sum = 0

    for feature in features:
        ai = feature["properties"].get("ai_analysis", {})
        if ai.get("alligator_cracking", "").lower() == "yes":
            alligator_cracking_count += 1
        if ai.get("line_cracking", "").lower() == "yes":
            line_cracking_count += 1
        health_index_sum += ai.get("road_health_index", 0)

    line_cracking_ratio = line_cracking_count / total_points
    road_health_avg = round(health_index_sum / total_points / 10, 1)

    return {
        "file": os.path.basename(filepath),
        "alligator_cracking_count": alligator_cracking_count,
        "line_cracking_level": classify_cracking_ratio(line_cracking_ratio),
        "road_health_avg_0_to_10": road_health_avg
    }

def process_geojson_directory(directory_path):
    results = []
    for file_path in glob(os.path.join(directory_path, "*.geojson")):
        result = analyze_geojson_file(file_path)
        if result:
            results.append(result)
    return results

# Example usage
if __name__ == "__main__":
    summary = process_geojson_directory("greenway_geojsons")
    for item in summary:
        print(item)