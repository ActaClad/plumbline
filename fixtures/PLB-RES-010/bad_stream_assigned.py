"""`.messages.stream()` assigned and iterated without `with` — connection leak."""
import anthropic

client = anthropic.Anthropic()


def answer(q: str) -> str:
    stream = client.messages.stream(  # not a context manager -> leaked connection
        model="claude-sonnet-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": q}],
    )
    out = ""
    for event in stream:
        out += str(event)
    return out
