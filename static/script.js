console.log("JavaScript Loaded");

/// BUTTONS
const btnStartMonitoring = document.getElementById("btn-start-monitoring");
const btnStopMonitoring = document.getElementById("btn-stop-monitoring");
const btnCheckForChanges = document.getElementById("btn-check-for-changes");
const btnSaveNewAiInstructions = document.getElementById("btn-save-new-ai-instructions");

/// TEXT INPUTS
const inputAiInstructions = document.getElementById("input-ai-instructions");


/// STATUS VALUES
const valueProgramStatus = document.getElementById("value-program-status");
const valueVideoProcessingStatus = document.getElementById("value-video-processing-status");
const valueWoProcessingStatus = document.getElementById("value-wo-processing-status");

let socket;




/// EVENT LISTENERS FOR BUTTONS
btnStartMonitoring.addEventListener("click", () => {
    console.log("Start Monitoring Button Clicked");
    socket = new WebSocket("ws://127.0.0.1:5001/ws/start-monitoring")
});