"""Tests for Campus helpdesk data, retrieval, and API behavior."""

import csv
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

import app as helpdesk_app  # noqa: E402
import llm_client  # noqa: E402
from config import DATA_DIR, LM_STUDIO_MODEL, MAX_HISTORY_MESSAGES  # noqa: E402
from llm_client import LLMUnavailableError  # noqa: E402
from retriever import KnowledgeRetriever  # noqa: E402


@pytest.fixture()
def client():
    helpdesk_app.app.config.update(TESTING=True)
    return helpdesk_app.app.test_client()


def test_six_data_files_have_eight_valid_campus_records_each():
    expected = {
        "admissions.json", "fees.json", "exams.json",
        "timetable.json", "events.json", "contacts.json",
    }
    files = {path.name for path in DATA_DIR.glob("*.json")}
    assert files == expected

    all_records = []
    for path in DATA_DIR.glob("*.json"):
        records = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(records, list)
        assert len(records) >= 8
        assert all(
            isinstance(record.get(key), str) and record[key].strip()
            for record in records
            for key in ("id", "category", "question", "answer")
        )
        assert all(
            isinstance(record["keywords"], list) and record["keywords"]
            for record in records
        )
        all_records.extend(records)
    assert len({record["id"] for record in all_records}) == len(all_records)
    assert {record["category"] for record in all_records} == {
        "admissions", "fees", "exams", "timetable", "events", "general",
    }


def test_retriever_returns_relevant_chunks_and_ignores_unknown_queries():
    retriever = KnowledgeRetriever(DATA_DIR, top_k=4)
    fees = retriever.search("What is the annual B.Tech tuition fee?")
    assert 1 <= len(fees) <= 5
    assert fees[0]["id"] == "fees_002"
    assert not retriever.search("Tell me about quantum physics")
    assert "helpdesk@campus.example" in retriever.helpdesk_contact()["answer"]


def test_chat_returns_required_api_shape_and_logs_question(client, tmp_path):
    log_path = tmp_path / "queries.csv"
    with (
        patch.object(helpdesk_app, "LOG_FILE", log_path),
        patch.object(helpdesk_app, "generate_reply", return_value="B.Tech tuition is Rs 85,000 per year."),
    ):
        response = client.post(
            "/api/chat",
            json={"message": "What is the annual B.Tech tuition fee?", "history": []},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"reply", "category", "source"}
    assert payload["reply"] == "B.Tech tuition is Rs 85,000 per year."
    assert payload["category"] == "fees"
    assert payload["source"] == "llm"
    with log_path.open(encoding="utf-8", newline="") as log_file:
        rows = list(csv.DictReader(log_file))
    assert rows[0]["question"] == "What is the annual B.Tech tuition fee?"
    assert rows[0]["category"] == "fees"
    assert rows[0]["timestamp"]


def test_invalid_or_oversized_chat_messages_are_rejected(client):
    empty = client.post("/api/chat", json={"message": "  "})
    assert empty.status_code == 400
    assert "non-empty" in empty.get_json()["error"]

    too_long = client.post("/api/chat", json={"message": "x" * 2001})
    assert too_long.status_code == 400
    assert "2000" in too_long.get_json()["error"]


def test_offline_fallback_returns_best_record_and_notice(client):
    with patch.object(
        helpdesk_app, "generate_reply", side_effect=LLMUnavailableError("offline")
    ):
        response = client.post(
            "/api/chat", json={"message": "What is the annual B.Tech tuition fee?"}
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert "LM Studio is unavailable" in payload["reply"]
    assert "Rs 85,000" in payload["reply"]
    assert payload["category"] == "fees"
    assert payload["source"] == "fallback"


def test_unknown_query_uses_campus_contact_fallback(client):
    with patch.object(helpdesk_app, "generate_reply") as generate:
        response = client.post(
            "/api/chat", json={"message": "Tell me about quantum physics"}
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert "helpdesk@campus.example" in payload["reply"]
    assert payload["category"] == "general"
    assert payload["source"] == "fallback"
    generate.assert_not_called()


def test_history_is_limited_to_last_five_messages(client):
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"Message {index}"}
        for index in range(12)
    ]
    with patch.object(helpdesk_app, "generate_reply", return_value="Campus answer.") as generate:
        response = client.post(
            "/api/chat",
            json={"message": "When is the semester exam?", "history": history},
        )
    assert response.status_code == 200
    retained_history = generate.call_args.args[1]
    assert len(retained_history) == MAX_HISTORY_MESSAGES == 5
    assert retained_history[0]["content"] == "Message 7"


def test_llm_request_has_local_model_and_expected_settings():
    response = type(
        "Response",
        (),
        {
            "raise_for_status": lambda self: None,
            "json": lambda self: {
                "choices": [{"message": {"content": "Campus answer."}}]
            },
        },
    )()
    context = [{
        "category": "fees",
        "question": "B.Tech fee?",
        "answer": "B.Tech tuition is Rs 85,000 per year.",
    }]
    with patch.object(llm_client.requests, "post", return_value=response) as post:
        answer = llm_client.generate_reply("B.Tech fee?", [], context)

    payload = post.call_args.kwargs["json"]
    assert answer == "Campus answer."
    assert payload["model"] == LM_STUDIO_MODEL
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 400
    assert "B.Tech tuition is Rs 85,000" in payload["messages"][0]["content"]


def test_frontend_uses_campus_brand_and_expected_controls(client):
    response = client.get("/")
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Campus Helpdesk" in page
    assert "Nagpur" not in page
    assert "clear-chat" in page
    assert "theme-toggle" in page
    assert client.get("/script.js").status_code == 200
    assert client.get("/style.css").status_code == 200


def test_quick_questions_endpoint_supplies_six_requested_chips(client):
    response = client.get("/api/quick-questions")
    assert response.status_code == 200
    assert [item["label"] for item in response.get_json()] == [
        "Admissions", "Fees", "Exams", "Timetable", "Events & Clubs", "Contact Office",
    ]


def test_health_endpoint_reports_server_and_local_model(client):
    with patch.object(helpdesk_app.requests, "get") as get:
        get.return_value.raise_for_status.return_value = None
        get.return_value.json.return_value = {"data": [{"id": LM_STUDIO_MODEL}]}
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.get_json()["lm_studio"] == "reachable"
    assert response.get_json()["records"] >= 48
