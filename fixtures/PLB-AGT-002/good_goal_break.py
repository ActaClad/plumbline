"""Good: while True with a reachable goal-based exit — it terminates."""
from openai import OpenAI

client = OpenAI()


def run_agent(goal: str) -> str:
    messages = [{"role": "user", "content": goal}]
    while True:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=messages, max_tokens=256
        )
        reply = resp.choices[0].message.content
        if reply.startswith("FINAL:"):
            return reply
        messages.append({"role": "assistant", "content": reply})
