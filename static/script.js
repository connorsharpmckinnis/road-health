console.log("JavaScript Loaded");

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

// // STATUS SECTIONS
// // // PROGRAM
const valueProgramStatus = document.getElementById("value-program-status");
// // // VIDEO PROCESSING CARD SECTION
const valueVideoStatus = document.getElementById("value-video-status");
const videoSection = document.getElementById("subsection-video-cards");
// // // STATUS UPDATE FEED
const subsectionStatusFeed = document.getElementById("subsection-status-feed")
// // // WORK ORDER CARD SECTION
const woSection = document.getElementById("subsection-wo-cards");


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
// // // ADD STATUS UPDATE TO SUBSECTION-STATUS-FEED (Non-Card)
function addStatusUpdate(message) {
    const entry = document.createElement("p");
    entry.className = "card"
    entry.textContent = `${new Date().toLocaleTimeString()}: ${message}`;

    subsectionStatusFeed.appendChild(entry);

    subsectionStatusFeed.scrollTop = subsectionStatusFeed.scrollHeight;
}

// // // DISPLAY TEMP BADGE FOR 1 SECOND
function showTempBadge(message) {
    const badge = document.getElementById("temp-badge");
    badge.textContent = message;
    badge.style.display = "block";

    // Hide badge after 1 second
    setTimeout(() => {
        badge.style.display = "none";
    }, 1000);
}

// // // ADD STATUS UPDATE CARD TO FEED
function addStatusUpdateCard(updateData) {
    
    // Create a new card
    const entry = document.createElement("div");
    newCard.className = "card mb-3";
    entry.className = "card";  // Add CSS later to make it look nice

    // Fill in the details from JSON
    entry.innerHTML = `
        <p class="card-title"><strong>${new Date().toLocaleTimeString()}:</strong> ${updateData.message}</p>
        <p class="card-text"><em>Source:</em> ${updateData.source}</p>
        <p class="card-text"><em>Status:</em> ${updateData.status}</p>
    `;

    // Append the new status update
    subsectionStatusFeed.appendChild(entry);

    // Auto-scroll to the latest update
    subsectionStatusFeed.scrollTop = subsectionStatusFeed.scrollHeight;
}

// // // UPDATE OR ADD VIDEO PROCESSING CARD
function updateVideoProcessingCard(updateData) {
    if (!updateData.details || !updateData.details.video_file) {
        console.warn("Invalid video update data:", updateData);
        return;
    }

    // Extract video filename
    const videoFile = updateData.details.video_file;
    const progress = updateData.details.progress || "N/A";
    const stage = updateData.details.stage || "Unknown";
    const status = updateData.status || "Pending";

    // Check if a card for this video already exists
    let existingCard = document.getElementById(`video-${videoFile}`);

    if (existingCard) {
        // ✅ Update existing card content
        existingCard.innerHTML = `
            <h3 class="card-title">File: ${videoFile}</h3>
            <p class="card-text"><em>Status:</em> ${status}</p>
            <p class="card-text"><em>Stage:</em> ${stage}</p>
            <div class="progress">
                <div class="progress-bar bg-info" role="progressbar" style="width: ${progress};">
                    ${progress}
                </div>
            </div>
        `;
    } else {
        // ✅ Create a new card if it doesn't exist
        const newCard = document.createElement("div");
        newCard.className = "card mb-3";
        newCard.className = "card";
        newCard.id = `video-${videoFile}`;

        newCard.innerHTML = `
            <h3 class="card-title">File: ${videoFile}</h3>
            <p class="card-text"><em>Status:</em> ${status}</p>
            <p class="card-text"><em>Stage:</em> ${stage}</p>
            <div class="progress">
                <div class="progress-bar bg-info" role="progressbar" style="width: ${progress};">
                    ${progress}
                </div>
            </div>
        `;

        videoSection.appendChild(newCard);
    }
}

// // // UPDATE OR ADD WORK ORDER PROCESSING CARD
function updateWorkOrderProcessingCard(updateData) {
    const existingCard = document.getElementById(`wo-${updateData.details.video_file}`);

    if (existingCard) {
        // Update existing card
        existingCard.innerHTML = `
            <h3 class="card-title">File: ${updateData.details.video_file}</h3>
            <p class="card-text"><em>Status:</em> ${updateData.status}</p>
            <p class="card-text"><em>Work Orders Created:</em> ${updateData.details.wo_count || "N/A"}</p>
        `;
    } else {
        // Create a new card
        const newCard = document.createElement("div");
        newCard.className = "card mb-3";
        newCard.className = "card";
        newCard.id = `wo-${updateData.details.video_file}`;

        newCard.innerHTML = `
            <h3 class="card-title">File: ${updateData.details.video_file}</h3>
            <p class="card-text"><em>Status:</em> ${updateData.status}</p>
            <p class="card-text"><em>Work Orders Created:</em> ${updateData.details.wo_count || "N/A"}</p>
        `;

        woSection.appendChild(newCard);
    }
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

    // Route to html elements depending on the data.type
    if (data.type === "Feed") {
        addStatusUpdateCard(data);
    } else if (data.type === "Temp") {
        showTempBadge(data.message);
    } else if (data.type === "Video") {
        if (data.level === "Section") {
            valueVideoStatus.textContent = data.message;
        } else {
            updateVideoProcessingCard(data);
        }
    } else if (data.type == "WorkOrder") {
        updateWorkOrderProcessingCard(data);
    } else if (data.type === "Program") {
        countdown = `(${data.details.countdown || null})`;
        valueProgramStatus.textContent = `${data.status} ${countdown}`;
    } else {
        console.warn("Received unknown update type:", data);
    }

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

// // TEST BUTTON EVENT LISTENERS
const btnProgramTest = document.getElementById("btn-test-program-status");
const btnVideoTest = document.getElementById("btn-test-video-status");
const btnWOTest = document.getElementById("btn-test-wo-status");
const btnFeedTest = document.getElementById("btn-test-feed-status");

btnProgramTest.addEventListener("click", () => {
    console.log("Test Program Status Button Clicked");
    sendHttpRequest("/test-program-status");
});

btnVideoTest.addEventListener("click", () => {
    console.log("Test Video Status Button Clicked");
    sendHttpRequest("/test-video-status");
});

btnWOTest.addEventListener("click", () => {
    console.log("Test Work Order Status Button Clicked");
    sendHttpRequest("/test-wo-status");
});

btnFeedTest.addEventListener("click", () => {
    console.log("Test Feed Status Button Clicked");
    sendHttpRequest("/test-feed-status");
});