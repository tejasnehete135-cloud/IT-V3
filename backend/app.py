"""Flask API for Campus Helpdesk."""

import csv
import logging
import re
import threading
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from config import (
    DATA_DIR,
    FRONTEND_DIR,
    LM_STUDIO_MODEL,
    LM_STUDIO_MODELS_URL,
    LM_STUDIO_TIMEOUT_SECONDS,
    LOG_FILE,
    MAX_HISTORY_MESSAGES,
    MAX_MESSAGE_LENGTH,
    PORT,
    RETRIEVAL_TOP_K,
)
from llm_client import LLMUnavailableError, generate_reply
from retriever import KnowledgeRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
CORS(app, resources={r"/api/*": {"origins": "*"}})
retriever = KnowledgeRetriever(DATA_DIR, top_k=RETRIEVAL_TOP_K)
log_lock = threading.Lock()

QUICK_QUESTIONS = [
    {"label": "Admissions", "question": "How do I apply for an undergraduate program?"},
    {"label": "Fees", "question": "What is the annual B.Tech tuition fee?"},
    {"label": "Exams", "question": "When are the semester exams?"},
    {"label": "Timetable", "question": "What is the weekly class schedule?"},
    {"label": "Events & Clubs", "question": "What clubs and campus events are available?"},
    {"label": "Contact Office", "question": "How can I contact the Campus Helpdesk?"},
]
CATEGORY_PATTERNS = [
    ("admissions", r"\b(admission|apply|application|eligib|course|seat|scholarship|merit|entrance|document)\w*\b"),
    ("fees", r"\b(fee|fees|tuition|hostel|bus|payment|refund|late charge|cost|installment)\w*\b"),
    ("exams", r"\b(exam|examination|hall ticket|attendance|revaluation|result|passing|assessment)\w*\b"),
    ("timetable", r"\b(timetable|time table|schedule|lecture|class|monday|tuesday|wednesday|thursday|friday|saturday|lab)\w*\b"),
    ("events", r"\b(event|fest|sports|club|placement|workshop|nss|activity|activities|library)\w*\b"),
]


def _validate_payload(payload: object) -> Tuple[str, List[Dict[str, str]]]:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message must be a non-empty string.")
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"Message must be at most {MAX_MESSAGE_LENGTH} characters.")
    history = payload.get("history", [])
    if not isinstance(history, list):
        raise ValueError("History must be a list.")
    valid_history: List[Dict[str, str]] = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        if (
            not isinstance(item, dict)
            or item.get("role") not in {"user", "assistant"}
            or not isinstance(item.get("content"), str)
        ):
            raise ValueError("Each history item needs a user/assistant role and text.")
        content = item["content"].strip()
        if not content or len(content) > MAX_MESSAGE_LENGTH:
            raise ValueError("History messages must contain valid text.")
        valid_history.append({"role": item["role"], "content": content})
    return message, valid_history


def _detect_category(message: str, chunks: List[Dict[str, object]]) -> str:
    lowered = message.lower()
    for category, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, lowered):
            return category
    if chunks:
        category = str(chunks[0]["category"])
        if category in {"admissions", "fees", "exams", "timetable", "events"}:
            return category
    return "general"


def _log_question(message: str, category: str) -> None:
    try:
        with log_lock:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            needs_header = not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0
            with LOG_FILE.open("a", encoding="utf-8", newline="") as log_file:
                writer = csv.writer(log_file)
                if needs_header:
                    writer.writerow(["timestamp", "question", "category"])
                writer.writerow([
                    datetime.now(timezone.utc).isoformat(),
                    message,
                    category,
                ])
    except OSError:
        logger.exception("Could not write the question log.")


def _contact_fallback() -> str:
    contact = retriever.helpdesk_contact()
    if contact:
        return str(contact["answer"])
    return (
        "I don't have that information. Please contact the Campus Helpdesk at "
        "helpdesk@campus.example or +1-555-0100."
    )


def _fallback_reply(message: str, category: str) -> Tuple[str, str]:
    record = retriever.fallback_answer(message)
    if record:
        return (
            "LM Studio is unavailable; here's the closest answer from Campus data:\n\n"
            + str(record["answer"]),
            str(record["category"]),
        )
    return _contact_fallback(), category


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def frontend_file(filename: str):
    if filename.startswith("api/") or re.search(r"(^|/)\.\.(/|$)", filename):
        return jsonify({"error": "Not found."}), 404
    return send_from_directory(FRONTEND_DIR, filename)


@app.post("/api/chat")
def chat():
    try:
        message, history = _validate_payload(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    chunks = retriever.search(message, top_k=RETRIEVAL_TOP_K)
    category = _detect_category(message, chunks)
    _log_question(message, category)
    if not chunks:
        reply, category = _fallback_reply(message, category)
        return jsonify({"reply": reply, "category": category, "source": "fallback"})

    try:
        reply = generate_reply(message, history, chunks)
        source = "llm"
    except LLMUnavailableError:
        logger.warning("LM Studio unavailable; returning a data-based fallback.")
        reply, category = _fallback_reply(message, category)
        source = "fallback"

    return jsonify({"reply": reply, "category": category, "source": source})


@app.get("/api/quick-questions")
def quick_questions():
    return jsonify(QUICK_QUESTIONS)


@app.get("/api/health")
def health():
    try:
        response = requests.get(
            LM_STUDIO_MODELS_URL, timeout=min(LM_STUDIO_TIMEOUT_SECONDS, 5)
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("LM Studio returned an invalid model list.")
        model_ids = {
            model["id"]
            for model in payload["data"]
            if isinstance(model, dict) and isinstance(model.get("id"), str)
        }
        lm_studio = (
            "reachable" if LM_STUDIO_MODEL in model_ids else "model_not_loaded"
        )
    except (requests.RequestException, ValueError, TypeError):
        lm_studio = "unavailable"
    return jsonify({
        "status": "ok",
        "lm_studio": lm_studio,
        "model": LM_STUDIO_MODEL,
        "records": len(retriever.records),
    })


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Request is too large."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=False)
