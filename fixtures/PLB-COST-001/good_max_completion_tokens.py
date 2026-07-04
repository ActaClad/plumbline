"""Reasoning models cap output with max_completion_tokens / max_output_tokens —
those are valid caps and must NOT be flagged as "no output bound"."""
from openai import OpenAI

client = OpenAI()


def chat_completions(q: str) -> str:
    resp = client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": q}],
        max_completion_tokens=512,  # the reasoning-model output cap — bounded
    )
    return resp.choices[0].message.content


def responses(q: str) -> str:
    resp = client.responses.create(
        model="o3",
        input=q,
        max_output_tokens=512,  # Responses-API output cap — bounded
    )
    return resp.output_text
