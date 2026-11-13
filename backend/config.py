"""Runtime settings for the Campus student helpdesk."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")


def _project_path(setting: str, default: Path) -> Path:
    value = Path(os.getenv(setting, str(default)))
    return value if value.is_absolute() else PROJECT_ROOT / value


DATA_DIR = _project_path("HELPDESK_DATA_DIR", PROJECT_ROOT / "data")
LOG_FILE = _project_path("HELPDESK_LOG_FILE", PROJECT_ROOT / "logs" / "queries.csv")
FRONTEND_DIR = PROJECT_ROOT / "frontend"

LM_STUDIO_BASE_URL = os.getenv(
    "LM_STUDIO_BASE_URL", "http://localhost:1234/v1"
).rstrip("/")
LM_STUDIO_CHAT_URL = f"{LM_STUDIO_BASE_URL}/chat/completions"
LM_STUDIO_MODELS_URL = f"{LM_STUDIO_BASE_URL}/models"
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-4b")
LM_STUDIO_TIMEOUT_SECONDS = float(os.getenv("LM_STUDIO_TIMEOUT_SECONDS", "45"))
TEMPERATURE = float(os.getenv("HELPDESK_TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("HELPDESK_MAX_TOKENS", "400"))
RETRIEVAL_TOP_K = min(5, max(3, int(os.getenv("HELPDESK_RETRIEVAL_TOP_K", "4"))))
PORT = int(os.getenv("HELPDESK_PORT", "5000"))
MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_MESSAGES = 5

SYSTEM_PROMPT = (
    "You are Campus Helpdesk. Answer only from the provided Campus data context. "
    "If the answer is not available, say: \"I don't have that information. Please "
    "contact the Campus Helpdesk at helpdesk@campus.example or +1-555-0100.\" "
    "Keep answers short and friendly, and use bullet points for lists. Never "
    "invent dates, fees, contact details, or other facts."
)
