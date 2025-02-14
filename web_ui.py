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
    def __init__(self, source, level, type, status, message, details={}):
        self.timestamp = datetime.datetime.now().isoformat()
        self.source = source
        self.level = level
        self.type = type
        self.status = status
        self.message = message
        self.details = details

    def jsonify(self):
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "level": self.level,
            "type": self.type,
            "status": self.status,
            "message": self.message,
            "details": self.details
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
            except asyncio.CancelledError:
                print("WebSocket connection closed due to server shutdown.")
            except Exception as e:
                logging.error(f"WebSocket error: {e}")
            finally:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)






        
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

            await self.send_status_update(source='start_monitoring()')  # Send update to WebSocket clients

            return True  # HTTP response

        # Route for stopping monitoring
        @self.app.post("/stop-monitoring")
        async def stop_monitoring():
            """Stop the monitoring process."""
            
            # Logic for stopping the monitoring loop

            await self.send_status_update(source='stop_monitoring()')  # Send update to WebSocket clients

            return True

        # Route for directly checking for new videos
        @self.app.post("/video-check")
        async def check_for_new_videos():
            """Check for new videos."""
            
            # Logic for checking for new videos

            await self.send_status_update(source='check-for-new-videos()', type='Video', details={"video_file": "Test Video 123"})  # Send update to WebSocket clients

            return True

        # Route for saving new AI instructions
        @self.app.post("/save-ai-instructions")
        async def save_ai_instructions(instructions_field: dict):
            """Save new AI instructions."""
            
            # Logic for saving AI instructions

            await self.send_status_update(source='save_ai_instructions()', type='Temp')  # Send update to WebSocket clients

            return True

       
       
        ### ### HTTP ENDPOINTS FOR TESTS ### ###

        # Route for testing the program status
        @self.app.post("/test-program-status")
        async def test_program_status():
            """Test the program status."""
            
            # Logic for testing the program status

            await self.send_status_update(source='test_program_status()', type='Program')

        # Route for testing the video processing status
        @self.app.post("/test-video-status")
        async def test_video_status():
            """Test the video processing status."""
            
            # Logic for testing the video processing status

            await self.send_status_update(source='test_video_status()', type='Video', details={"video_file": "Test Video 123", "progress": "50%"})

        # Route for testing the work order status
        @self.app.post("/test-wo-status")
        async def test_wo_status():
            """Test the work order status."""
            
            # Logic for testing the work order status

            await self.send_status_update(source='test_wo_status()', type='WorkOrder', details={"video_file": "WO123", "wo_count": "2"})

        # Route for testing the feed status
        @self.app.post("/test-feed-status")
        async def test_feed_status():
            """Test the feed status."""
            
            # Logic for testing the feed status

            await self.send_status_update(source='test_feed_status()', type='Feed', message="Action has been taken somewhere", status="Active")


    # Function that can be called from other modules to send a status update through the WebSocket
    async def send_status_update(self, source:str='Default Source', level:str='Default Level', type:str='Feed', status:str='Default Status', message:str='Default Message', details:dict={}):
            """Broadcast a status update to all connected WebSocket clients."""
            disconnected_clients = []
            
            status_update = StatusUpdate(source, level, type, status, message, details).jsonify()
            
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

