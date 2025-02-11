// Connect to the WebSocket server
const socket = io("http://localhost:5001", {  // Use /ws instead of /socket.io
    transports: ["websocket", "polling"],  // Allow WebSockets & polling
    withCredentials: true,  // Allow cross-origin cookies if needed
    reconnectionAttempts: 5,  // Limit reconnection attempts
    reconnectionDelay: 2000   // Wait 2 seconds before retrying
});

// Function to update status on the web page
function updateStatus(data) {
    const statusDiv = document.getElementById("status");
    statusDiv.innerHTML = `Status: ${data.status || data.message} <br> Time Left: ${data.time_to_check || 0}`;
}

// Listen for real-time status updates from the server
socket.on("status_update", (data) => {
    updateStatus(data);
});

// Function to start monitoring
function startMonitoring() {
    socket.emit("start_monitoring");
}

// Function to stop monitoring
function stopMonitoring() {
    socket.emit("stop_monitoring");
}

// Wait until the document is fully loaded before attaching event listeners
document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("startBtn").addEventListener("click", startMonitoring);
    document.getElementById("stopBtn").addEventListener("click", stopMonitoring);
});