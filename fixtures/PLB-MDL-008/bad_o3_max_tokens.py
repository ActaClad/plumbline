"""o3 rejects `max_tokens` on Chat Completions — must use max_completion_tokens."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": q}],
        max_tokens=2000,  # o-series requires max_completion_tokens -> HTTP 400
    )
    return resp.choices[0].message.content
