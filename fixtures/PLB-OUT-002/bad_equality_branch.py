"""Branching on raw model output by string equality.

The code drives control flow by asserting the model said *exactly* "yes". Models
do not reliably emit an exact token — "Yes.", "yes!", "Sure, yes" all miss — and
the comparison is injectable. This is brittle control flow on unvalidated output.
"""

from openai import OpenAI

client = OpenAI()


def is_approved(prompt: str) -> bool:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    answer = resp.choices[0].message.content
    if answer == "yes":
        return True
    return False
