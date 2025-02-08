from flask import Flask, render_template, jsonify
from logging_config import logger
import os
import threading
from main import App  # Import your existing processing class

app = Flask(__name__)

LOG_FILE = "logs/app.log"

if not os.path.exists("logs"):
    os.makedirs("logs")

# Global instance of the App class
main_app = App()
processing_app = main_app.frame_processor


@app.route("/")
def dashboard():
    """Renders the dashboard UI"""
    return render_template("index.html")


@app.route("/status")
def status():
    """Returns the current system status, including processing state and pending files."""
    pending_files = len(os.listdir("unprocessed_videos")) if os.path.exists("unprocessed_videos") else 0
    current_status = getattr(main_app, "status", "Idle - Waiting for next check")

    return jsonify({
        "status": current_status,
        "pending_files": pending_files
    })


@app.route("/main-details")
def main_details():
    """Returns the main details of the app, such as monitoring state."""
    return jsonify({
        "main_status": main_app.status,
        "main_monitoring_active": main_app.monitoring_active,
        "time_to_check": main_app.time_to_check,
        "processing_status": main_app.processing_status
    })


@app.route("/processing-details")
def processing_details():
    """Returns the details of the processing pipeline."""
    return jsonify({
        "processing_video_fps": processing_app.video_fps,
        "processing_analysis_frames_per_second": processing_app.analysis_frames_per_second,
        "processing_analysis_max_frames": processing_app.analysis_max_frames,
        "processing_analysis_batch_size": processing_app.analysis_batch_size,
        "processing_seconds_analyzed": processing_app.seconds_analyzed,
        "processing_minutes_analyzed": processing_app.minutes_analyzed,
        "processing_status": processing_app.processing_status,
        "processing_stages": processing_app.processing_stages
    })


@app.route("/folder-contents")
def folder_contents():
    """Returns the current contents of the unprocessed and processed video folders."""
    unprocessed = os.listdir("unprocessed_videos") if os.path.exists("unprocessed_videos") else []
    processed = os.listdir("processed_videos") if os.path.exists("processed_videos") else []

    return jsonify({
        "unprocessed_videos": unprocessed,
        "processed_videos": processed
    })


@app.route("/logs")
def get_logs():
    """Returns the last N lines of the log file for UI polling."""
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})

    with open(LOG_FILE, "r") as file:
        lines = file.readlines()[-50:]  # Fetch last 50 log lines
        return jsonify({"logs": [line.strip() for line in lines]})


@app.route("/start-monitoring", methods=["POST"])
def start_monitoring():
    """Endpoint to start the monitoring process."""
    print(f"{main_app.monitoring_active = }")
    if not main_app.monitoring_active:
        threading.Thread(target=main_app.start_monitoring, daemon=True).start()
        return jsonify({"status": "Monitoring started"})
    else:
        return jsonify({"status": "Monitoring is already running"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)