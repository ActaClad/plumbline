"""A system message establishes the model's role and constraints — the rule must
stay silent."""

from openai import OpenAI

client = OpenAI()


def answer(prompt: str) -> object:
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a support agent. Refuse off-topic requests."},
            {"role": "user", "content": prompt},
        ],
    )
