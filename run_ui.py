# run_with_ui.py
from main import App
from web_ui import WebApp
import asyncio

if __name__ == "__main__":
    web_app = WebApp()
    app = App(web_app=web_app)
    asyncio.run(app.start_monitoring(interval=10))