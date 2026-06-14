"""Good (precision): params come via **kwargs, so max_tokens is UNKNOWN, not
absent — the rule stays silent rather than risk a false positive."""
from openai import OpenAI

client = OpenAI()


def generate(topic: str, **params: object) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": topic}],
        timeout=30,
        **params,
    )
    return resp.choices[0].message.content
