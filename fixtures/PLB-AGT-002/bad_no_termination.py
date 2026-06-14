"""Bad: a model-driven while True with no reachable break/return."""
from openai import OpenAI

client = OpenAI()


def run_agent(goal: str) -> None:
    state = {"goal": goal}
    while True:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": str(state)}], max_tokens=256
        )
        state["last"] = resp.choices[0].message.content
