"""Good: a bare call relies on the SDK's finite default timeout — not unbounded,
so PLB-RES-001 does not fire (detailed-design §9.4)."""
from openai import OpenAI

client = OpenAI()


def answer(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
    )
    return response.choices[0].message.content
