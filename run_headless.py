from main import App
import asyncio

if __name__ == "__main__":
    app = App()
    app.initialize()
    app.start_monitoring(interval=5, greenway_mode=False, mode="timelapse")