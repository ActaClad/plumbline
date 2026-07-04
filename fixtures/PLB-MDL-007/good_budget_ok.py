"""Correctly configured: budget_tokens (8000) >= 1024 and < max_tokens (16000)."""
import anthropic

client = anthropic.Anthropic()


def answer(q: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=16000,
        thinking={"type": "enabled", "budget_tokens": 8000},
        messages=[{"role": "user", "content": q}],
    )
    return resp.content[0].text
