"""Bad mini-repo: LLM/agent code with a CI pipeline that never runs evals."""
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
