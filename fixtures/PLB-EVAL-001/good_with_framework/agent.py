"""Good mini-repo (variant): evaluated via an LLM-eval framework, not a test."""
from openai import OpenAI

client = OpenAI()


def summarize(text: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}],
        timeout=10,
        max_tokens=256,
    )
    return resp.choices[0].message.content
