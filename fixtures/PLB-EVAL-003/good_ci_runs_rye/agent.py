"""Good mini-repo: CI runs the test suite via the Rye package manager."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": q}],
        timeout=10,
        max_tokens=256,
    )
    return resp.choices[0].message.content
