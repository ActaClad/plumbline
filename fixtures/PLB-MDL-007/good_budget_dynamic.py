"""budget_tokens comes from a variable — not a provable literal, must stay silent.

Guards the precision boundary: the rule only fires on values it can prove wrong.
"""
import anthropic

client = anthropic.Anthropic()


def answer(q: str, budget: int, cap: int) -> str:
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=cap,
        thinking={"type": "enabled", "budget_tokens": budget},  # unprovable -> no finding
        messages=[{"role": "user", "content": q}],
    )
    return resp.content[0].text
