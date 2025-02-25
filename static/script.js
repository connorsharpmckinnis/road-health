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
function createCard(id, header, bodyContent, container, imageHTML = "", url = "") {
    let card = document.getElementById(id);
    if (url !== "") {
        bodyContent += `<a href="${url}" class="btn btn-primary">View Details</a>`;
    }
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
    const url = updateData.details.url || "";

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

    createCard(`video-${videoFile}`, videoFile, content, videoSection, url=url);
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

// INFO SECTION SHENANIGANS

function showInfo(section) {
    const infoPanel = document.querySelector('.info-panel');
    const resizeHandle = document.createElement('div');
    resizeHandle.classList.add('resize-handle');
    infoPanel.appendChild(resizeHandle);

    // Make the panel resizable
    resizeHandle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        document.addEventListener('mousemove', resizePanel);
        document.addEventListener('mouseup', () => {
            document.removeEventListener('mousemove', resizePanel);
        });
    });

    function resizePanel(e) {
        const newWidth = window.innerWidth - e.clientX;
        // Allow resizing between 200px and 80% of the viewport width
        const maxWidth = window.innerWidth * 0.8; // 80% of viewport
        if (newWidth > 200 && newWidth < maxWidth) {
            infoPanel.style.width = `${newWidth}px`;
        }
    }

    // Optional: Dynamically adjust font size based on panel width
    window.addEventListener('resize', () => {
        const panelWidth = infoPanel.clientWidth;
        const newFontSize = Math.max(14, Math.min(24, panelWidth / 20));
        infoPanel.style.fontSize = `${newFontSize}px`;
    });
    const infoContent = document.getElementById('info-content');

    // Check if the panel is already open with the same content
    if (infoPanel.classList.contains('active') && infoContent.dataset.currentSection === section) {
        // If so, close it instead of reopening
        infoPanel.classList.remove('active');
        return;
    }

    // Define content for each section
    const content = {
        'program-info': `
            <section class="program-info">
                <h2>Program Information</h2>
                <div class="program-description">
                    <p>
                        The Road Health Analyzer evaluates road conditions using video footage collected by solid waste trucks.
                        By leveraging AI and automated analysis, this system reduces the need for manual road inspections, allowing 
                        Public Works teams to focus resources on targeted repairs and maintenance.
                    </p>
                    <p>
                        Future expansions can apply this design to other use-cases such as signage issues, green space monitoring, 
                        or event management.
                    </p>
                </div>
                
                <div class="system-features">
                    <h3>Identified Road Issues:</h3>
                    <ul>
                        <li>Potholes</li>
                        <li>Line cracks</li>
                        <li>'Alligator' cracking</li>
                        <li>Debris</li>
                    </ul>
                    <p>
                        The system automatically generates AssetOptics-based Work Orders in Salesforce when a pothole is detected, 
                        enabling proactive maintenance and awareness.
                    </p>
                </div>
                
                <div class="image-container">
                    <img src="/static/road-health-pothole-image.jpg" 
                        alt="Pothole Image" 
                        style="width:100%; height:auto; border-radius:8px;">
                </div>
            </section>
        `,
        'video-processing': `
            <section>
                <h2>Video Processing</h2>
                
                <p>
                    Video processing involves analyzing footage frame-by-frame to detect road issues. 
                    Going from raw video to flagged potholes is a complex process:
                </p>
                
                <div class="process-steps">
                    <h3>Processing Steps:</h3>
                    <ul>
                        <li>Store video in Box</li>
                        <li>Extract GPS coordinate path</li>
                        <li>Extract frames from footage</li>
                        <li>Match frames to closest GPS point</li>
                        <li>Prepare images in batches for the AI</li>
                        <li>Process structured AI responses</li>
                        <li>Assign analyses to correct frames</li>
                        <li>Select frames marked 'likely pothole' (≥ 0.9)</li>
                    </ul>
                </div>
                
                <p>
                    Future projects can take advantage of the easy instruction- and response-switching system to quickly configure 
                    an AI analyzer to look at new types of data (images, text, audio) and look for new things 
                    (people, objects, specific words, etc.).
                </p>
                
                <div class="code-block">
                    <h3>Example AI Instruction & Response Policy:</h3>
                    <pre>
            <code-text>
Instruction: "Please analyze these images and share your expert road health analyses, adhering to the JSON schema provided."

Response policy: 
    "required": [
        "file_id",
        "pothole",
        "pothole_confidence",
        "alligator_cracking",
        "alligator_cracking_confidence",
        "line_cracking",
        "line_cracking_confidence",
        "debris",
        "debris_confidence",
        "summary",
        "road_health_index"
    ]
            </code-text>
                    </pre>
                </div>
            </section>
        `,
        'work-orders': `
            <section class="work-orders">
    <h2>Work Orders</h2>

    <div class="work-order-description">
        <p>
            When a pothole is confidently detected by the AI, a Work Order is created automatically in Salesforce, 
            allowing Public Works teams to efficiently evaluate and proactively dispatch repair crews. 
            This automation helps reduce manual reporting and speeds up the maintenance response process.
        </p>
        <p>
            Salesforce's AssetOptics Work Orders include:
        </p>
        <ul>
            <li><strong>AI Analysis:</strong> Automated analysis of road images to identify maintenance needs.</li>
            <li><strong>Precise Location:</strong> The exact location of the pothole, accurate to a 9x9' area.</li>
            <li><strong>Street Segment Information:</strong> The nearest Salesforce street segment Location.</li>
            <li><strong>Visual Evidence:</strong> The image of the detected road issue, provided directly in the work order.</li>
        </ul>
    </div>

    <div class="work-order-image">
        <img src="/static/road-health-wo-screenshot.png" 
             alt="Work Order Screenshot" 
             style="width:100%; height:auto; border-radius:8px;">
    </div>

    <div class="work-order-automation">
        <p>
            The system's automations streamline notifications, review processes, and dispatch or dismissal actions. 
            This ensures Public Works staff can handle tasks efficiently within their existing Salesforce app, 
            minimizing training requirements and maximizing productivity.
        </p>
        <p>
            <strong>Future Potential:</strong> The same automation system can be extended to support other 
            maintenance tasks, such as addressing debris, evaluating sidewalk conditions, or identifying signage issues.
        </p>
    </div>
</section>
        `,
        'controls': `
            <section class="controls">
    <h2>Controls</h2>

    <div class="controls-description">
        <p>
            During the pilot phase, the system operates on a periodic check cycle, ensuring new videos are processed 
            as soon as possible. This approach provides near-real-time analysis while maintaining a straightforward 
            setup that supports proof-of-concept testing.
        </p>
        <p>
            The long-term vision involves a fully automated upload and processing system, triggered automatically 
            when GoPro devices connect to the Public Works Wi-Fi network upon vehicle return to base. 
            This upgrade will create a seamless and hands-off data ingestion process, enhancing overall efficiency.
        </p>
    </div>

    <div class="future-vision">
        <h3>Future Automation Plans:</h3>
        <ul>
            <li><strong>GoPro Integration:</strong> Automatic detection of GoPro devices via Wi-Fi connections.</li>
            <li><strong>Real-Time Processing:</strong> Immediate initiation of video analysis upon data upload.</li>
            <li><strong>Smart Triggers:</strong> Enable data analysis only when specific conditions are met (e.g., vehicle in depot).</li>
            <li><strong>Scalability:</strong> The system's modular design will allow adding new monitoring devices with minimal setup.</li>
        </ul>
    </div>
</section>
        `
    };

    // Set the content based on the section requested
    infoContent.innerHTML = content[section] || '<p>No information available.</p>';
    infoContent.dataset.currentSection = section; // Store the current section
    
    // Show the panel
    infoPanel.classList.add('active');
}

// Close the info panel
document.getElementById('btn-close-info').onclick = () => {
    document.getElementById('info-panel').classList.remove('active');
};