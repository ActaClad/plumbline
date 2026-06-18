"""A chat completion with only a user turn and no system prompt — the model's
role, constraints, and refusal behavior are left undefined."""

from openai import OpenAI

client = OpenAI()


def answer(prompt: str) -> object:
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
