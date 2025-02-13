import os
import logging
import asyncio
import socketio
from fastapi import FastAPI, WebSocket
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from main import App
import datetime
from typing import List


class StatusUpdate():
    def __init__(self, source, level, status, message, details={}):
        self.timestamp = datetime.datetime.now().isoformat()
        self.source = source
        self.level = level
        self.status = status
        self.message = message
        self.details = details

    def jsonify(self):
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "level": self.level,
            "status": self.status,
            "message": self.message,
            "details": self.details
        }


class Command():
    def __init__(self, action, parameters={}):
        self.action = action
        self.parameters = parameters

    def jsonify(self):
        return {
            "action": self.action,
            "parameters": self.parameters
        }

class WebApp:
    """Object-Oriented FastAPI and WebSocket Server for Monitoring."""

    def __init__(self):
        """Initialize the FastAPI app and Socket.IO server."""
        self.monitoring_status = "Idle"
        self.monitoring_active = False
        self.time_to_check = 0  
        self.active_connections: List[WebSocket] = []  # Store connected WebSocket clients
  

        # Initialize FastAPI & Socket.IO
        self.app = FastAPI()
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",
            logger=True,
            engineio_logger=True
        )

        # Serve static files (HTML, CSS, JS)
        self.app.mount("/static", StaticFiles(directory="static"), name="static")

        # Enable CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


        ### WEBSOCKET ENDPOINTS ###

        # Socket for status updates (web_ui.py -> script.js -> index.html)
        @self.app.websocket("/ws/status-updates")
        async def websocket_status_updates(websocket: WebSocket):
            """WebSocket endpoint for pushing status updates to the UI."""
            await websocket.accept()
            self.active_connections.append(websocket)

            try:
                while True:
                    await asyncio.sleep(10)  # Keep connection open
            except Exception:
                pass  # Ignore disconnection errors
            finally:
                self.active_connections.remove(websocket)  # Remove disconnected clients


        # Other sockets probably






        
        ### HTTP ENDPOINTS ###
        
        # Route for serving the index.html file
        @self.app.get("/")
        async def serve_index():
            """Serve the main index.html file."""
            return FileResponse("static/index.html")
        
        # Route for starting monitoring
        @self.app.post("/start-monitoring")
        async def start_monitoring():
            """Start the monitoring process."""
            
            # Logic for starting the monitoring loop

            status_update_start = StatusUpdate(
                source="web_ui",
                level="Program",
                status="Active",
                message="Started Monitoring (No actual logic yet)"
            ).jsonify()

            await self.send_status_update(status_update_start)  # Send update to WebSocket clients

            return status_update_start  # HTTP response

        # Route for stopping monitoring
        @self.app.post("/stop-monitoring")
        async def stop_monitoring():
            """Stop the monitoring process."""
            
            # Logic for stopping the monitoring loop

            status_update_stop = StatusUpdate(
                source="web_ui",
                level="Program",
                status="Idle",
                message="Stopped Monitoring (No actual logic yet)"
            ).jsonify()

            await self.send_status_update(status_update_stop)  # Send update to WebSocket clients

            return status_update_stop

        # Route for directly checking for new videos
        @self.app.post("/video-check")
        async def check_for_new_videos():
            """Check for new videos."""
            
            # Logic for checking for new videos

            status_update_check = StatusUpdate(
                source="web_ui",
                level="Program",
                status="Idle",
                message="Checked for new videos (No actual logic yet)"
            ).jsonify()

            await self.send_status_update(status_update_check)  # Send update to WebSocket clients

            return status_update_check

        # Route for saving new AI instructions
        @self.app.post("/save-ai-instructions")
        async def save_ai_instructions(instructions_field: dict):
            """Save new AI instructions."""
            
            # Logic for saving AI instructions

            status_update_save = StatusUpdate(
                source="web_ui",
                level="Program",
                status="Idle",
                message=f"Saved new AI instructions (No actual logic yet). Instructions: {instructions_field}"
            ).jsonify()

            self.send_status_update(status_update_save)  # Send update to WebSocket clients

            return status_update_save




    # Function that can be called from other modules to send a status update through the WebSocket
    async def send_status_update(self, status_update: dict):
            """Broadcast a status update to all connected WebSocket clients."""
            disconnected_clients = []
            for websocket in self.active_connections:
                try:
                    await websocket.send_json(status_update)
                except Exception:
                    disconnected_clients.append(websocket)

            # Remove disconnected clients
            for client in disconnected_clients:
                self.active_connections.remove(client)    

    def run(self):
        """Run the FastAPI application with Uvicorn."""
        uvicorn.run(self.app, host="0.0.0.0", port=5001, reload=True)        

web_app = WebApp()
fastapi_app = web_app.app



# Run the app if executed as a script
if __name__ == "__main__":    
    uvicorn.run("web_ui:fastapi_app", host="127.0.0.1", port=5001, reload=True)

