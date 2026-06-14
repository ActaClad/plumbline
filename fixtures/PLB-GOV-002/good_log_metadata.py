"""Good: only metadata and identifiers are logged, never raw content."""
import logging

from openai import OpenAI

client = OpenAI()
logger = logging.getLogger(__name__)


def run(q: str, run_id: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    logger.info("completion ok", extra={"run_id": run_id, "tokens": resp.usage.total_tokens})
    return resp
