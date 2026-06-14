"""Good: model output is parsed and dispatched via an allow-list, never executed."""
import json

from openai import OpenAI

client = OpenAI()
ALLOWED = {"greet": lambda: "hi", "bye": lambda: "bye"}


def run(task: str):
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": task}],
        timeout=10,
        max_tokens=256,
    )
    try:
        action = json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return None
    return ALLOWED[action["name"]]()
