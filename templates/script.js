/*document.addEventListener("DOMContentLoaded", function() {
    const startBtn = document.getElementById("startMonitoringBtn");
    const stopBtn = document.getElementById("stopMonitoringBtn");

    startBtn.addEventListener("click", function() {
        fetch("/start-monitoring", { method: "POST" })
            .then(response => response.json())
            .then(data => {
                if (data.status === "monitoring_started") {
                    startBtn.style.display = "none";
                    stopBtn.style.display = "inline-block";
                } else {
                    alert("Failed to start monitoring");
                }
            })
            .catch(error => console.error("Error starting monitoring:", error));
    });

    stopBtn.addEventListener("click", function() {
        fetch("/stop-monitoring", { method: "POST" })
            .then(response => response.json())
            .then(data => {
                if (data.status === "monitoring_stopped") {
                    stopBtn.style.display = "none";
                    startBtn.style.display = "inline-block";
                } else {
                    alert("Failed to stop monitoring");
                }
            })
            .catch(error => console.error("Error stopping monitoring:", error));
    });

    // Initial state check
    fetch("/monitoring-status")
        .then(response => response.json())
        .then(data => {
            if (data.monitoring_active) {
                startBtn.style.display = "none";
                stopBtn.style.display = "inline-block";
            } else {
                startBtn.style.display = "inline-block";
                stopBtn.style.display = "none";
            }
        })
        .catch(error => console.error("Error fetching monitoring status:", error));

    // Function to fetch all details and update the UI
    function fetchAllDetails() {
        fetch("/all-details")
            .then(response => response.json())
            .then(data => {
                document.getElementById("main_app_status").innerText = data.main_app_status;
                document.getElementById("main_monitoring_active").innerText = data.main_monitoring_active;
                if (data.processing_active) {
                    document.getElementById("processing-section").classList.remove("hidden");
                    document.getElementById("processing-tracker").innerText = data.processing_details;
                } else {
                    document.getElementById("processing-section").classList.add("hidden");
                }
            })
            .catch(error => console.error("Error fetching all details:", error));
    }

    // Function to fetch status and update the UI
    function fetchStatus() {
        fetch("/status")
            .then(response => response.json())
            .then(data => {
                document.getElementById("status").innerText = data.status;
                document.getElementById("time_to_check").innerText = data.time_to_check;
            })
            .catch(error => console.error("Error fetching status:", error));
    }

    // Function to fetch logs and update the UI
    function fetchLogs() {
        fetch("/logs")
            .then(response => response.json())
            .then(data => {
                document.getElementById("logs").innerHTML = data.logs.join("<br>");
            })
            .catch(error => console.error("Error fetching logs:", error));
    }

    // Function to fetch folder contents and update the UI
    function fetchFolderContents() {
        fetch("/folder-contents")
            .then(response => response.json())
            .then(data => {
                document.getElementById("unprocessedList").innerHTML = 
                    data.unprocessed_videos.length > 0 ? data.unprocessed_videos.join("<br>") : "No pending files";
                document.getElementById("processedList").innerHTML = 
                    data.processed_videos.length > 0 ? data.processed_videos.join("<br>") : "No processed files";
            })
            .catch(error => console.error("Error fetching folder contents:", error));
    }

    // Polling intervals (polling every few seconds)
    setInterval(fetchFolderContents, 5000);
    setInterval(fetchStatus, 1000);
    setInterval(fetchLogs, 5000);
    setInterval(fetchAllDetails, 1000);

    // Initial fetches
    fetchStatus();
    fetchLogs();
    fetchFolderContents();
    fetchAllDetails();
});*/

document.addEventListener("DOMContentLoaded", function() {
    const startBtn = document.getElementById("startMonitoringBtn");
    const stopBtn = document.getElementById("stopMonitoringBtn");
    const idleBadge = document.getElementById("badge-idle");
    const activeBadge = document.getElementById("badge-active");
    const errorBadge = document.getElementById("badge-error");
    const timeToCheckEl = document.getElementById("time_to_check");
    const statusEl = document.getElementById("status");

    // Establish WebSocket connection
    const socket = io("http://localhost:5001");
    const BASE_URL = "http://localhost:5001";


    socket.on("update_status", function(data) {
        // Update status text
        statusEl.innerText = data.status;
        timeToCheckEl.innerText = data.time_to_check > 0 ? `Time to check: ${data.time_to_check}s` : "";

        // Update badges
        idleBadge.style.display = "none";
        activeBadge.style.display = "none";
        errorBadge.style.display = "none";

        if (data.status.includes("Idle")) {
            idleBadge.style.display = "inline-block";
        } else if (data.status.includes("Monitoring active") || data.status.includes("Checking for new files")) {
            activeBadge.style.display = "inline-block";
        } else if (data.status.includes("error") || data.status.includes("stopped due to error")) {
            errorBadge.style.display = "inline-block";
        }
    });

    // Start Monitoring
    startBtn.addEventListener("click", function() {
        fetch(`${BASE_URL}/start-monitoring`, { method: "POST" })
            .then(response => response.json())
            .then(data => {
                if (data.status === "monitoring_started") {
                    startBtn.style.display = "none";
                    stopBtn.style.display = "inline-block";
                } else {
                    alert("Failed to start monitoring");
                }
            })
            .catch(error => console.error("Error starting monitoring:", error));
    });

    // Stop Monitoring
    stopBtn.addEventListener("click", function() {
        fetch(`${BASE_URL}/stop-monitoring`, { method: "POST" })
            .then(response => response.json())
            .then(data => {
                if (data.status === "monitoring_stopped") {
                    stopBtn.style.display = "none";
                    startBtn.style.display = "inline-block";
                } else {
                    alert("Failed to stop monitoring");
                }
            })
            .catch(error => console.error("Error stopping monitoring:", error));
    });
});