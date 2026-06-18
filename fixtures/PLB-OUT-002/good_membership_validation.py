"""Constraining the output to a known set before acting on it is the FIX for
this defect, not the defect. Membership against an allow-list (`in {...}`) is
validation, so the rule must not fire on it — only on raw equality branching."""

from openai import OpenAI

client = OpenAI()

VALID_ACTIONS = {"approve", "reject", "escalate"}


def route(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    answer = (resp.choices[0].message.content or "").strip().lower()
    if answer in VALID_ACTIONS:
        return answer
    return "reject"
