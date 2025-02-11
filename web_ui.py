import os
import logging
import asyncio
import socketio
from fastapi import FastAPI
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware



class MonitoringApp:
    """Object-Oriented FastAPI and WebSocket Server for Monitoring."""

    def __init__(self):
        """Initialize the FastAPI app and Socket.IO server."""
        self.monitoring_status = "Idle"
        self.monitoring_active = False
        self.time_to_check = 0

        # Initialize FastAPI & Socket.IO
        self.app = FastAPI()
        self.sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins="*",  # Allow all origins
            logger=True,                # Enable logging for debugging
            engineio_logger=True
        )
        self.app.mount("/socket.io", socketio.ASGIApp(self.sio))

        # Enable CORS middleware for HTTP requests
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all domains (change to a specific domain for production)
            allow_credentials=True,
            allow_methods=["*"],  # Allow all HTTP methods
            allow_headers=["*"],  # Allow all headers
        )


        # Setup Logging
        self.setup_logging()

        # Serve static files (HTML, CSS, JS)
        self.app.mount("/static", StaticFiles(directory="static"), name="static")

        # Ensure static folder exists
        if not os.path.exists("static"):
            os.makedirs("static")

        # Register http routes and websocket events
        self.register_http_routes()
        self.register_socket_events()

    def setup_logging(self):
        """Set up logging configuration."""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        logging.basicConfig(
            filename=os.path.join(log_dir, "app.log"),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def register_http_routes(self):
        """Register HTTP Routes."""

        @self.app.get("/")
        async def serve_home():
            """Serve the HTML file for the web UI."""
            return FileResponse("static/index.html")  # Serve the HTML file

        @self.app.get("/status")
        async def get_status():
            """Expose monitoring status via HTTP."""
            return {
                "status": self.monitoring_status,
                "time_to_check": self.time_to_check,
                "active": self.monitoring_active,
            }

    def register_socket_events(self):
        """Register event handlers for Socket.IO."""

        @self.sio.event
        async def connect(sid, environ):
            """Handle new client connections."""
            self.logger.info(f"Client {sid} connected")
            await self.sio.emit("status_update", {"message": "Connected to server"}, to=sid)

        @self.sio.event
        async def start_monitoring(sid):
            """Start the monitoring loop."""
            await self.start_monitoring()

        @self.sio.event
        async def stop_monitoring(sid):
            """Stop the monitoring loop."""
            await self.stop_monitoring()

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnections."""
            self.logger.info(f"Client {sid} disconnected")

    async def monitoring_loop(self):
        """Background loop that monitors for new files."""
        while self.monitoring_active:
            for i in range(10, 0, -1):
                self.time_to_check = i
                self.monitoring_status = "Idle"

                # Emit update to frontend
                await self.sio.emit("status_update", {"status": self.monitoring_status, "time_to_check": self.time_to_check})

                await asyncio.sleep(1)  # ✅ Corrected (async sleep)

            self.monitoring_status = "Checking for new files..."
            await self.sio.emit("status_update", {"status": self.monitoring_status, "time_to_check": 0})

            await asyncio.sleep(3)  # ✅ Corrected (async sleep)

        await self.sio.emit("status_update", {"message": "Monitoring Stopped."})

    async def start_monitoring(self):
        """Start the monitoring loop."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.logger.info("Monitoring started.")
            asyncio.create_task(self.monitoring_loop())
            await self.sio.emit("status_update", {"message": "Monitoring Started."})

    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring_active = False
        self.logger.info("Monitoring stopped.")
        await self.sio.emit("status_update", {"message": "Stopping Monitoring..."})

    def run(self):
        """Run the FastAPI application with Uvicorn."""
        uvicorn.run(self.app, host="0.0.0.0", port=5001, reload=True)


monitoring_app = MonitoringApp()
app = monitoring_app.app  # Expose FastAPI instance globally

# Run the app if executed as a script
if __name__ == "__main__":
    uvicorn.run("web_ui:app", host="0.0.0.0", port=5001, reload=True)