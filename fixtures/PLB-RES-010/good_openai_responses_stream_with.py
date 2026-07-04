"""OpenAI `.responses.stream()` used as a context manager — must stay silent."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    out = ""
    with client.responses.stream(model="gpt-4o", input=q) as stream:
        for event in stream:
            out += str(event)
    return out
