"""Bad: the full model response is written to the logs."""
import logging

from openai import OpenAI

client = OpenAI()
logger = logging.getLogger(__name__)


def run(q: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    logger.info(resp.choices[0].message.content)
