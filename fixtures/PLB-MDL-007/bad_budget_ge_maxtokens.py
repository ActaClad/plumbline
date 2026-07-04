"""budget_tokens (16000) >= max_tokens (8000) — Anthropic rejects with HTTP 400."""
import anthropic

client = anthropic.Anthropic()


def answer(q: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 16000},  # >= max_tokens -> 400
        messages=[{"role": "user", "content": q}],
    )
    return resp.content[0].text
