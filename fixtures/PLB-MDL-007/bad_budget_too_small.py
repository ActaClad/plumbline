"""budget_tokens (512) is below the 1024 minimum — HTTP 400."""
import anthropic

client = anthropic.Anthropic()


def answer(q: str) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        thinking={"type": "enabled", "budget_tokens": 512},  # < 1024 -> 400
        messages=[{"role": "user", "content": q}],
    )
    return resp.content[0].text
