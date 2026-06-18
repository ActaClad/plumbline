"""A high temperature with NO tools is creative free-text generation, not action
selection — exactly where higher sampling is appropriate. The rule targets the
tool-calling path only, so this must stay silent."""

from openai import OpenAI

client = OpenAI()


def write_tagline(prompt: str) -> object:
    return client.chat.completions.create(
        model="gpt-4o",
        temperature=0.9,
        messages=[{"role": "user", "content": prompt}],
    )
