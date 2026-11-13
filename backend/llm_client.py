"""HTTP client for the local OpenAI-compatible LM Studio endpoint."""

from typing import Dict, List

import requests

from config import (
    LM_STUDIO_CHAT_URL,
    LM_STUDIO_MODEL,
    LM_STUDIO_TIMEOUT_SECONDS,
    MAX_HISTORY_MESSAGES,
    MAX_TOKENS,
    SYSTEM_PROMPT,
    TEMPERATURE,
)


class LLMUnavailableError(RuntimeError):
    """Raised when LM Studio is unreachable or returns an invalid response."""


def generate_reply(
    message: str, history: List[Dict[str, str]], chunks: List[Dict[str, object]]
) -> str:
    context = "\n".join(
        f"- [{chunk['category']} | {chunk['question']}] {chunk['answer']}"
        for chunk in chunks
    )
    messages = [{
        "role": "system",
        "content": f"{SYSTEM_PROMPT}\n\nCollege information:\n{context}",
    }]
    messages.extend(history[-MAX_HISTORY_MESSAGES:])
    messages.append({"role": "user", "content": message})

    try:
        response = requests.post(
            LM_STUDIO_CHAT_URL,
            json={
                "model": LM_STUDIO_MODEL,
                "messages": messages,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_TOKENS,
                "stream": False,
            },
            timeout=LM_STUDIO_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        reply = payload["choices"][0]["message"]["content"]
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("LM Studio returned an empty reply.")
        return reply.strip()
    except (
        requests.RequestException, ValueError, KeyError, IndexError, TypeError
    ) as exc:
        raise LLMUnavailableError(
            "The local language model is unavailable or returned an invalid response."
        ) from exc
