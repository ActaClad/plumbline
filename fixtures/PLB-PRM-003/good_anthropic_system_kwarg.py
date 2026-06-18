"""Anthropic carries the system prompt as a top-level `system=` argument, not as
a message in the list. The rule recognizes that and stays silent (provider-
agnostic, no branching)."""

from anthropic import Anthropic

client = Anthropic()


def answer(prompt: str) -> object:
    return client.messages.create(
        model="claude-sonnet-4-6",
        system="You are a support agent. Refuse off-topic requests.",
        messages=[{"role": "user", "content": prompt}],
    )
