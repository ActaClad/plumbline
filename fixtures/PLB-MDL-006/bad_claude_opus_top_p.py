"""claude-opus-4-8 removed sampling params — `top_p` here returns HTTP 400.

The model is pinned in a single-assignment constant to show it is still resolved
(like MDL-002), not only caught as an inline literal.
"""
import anthropic

client = anthropic.Anthropic()

MODEL = "claude-opus-4-8"


def answer(q: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": q}],
        top_p=0.9,  # removed on Opus 4.7+/Fable -> HTTP 400
    )
    return resp.content[0].text
