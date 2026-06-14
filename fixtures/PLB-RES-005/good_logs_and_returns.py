"""Good: the handler logs and returns an explicit error result."""
import logging

from openai import OpenAI

client = OpenAI()
logger = logging.getLogger(__name__)


def answer(q: str) -> str | None:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": q}]
        )
        return resp.choices[0].message.content
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        return None
