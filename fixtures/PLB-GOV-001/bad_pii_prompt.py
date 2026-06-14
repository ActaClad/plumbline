"""Bad: PII (an email) is sent to the model provider with no redaction."""
from openai import OpenAI

client = OpenAI()


def summarize_user(email: str):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": email}],
        timeout=10,
        max_tokens=256,
    )
