import os
import json
from collections import defaultdict

class JsonAggregator:
    def __init__(self, input_folder, output_file="overview.json"):
        """
        Initializes the JsonAggregator with the folder containing JSON files and the output file name.
        
        :param input_folder: Path to the folder containing processed JSON files.
        :param output_file: Name of the file to save the aggregated results.
        """
        self.input_folder = input_folder
        self.output_file = output_file

    def aggregate_results(self):
        """
        Aggregates the results from JSON files in the input folder and generates an overview.
        
        :return: A dictionary containing aggregated statistics.
        """
        stats = {
            "pothole": {"yes": 0, "pothole_frames": [], "no": 0, "confidence_total": 0, "confidence_count": 0},
            "alligator_cracking": {"yes": 0, "no": 0, "confidence_total": 0, "confidence_count": 0},
            "line_cracking": {"yes": 0, "no": 0, "confidence_total": 0, "confidence_count": 0},
            "debris": {"yes": 0, "no": 0, "confidence_total": 0, "confidence_count": 0},
            "road_health_index": {"total": 0, "count": 0},
        }

        for filename in os.listdir(self.input_folder):
            if filename.endswith(".json"):
                filepath = os.path.join(self.input_folder, filename)
                with open(filepath, "r") as file:
                    data = json.load(file)
                    analysis = data.get("ai_analysis", {})
                    
                    self._update_stats(stats, analysis, "pothole", "pothole_confidence", filename)
                    self._update_stats(stats, analysis, "alligator_cracking", "alligator_cracking_confidence")
                    self._update_stats(stats, analysis, "line_cracking", "line_cracking_confidence")
                    self._update_stats(stats, analysis, "debris", "debris_confidence")

                    if "road_health_index" in analysis:
                        stats["road_health_index"]["total"] += analysis["road_health_index"]
                        stats["road_health_index"]["count"] += 1

        overview = self._generate_overview(stats)
        self._save_overview(overview)
        return overview

    @staticmethod
    def _update_stats(stats, analysis, key, confidence_key, filename=None):
        """
        Updates the statistics for a specific issue type.

        :param stats: The statistics dictionary to update.
        :param analysis: The analysis data from the JSON file.
        :param key: The key representing the issue type (e.g., "pothole").
        :param confidence_key: The key representing the confidence value for the issue type.
        :param filename: The filename of the current JSON file being processed.
        """
        if key in analysis:
            stats[key][analysis[key]] += 1
            stats[key]["confidence_total"] += analysis.get(confidence_key, 0)
            stats[key]["confidence_count"] += 1
            if key == "pothole" and analysis[key] == "yes" and filename:
                stats[key]["pothole_frames"].append(f"{filename} ({analysis[confidence_key]})")

    @staticmethod
    def _generate_overview(stats):
        """
        Generates an overview dictionary based on the aggregated statistics.

        :param stats: The aggregated statistics dictionary.
        :return: A dictionary containing the overview.
        """
        return {
            "pothole": JsonAggregator._compute_statistics(stats["pothole"]),
            "alligator_cracking": JsonAggregator._compute_statistics(stats["alligator_cracking"]),
            "line_cracking": JsonAggregator._compute_statistics(stats["line_cracking"]),
            "debris": JsonAggregator._compute_statistics(stats["debris"]),
            "road_health_index": {
                "average": stats["road_health_index"]["total"] / stats["road_health_index"]["count"]
                if stats["road_health_index"]["count"] > 0 else 0
            }
        }

    @staticmethod
    def _compute_statistics(data):
        """
        Computes statistics for a specific issue type.

        :param data: The data dictionary for the issue type.
        :return: A dictionary containing statistics for the issue type.
        """
        result = {
            "yes_count": data["yes"],
            "no_count": data["no"],
            "average_confidence": data["confidence_total"] / data["confidence_count"]
            if data["confidence_count"] > 0 else 0
        }
        if "pothole_frames" in data:
            result["pothole_frames"] = data["pothole_frames"]
        return result

    def _save_overview(self, overview):
        """
        Saves the overview to a JSON file.

        :param overview: The overview dictionary to save.
        """
        with open(self.output_file, "w") as outfile:
            json.dump(overview, outfile, indent=4)
        print(f"Overview generated and saved to {self.output_file}.")

# Usage Example
if __name__ == "__main__":
    aggregator = JsonAggregator(input_folder="processed_frames", output_file="overview.json")
    overview = aggregator.aggregate_results()
    print("Overview:")
    print(json.dumps(overview, indent=4))