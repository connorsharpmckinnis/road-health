import os
import logging
import asyncio
import socketio
from fastapi import FastAPI
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from main import App



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

        # Initialize main app
        self.main = App()

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
                "status": self.main.status,
                "time_to_check": self.main.time_to_check,
                "active": self.main.monitoring_active,
            }

    def register_socket_events(self):
        """Register event handlers for Socket.IO."""

        @self.sio.event
        async def connect(sid, environ):
            """Handle new client connections."""
            self.logger.info(f"Client {sid} connected")
            await self.sio.emit("status_update", {"message": "Connected to server", "status": self.main.status}, to=sid)

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
        """Run the monitoring loop from main.py asynchronously."""
        logging.info("Starting monitoring loop asynchronously...")
        await asyncio.to_thread(self.main.start_monitoring, interval=10)

        while self.main.monitoring_active:
            # Emit current status updates
            await self.sio.emit("status_update", {
                "status": self.main.status,
                "time_to_check": self.main.time_to_check
            })
            await asyncio.sleep(1)  # Avoid spamming updates

    async def start_monitoring(self):
        """Start the monitoring loop."""
        self.logger.info("✅ start_monitoring() function called!")
        if not self.main.monitoring_active:
            self.logger.info("🔥 Calling start_monitoring() in main.py...")
            self.main.monitoring_status = "Active"
            self.main.status = "Active"
            self.logger.info("Monitoring started.")
            asyncio.create_task(self.monitoring_loop())
            await self.sio.emit("status_update", {"message": "Monitoring Started.", "status": self.main.monitoring_status})

    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.main.monitoring_active = False
        self.main.monitoring_status = "Idle"
        self.main.status = "Idle"
        self.logger.info("Monitoring stopped.")
        await self.sio.emit("status_update", {"message": "Stopping Monitoring...", "status": self.main.monitoring_status})

    def run(self):
        """Run the FastAPI application with Uvicorn."""
        uvicorn.run(self.app, host="0.0.0.0", port=5001, reload=True)


monitoring_app = MonitoringApp()
app = monitoring_app.app  # Expose FastAPI instance globally

# Run the app if executed as a script
if __name__ == "__main__":
    uvicorn.run("web_ui:app", host="0.0.0.0", port=5001, reload=True)