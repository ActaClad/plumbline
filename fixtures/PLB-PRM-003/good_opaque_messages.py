"""The messages are built elsewhere and passed as a variable, so the roles are
not statically visible — a system message may well be in there. The rule must
NOT guess: it stays silent rather than risk a false positive."""

from openai import OpenAI

client = OpenAI()


def answer(history: list) -> object:
    return client.chat.completions.create(
        model="gpt-4o",
        messages=history,
    )
