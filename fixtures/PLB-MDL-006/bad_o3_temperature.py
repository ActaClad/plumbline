"""o3 (an OpenAI reasoning model) rejects `temperature` — 400 on every call."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": q}],
        temperature=0.7,  # reasoning models reject sampling params -> HTTP 400
    )
    return resp.choices[0].message.content
