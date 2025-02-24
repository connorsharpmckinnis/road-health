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
const valueProgramStatus = document.getElementById("badge-program-status");
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

// // // DISPLAY TEMP BADGE FOR 1 SECOND
function showTempBadge(message) {
    const badge = document.getElementById("badge-box-check");
    
    // Wait to show badge for 1 second (until actual 0)
    
    badge.hidden = false;
    
    
    // Hide badge after 1 second
    setTimeout(() => {
        badge.hidden = true;
    }, 1000);
}

// // // UPDATE PROGRAM STATUS
function updateProgramStatus(updateData) {
    if (updateData.status === "Active") {
        valueProgramStatus.classList.remove("bg-warning");
        valueProgramStatus.classList.add("bg-primary");
        countdown = `(${updateData.details.countdown || null})`;
        valueProgramStatus.textContent = `${updateData.status} ${countdown}`;
    } else if (updateData.status === "Processing") {
        valueProgramStatus.classList.remove("bg-primary");
        valueProgramStatus.classList.add("bg-success");
        valueProgramStatus.textContent = "Processing (Monitoring Paused)";
    } else {
        valueProgramStatus.classList.remove("bg-primary");
        valueProgramStatus.classList.add("bg-warning");
        valueProgramStatus.textContent = updateData.status;
    }
}

// Helper to create a card and prepend it to the container with a fade-in effect
function createCard(id, header, bodyContent, container, imageHTML = "") {
    let card = document.getElementById(id);
    const cardHTML = `
        <h4 class="card-header">${header}</h4>
        <div class="card-body">
            ${imageHTML}
            ${bodyContent}
        </div>
    `;
     
    if (card) {
        card.classList.remove("visible"); // Reset visibility for re-animation
        void card.offsetWidth; // Force reflow to trigger transition
        card.innerHTML = cardHTML;
    } else {
        card = document.createElement("div");
        card.className = "card col-md-6"; // Initially not 'visible' for transition
        card.id = id;
        card.innerHTML = cardHTML;
        container.prepend(card);
    }

    // Apply the 'visible' class to trigger the transition after a short delay
    setTimeout(() => {
        card.classList.add("visible");
    }, 10);
}

// Helper to create badge with status styles
function getBadgeClass(status) {
    switch (status) {
        case "In Progress": return "badge bg-primary";
        case "Complete": return "badge bg-success";
        default: return "badge bg-secondary";
    }
}

// Add status update card to feed
function addStatusUpdateCard(updateData) {
    const content = `
        <p class="card-text">
            <span class="text-white">${updateData.source}</span> | 
            <span class="text-white">${updateData.message}</span>
            
        </p>
    `;
    createCard(`status-${Date.now()}`, new Date().toLocaleTimeString(), content, subsectionStatusFeed);
    subsectionStatusFeed.scrollTop = 0;
}

// Update or add video processing card
function updateVideoProcessingCard(updateData) {
    if (!updateData.details?.video_file) return;

    const videoFile = updateData.details.video_file;
    const progress = updateData.details.progress || "0%";
    const status = updateData.status || "Pending";
    const stage = updateData.details.stage || "Unknown";

    let activeModifiers = "";
    if (updateData.status == "In Progress") {
        activeModifiers = "progress-bar-striped progress-bar-animated bg-primary";
    } else if (updateData.status === "Complete") {
        activeModifiers = "bg-success";
    } else {
        activeModifiers = "bg-secondary";
    }

    const progressBar = `
        <div class="progress" style="height: 30px;">
            <div class="progress-bar ${activeModifiers}" 
                role="progressbar" 
                style="width: ${progress};"
                aria-valuenow="${parseInt(progress)}"
                aria-valuemin="0" 
                aria-valuemax="100">
                ${progress}
            </div>
        </div>
    `;

    const content = `
        <h2 class="card-title"><em>${status}</em></h2>
        <p class="${getBadgeClass(status)}">${stage}</p>
        ${progressBar}
    `;

    createCard(`video-${videoFile}`, videoFile, content, videoSection);
}

// Update or add work order processing card
function updateWorkOrderProcessingCard(updateData) {
    const woId = updateData.details.work_order_id;
    const imageHTML = updateData.details.image_base64 
        ? `<img src="data:image/jpeg;base64,${updateData.details.image_base64}" 
                 alt="Image of the detected issue"
                 class="card-img-top" 
                 style="width: 300px; height: 130px;">`
        : "";

    const content = `
        <h2 class="card-title"><em>${updateData.message}</em></h2>
        <p class="card-text"><em>Id: ${woId}</em></p>
        <p class="card-text">${updateData.details.ai_analysis}</p>
    `;

    createCard(`wo-${woId}`, "Work Order Created", content, woSection, imageHTML);
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
        updateProgramStatus(data);
    } else {
        console.warn("Received unknown update type:", data);
    }

};

// EVENT LISTENERS FOR BUTTONS
btnStartMonitoring.addEventListener("click", () => {
    console.log("Start Monitoring Button Clicked");
    sendHttpRequest("/start-monitoring");
    updateData = {"message": "Monitoring Started", "source": "Web UI button click: 'btnStartMonitoring'"};
    addStatusUpdateCard(updateData);
    btnStartMonitoring.disabled = true;
    btnStopMonitoring.disabled = false;
});

btnStopMonitoring.addEventListener("click", () => {
    console.log("Stop Monitoring Button Clicked");
    sendHttpRequest("/stop-monitoring");
    updateData = {"message": "Monitoring Stopped", "source": "Web UI button click: 'btnStopMonitoring'"};
    addStatusUpdateCard(updateData);
    btnStartMonitoring.disabled = false;
    btnStopMonitoring.disabled = true;
});

btnCheckForChanges.addEventListener("click", () => {
    console.log("Check for Changes Button Clicked");
    sendHttpRequest("/video-check");
    updateData = {"message": "Video Check Requested", "source": "Web UI button click: 'btnCheckForChanges'"};
    addStatusUpdateCard(updateData);
});

btnSaveNewAiInstructions.addEventListener("click", () => {
    console.log("Save New AI Instructions Button Clicked");
    sendHttpRequest("/save-ai-instructions", "POST", { instructions: inputAiInstructions.value });
    updateData = {"message": "AI Instructions Updated", "source": "Web UI button click: 'btnSaveNewAiInstructions'"};
    addStatusUpdateCard(updateData);
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