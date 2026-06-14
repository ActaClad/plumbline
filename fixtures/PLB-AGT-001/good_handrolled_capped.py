"""Good: a hand-rolled loop with a hard step bound — range() caps iterations."""
from openai import OpenAI

client = OpenAI()
MAX_STEPS = 10


def run_agent(goal: str) -> str:
    messages = [{"role": "user", "content": goal}]
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=256
        )
        reply = resp.choices[0].message.content
        if reply.startswith("FINAL:"):
            return reply
        messages.append({"role": "assistant", "content": reply})
    raise RuntimeError("agent did not converge")
