"""Good: a client-level timeout covers every call."""
from openai import OpenAI

client = OpenAI(timeout=30)


def answer(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content
