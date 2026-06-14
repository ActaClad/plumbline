"""Good: a for loop terminates by construction (the iterator exhausts)."""
from openai import OpenAI

client = OpenAI()


def run_agent(goal: str) -> None:
    for _ in range(5):
        client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": goal}], max_tokens=256
        )
