"""gpt-4o is NOT a reasoning model — `temperature` is valid here, must stay silent.

Guards the precision boundary: the rule keys on the model, not the mere presence
of a sampling param. A chat model with temperature is correct code.
"""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": q}],
        temperature=0.7,  # perfectly valid on a chat model
        max_tokens=512,
    )
    return resp.choices[0].message.content
