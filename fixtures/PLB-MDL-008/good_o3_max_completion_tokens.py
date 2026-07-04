"""o3 called correctly with max_completion_tokens."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": q}],
        max_completion_tokens=2000,
    )
    return resp.choices[0].message.content
