import logging
import os

LOG_FILE = "logs/app.log"

if not os.path.exists("logs"):
    os.makedirs("logs")

AI_LOG_LEVEL = 15
logging.addLevelName(AI_LOG_LEVEL, "ai")

def ai(self, message, *args, **kwargs):
    """Custom AI log method"""
    if self.isEnabledFor(AI_LOG_LEVEL):
        self._log(AI_LOG_LEVEL, message, args, **kwargs)

logging.Logger.ai = ai

# Define custom filter to exclude external HTTP/API logs
class APIFilter(logging.Filter):
    def filter(self, record):
        return "HTTP Request" not in record.getMessage()  # Exclude HTTP API calls


class RouteFilter(logging.Filter):
    """Filters out logs from frequent polling routes."""
    def filter(self, record):
        return not ("/status" in record.getMessage() or "/processing-details" in record.getMessage() or "/main-details" in record.getMessage() or "/folder-contents" in record.getMessage() or "/logs" in record.getMessage())

log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)
file_handler.addFilter(RouteFilter())
file_handler.addFilter(APIFilter())  # Apply filter to exclude HTTP logs

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)
console_handler.addFilter(RouteFilter())
console_handler.addFilter(APIFilter())  # Apply filter to exclude HTTP logs

# Root logger configuration
logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

logger = logging.getLogger(__name__)

# Suppress logging from OpenAI and urllib3
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)