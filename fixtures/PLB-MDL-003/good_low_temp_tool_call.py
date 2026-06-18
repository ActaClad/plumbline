"""The same action-selection call, but at temperature 0 — deterministic tool
choice. This is the correct setting for an agentic/action path, so the rule
must stay silent."""

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
        temperature=0.0,
        tools=TOOLS,
        messages=[{"role": "user", "content": prompt}],
    )
