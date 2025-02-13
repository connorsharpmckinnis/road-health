console.log("JavaScript Loaded");
let socket;

// CONSTANTS

// // WEBSOCKET-RELATED CONSTANTS
const wsUrl = (window.location.protocol === "https:" ? "wss" : "ws") + "://" + window.location.host + "/ws";


// // BUTTONS
const btnStartMonitoring = document.getElementById("btn-start-monitoring");
const btnStopMonitoring = document.getElementById("btn-stop-monitoring");
const btnCheckForChanges = document.getElementById("btn-check-for-changes");
const btnSaveNewAiInstructions = document.getElementById("btn-save-new-ai-instructions");

// // TEXT INPUTS
const inputAiInstructions = document.getElementById("input-ai-instructions");

// // STATUS VALUES
// // // PROGRAM
const valueProgramStatus = document.getElementById("value-program-status");
// // // VIDEO
const valueVideoProcessingStatus = document.getElementById("value-video-processing-status");
// // // WORK ORDER
const valueWoProcessingStatus = document.getElementById("value-wo-processing-status");
// // // STATUS UPDATE FEED
const subsectionStatusFeed = document.getElementById("subsection-status-feed")


// UTILITY FUNCTIONS
// // HTTP FUNCTIONS
// // // SEND HTTP REQUEST
async function sendHttpRequest(endpoint, method = "POST", body = null) {
    try {
        const response = await fetch(endpoint, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: body ? JSON.stringify(body) : null
        });

        const data = await response.json();
        console.log(`Response from ${endpoint}:`, data);
    } catch (error) {
        console.error(`Error sending request to ${endpoint}:`, error);
    }
}

// // WEBSOCKET FUNCTIONS
// // // ADD STATUS UPDATE TO SUBSECTION-STATUS-FEED
function addStatusUpdate(message) {
    const entry = document.createElement("p");
    entry.className = "card-status-update"
    entry.textContent = `${new Date().toLocaleTimeString()}: ${message}`;

    subsectionStatusFeed.appendChild(entry);

    subsectionStatusFeed.scrollTop = subsectionStatusFeed.scrollHeight;
}

// // // GET WEBSOCKET URL
function getWebSocketUrl(endpoint) {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    return `${protocol}://${host}${endpoint}`;
}


// WEBSOCKET CONNECTIONS
const statusFeedSocket = new WebSocket(wsUrl + "/status-updates");
statusFeedSocket.onopen = () => {
    console.log("Status Feed WebSocket Connected");
};
statusFeedSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("Status Feed WebSocket Message:", data);
    addStatusUpdate(data.message);
};

// EVENT LISTENERS FOR BUTTONS
btnStartMonitoring.addEventListener("click", () => {
    console.log("Start Monitoring Button Clicked");
    sendHttpRequest("/start-monitoring");
});

btnStopMonitoring.addEventListener("click", () => {
    console.log("Stop Monitoring Button Clicked");
    sendHttpRequest("/stop-monitoring");
});

btnCheckForChanges.addEventListener("click", () => {
    console.log("Check for Changes Button Clicked");
    sendHttpRequest("/video-check");
});

btnSaveNewAiInstructions.addEventListener("click", () => {
    console.log("Save New AI Instructions Button Clicked");
    sendHttpRequest("/save-ai-instructions", "POST", { instructions: inputAiInstructions.value });
});