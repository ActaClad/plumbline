"""Bad: a hand-rolled agent loop with no max-iteration cap — same detector."""
from openai import OpenAI

client = OpenAI()


def run_agent(goal: str) -> str:
    messages = [{"role": "user", "content": goal}]
    while True:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=256
        )
        reply = resp.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
