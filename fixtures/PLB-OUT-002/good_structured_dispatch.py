"""Dispatching on a structured response-envelope field is correct handling, not
the defect. `item.type` is an API-guaranteed discriminator, not generated text —
branching on it is exactly how you process a typed response. Real-repo FP class
(found 9x on simonw/llm's response handler); the rule must stay silent here."""

from openai import OpenAI

client = OpenAI()


def handle(prompt: str) -> list:
    resp = client.responses.create(
        model="gpt-4o",
        input=[{"role": "user", "content": prompt}],
    )
    out = []
    for item in resp.output:
        if item.type == "function_call":
            out.append(("call", item))
        elif item.type == "message":
            out.append(("msg", item))
    return out
