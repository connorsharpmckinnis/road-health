from main import App
import asyncio

if __name__ == "__main__":
    app = App(web_app=None)
    asyncio.run(app.start_monitoring(interval=10))