"""Good: PII is redacted before it reaches the prompt."""
from openai import OpenAI

client = OpenAI()


def redact(text: str) -> str:
    return "[redacted]"


def summarize_user(email: str):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": redact(email)}],
        timeout=10,
        max_tokens=256,
    )
