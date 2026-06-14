"""Good: explicit positive retry count."""
from openai import OpenAI

client = OpenAI(max_retries=3)


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}]
    )
    return resp.choices[0].message.content
