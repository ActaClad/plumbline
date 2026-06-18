"""A current, supported model. The rule matches by EXACT id, so a live model
that merely shares a family prefix with a dead one (`gpt-4...`) must stay silent."""

from openai import OpenAI

client = OpenAI()


def classify(text: str) -> object:
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": text}],
    )
