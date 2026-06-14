"""Good: catches a specific exception and re-raises."""
from openai import APIError, OpenAI

client = OpenAI()


def answer(q: str) -> str:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": q}]
        )
        return resp.choices[0].message.content
    except APIError:
        raise
