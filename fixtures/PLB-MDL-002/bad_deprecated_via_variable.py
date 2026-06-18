"""The deprecated id is pinned in a module-level constant, not inline. Because
the rule consumes the adapter-RESOLVED model value (tri-state Known), it still
catches it through the single-assignment variable."""

from openai import OpenAI

client = OpenAI()

MODEL = "claude-2"


def run(text: str) -> object:
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": text}],
    )
