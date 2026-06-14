"""Good: a human-gated chat REPL. The `while True` is bounded by the user typing
'quit', not by the model — not a runaway agent loop, so AGT-001 must stay silent."""
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def chat() -> None:
    while True:
        msg = input("you: ")
        if msg == "quit":
            break
        client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": msg}], timeout=10, max_tokens=256
        )
