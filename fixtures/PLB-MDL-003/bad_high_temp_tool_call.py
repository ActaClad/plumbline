"""A tool-calling completion run at a high sampling temperature.

`tools=` means the model is selecting an action; `temperature=0.9` makes that
selection nondeterministic — the same input can pick different tools across
runs, which is untestable and a reliability hazard on an action path.
"""

from openai import OpenAI

client = OpenAI()

TOOLS = [
    {
        "type": "function",
        "function": {"name": "get_weather", "parameters": {}},
    }
]


def choose_action(prompt: str) -> object:
    return client.chat.completions.create(
        model="gpt-4o",
        temperature=0.9,
        tools=TOOLS,
        messages=[{"role": "user", "content": prompt}],
    )
