"""Bad: no output cap — the generation can run to the full context window."""
from openai import OpenAI

client = OpenAI()


def write_essay(topic: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": topic}],
        timeout=30,
    )
    return resp.choices[0].message.content
