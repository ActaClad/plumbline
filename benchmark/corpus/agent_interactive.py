"""FP stress: human-gated chat REPLs. The `while True` is bounded by the user,
not the model, so NO agent rule should fire (ADR-0012 D2 interactive narrowing).
No markers -> any finding here is a false positive."""
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def repl_with_break() -> None:
    while True:
        msg = input("you: ")
        if msg == "quit":
            break
        client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": msg}], timeout=10, max_tokens=256
        )


def repl_loop_on_prompt() -> None:
    line = input("> ")
    while line:
        client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": line}], timeout=10, max_tokens=256
        )
        line = input("> ")
