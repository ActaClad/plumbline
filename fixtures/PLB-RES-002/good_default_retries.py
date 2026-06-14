"""Good: rely on the SDK's automatic retries (default max_retries=2)."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}]
    )
    return resp.choices[0].message.content
