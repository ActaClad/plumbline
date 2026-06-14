"""Bad: retries disabled at the client — transient errors become failures."""
from openai import OpenAI

client = OpenAI(max_retries=0)


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}]
    )
    return resp.choices[0].message.content
