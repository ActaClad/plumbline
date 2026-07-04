"""Anthropic REQUIRES max_tokens — it must never be flagged here (precision boundary)."""
import anthropic

client = anthropic.Anthropic()


def answer(q: str) -> str:
    resp = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,  # required by the Anthropic API — correct
        messages=[{"role": "user", "content": q}],
    )
    return resp.content[0].text
