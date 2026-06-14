"""Bad: retries disabled on the call."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}], max_retries=0
    )
    return resp.choices[0].message.content
