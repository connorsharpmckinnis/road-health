// Connect to the WebSocket server
const socket = io("http://localhost:5001", {
    transports: ["websocket", "polling"],
    withCredentials: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 2000
});

// Function to update status on the web page
function updateStatus(data) {
    const statusDiv = document.getElementById("status");
    statusDiv.innerHTML = `<strong>Checking Box in </strong> ${data.time_to_check || 0}...`;

    // Update the visibility of the status badges
    updateBadgeVisibility(data.status);

}

// Listen for real-time status updates from the server
socket.on("status_update", (data) => {
    console.log("Received status update:", data);
    updateStatus(data);
});

// Handle connection errors
socket.on("connect_error", () => {
    document.getElementById("status").innerHTML = "⚠️ Connection lost. Retrying...";
});

// Function to start monitoring
function startMonitoring() {
    console.log("🔹 Emitting start_monitoring event...");
    socket.emit("start_monitoring");

    const stopBtn = document.getElementById("stopBtn");
    const startBtn = document.getElementById("startBtn");

    startBtn.setAttribute("disabled", "true");
    stopBtn.removeAttribute("disabled");

    startBtn.setAttribute("hidden", "true");
    stopBtn.removeAttribute("hidden");
}

// Function to stop monitoring
function stopMonitoring() {
    const stopBtn = document.getElementById("stopBtn");
    const startBtn = document.getElementById("startBtn");

    console.log("Stop clicked: ", startBtn.disabled, stopBtn.disabled); // Debugging

    socket.emit("stop_monitoring");

    // Properly toggle Shoelace buttons
    startBtn.removeAttribute("disabled");
    stopBtn.setAttribute("disabled", "true");

    startBtn.removeAttribute("hidden");
    stopBtn.setAttribute("hidden", "true");
}

// Function to update status badge visibility
function updateBadgeVisibility(status) {
    status = status || "Idle"; // Default to "Idle" if status is undefined
    console.log("🔹 Updating badge visibility for status:", status); // Debugging

    const badgeIdle = document.getElementById("badge-idle");
    const badgeActive = document.getElementById("badge-active");
    const badgeError = document.getElementById("badge-error");

    if (!badgeIdle || !badgeActive || !badgeError) {
        console.warn("⚠️ One or more status badges not found in the DOM.");
        return;
    }

    // Hide all badges
    badgeIdle.style.display = "none";
    badgeActive.style.display = "none";
    badgeError.style.display = "none";

    // Show only the relevant badge
    if (status === "Idle") {
        badgeIdle.style.display = "inline-block";
    } else if (status === "Active" || status === "Checking for new files...") {
        badgeActive.style.display = "inline-block";
    } else if (status === "Error") {
        badgeError.style.display = "inline-block";
    }
}

// Ensure event listeners are attached after DOM loads
document.addEventListener("DOMContentLoaded", function() {
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");

    if (startBtn && stopBtn) {
        console.log("✅ Start and Stop buttons found. Adding event listeners.");
        startBtn.addEventListener("click", startMonitoring);
        stopBtn.addEventListener("click", stopMonitoring);
    } else {
        console.log("❌ ERROR: Buttons not found in DOM.");
    }
});