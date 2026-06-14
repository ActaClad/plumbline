"""Good: an explicit output cap."""
from openai import OpenAI

client = OpenAI()


def write_summary(topic: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": topic}],
        timeout=30,
        max_tokens=512,
    )
    return resp.choices[0].message.content
