"""Checking the output for emptiness is the RECOMMENDED guard (see OUT-003), not
a defect — the rule must stay silent on truthiness / empty-content checks, or it
would punish exactly the handling it wants to encourage."""

from openai import OpenAI

client = OpenAI()


def summarize(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    answer = resp.choices[0].message.content
    if not answer:
        return "(no summary available)"
    return answer
