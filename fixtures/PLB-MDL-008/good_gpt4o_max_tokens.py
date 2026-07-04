"""gpt-4o is not a reasoning model — max_tokens is valid, must stay silent."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": q}],
        max_tokens=2000,  # valid on a chat model
    )
    return resp.choices[0].message.content
