import json
import os
from glob import glob

def classify_cracking_ratio(ratio):
    if ratio == 0:
        return "none"
    elif ratio <= 0.25:
        return "low"
    elif ratio <= 0.5:
        return "medium"
    else:
        return "high"

def classify_severity(value):
    if value >= 1 and value <= 3:
        return "mild"
    elif value >= 4 and value <= 6:
        return "moderate"
    elif value >= 7 and value <= 10:
        return "severe"
    return None

def analyze_geojson_file(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    features = data.get("features", [])
    total_points = len(features)
    if total_points == 0:
        return None

    raveling_frame_count = 0
    upheaval_frame_count = 0
    line_cracking_counts = {"mild": 0, "moderate": 0, "severe": 0}
    longitudinal_cracking_counts = {"mild": 0, "moderate": 0, "severe": 0}
    alligator_cracking_counts = {"mild": 0, "moderate": 0, "severe": 0}

    health_index_sum = 0
    paser_rating_sum = 0
    paser_rating_count = 0
    longitudinal_cracking_frame_count = 0

    for feature in features:
        ai = feature["properties"].get("ai_analysis", {})
        raveling = ai.get("raveling", 0)
        upheaval = ai.get("upheaval", 0)
        line_cracking = ai.get("line_cracking", 0)
        longitudinal_cracking = ai.get("longitudinal_cracking", 0)
        alligator_cracking = ai.get("alligator_cracking", 0)
        paser_rating = ai.get("PASER_rating", 0)

        if raveling > 0:
            raveling_frame_count += 1
        if upheaval > 0:
            upheaval_frame_count += 1

        line_cracking_severity = classify_severity(line_cracking)
        if line_cracking_severity:
            line_cracking_counts[line_cracking_severity] += 1

        longitudinal_cracking_severity = classify_severity(longitudinal_cracking)
        if longitudinal_cracking_severity:
            longitudinal_cracking_counts[longitudinal_cracking_severity] += 1
            longitudinal_cracking_frame_count += 1

        alligator_cracking_severity = classify_severity(alligator_cracking)
        if alligator_cracking_severity:
            alligator_cracking_counts[alligator_cracking_severity] += 1

        health_index_sum += ai.get("road_health_index", 0)

        if paser_rating:
            paser_rating_sum += paser_rating
            paser_rating_count += 1

    raveling_classification = classify_cracking_ratio(raveling_frame_count / total_points)
    upheaval_classification = classify_cracking_ratio(upheaval_frame_count / total_points)
    longitudinal_cracking_percent = classify_cracking_ratio(longitudinal_cracking_frame_count / total_points)

    road_health_avg = round(health_index_sum / total_points / 10, 1)
    paser_rating_avg = round(paser_rating_sum / paser_rating_count, 1) if paser_rating_count > 0 else 0

    return {
        "file": os.path.basename(filepath),
        "line_cracking_counts": line_cracking_counts,
        "longitudinal_cracking_counts": longitudinal_cracking_counts,
        "alligator_cracking_counts": alligator_cracking_counts,
        "raveling_classification": raveling_classification,
        "upheaval_classification": upheaval_classification,
        "longitudinal_cracking_classification": longitudinal_cracking_percent,
        "road_health_avg_0_to_10": road_health_avg,
        "PASER_rating_avg": paser_rating_avg
    }

def process_geojson_directory(directory_path):
    results = []
    preferred_order = [
        "GX010519_20250416_12_33.geojson",
        "GX010523_20250416_12_40.geojson",
        "GX010518_20250416_12_25.geojson",
        "GX010520_20250416_12_49.geojson",
        "GX010525_20250416_12_29.geojson",
        "GX010528_20250416_12_21.geojson",
        "GX010526_20250416_12_35.geojson",
        "GX010532_20250416_12_36.geojson",
        "GX010533_20250416_12_34.geojson",
        "GX010531_20250416_12_27.geojson",
        "GX010530_20250416_12_26.geojson",
        "GX010521_20250416_12_44.geojson",
        "GX010517_20250416_12_16.geojson"
    ]
    for file_path in glob(os.path.join(directory_path, "*.geojson")):
        result = analyze_geojson_file(file_path)
        if result:
            results.append(result)

    results.sort(key=lambda x: preferred_order.index(x["file"]) if x["file"] in preferred_order else len(preferred_order))
    
    return results

# Example usage
if __name__ == "__main__":
    summary = process_geojson_directory("greenway_geojsons")
    for item in summary:
        print(item)