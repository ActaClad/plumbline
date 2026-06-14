"""Good: the parse is wrapped in a try that handles JSONDecodeError."""
import json

from openai import OpenAI

client = OpenAI()


def extract(text: str) -> dict | None:
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=30
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return None
