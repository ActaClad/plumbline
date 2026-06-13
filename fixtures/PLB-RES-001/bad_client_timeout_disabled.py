"""Bad: the client disables the timeout; every call through it is unbounded."""
from openai import OpenAI

client = OpenAI(timeout=None)  # PLB-RES-001 source


def answer(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content
