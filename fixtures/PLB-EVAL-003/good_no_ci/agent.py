"""Good for EVAL-003: no CI pipeline at all, so there is nothing to gate — the
'no eval suite' concern belongs to EVAL-001, not this rule. EVAL-003 stays silent."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": q}],
        timeout=10,
        max_tokens=256,
    )
    return resp.choices[0].message.content
