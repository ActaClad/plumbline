"""Good mini-repo: the same agent, with a CI pipeline that runs the test suite."""
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
