"""`.messages.stream()` used correctly as a context manager — must stay silent."""
import anthropic

client = anthropic.Anthropic()


def answer(q: str) -> str:
    out = ""
    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": q}],
    ) as stream:
        for text in stream.text_stream:
            out += text
    return out
