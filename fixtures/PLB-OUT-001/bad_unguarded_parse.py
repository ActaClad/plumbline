"""Bad: model output goes straight into json.loads with no guard."""
import json

from openai import OpenAI

client = OpenAI()


def extract(text: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}],
        timeout=30,
    )
    content = resp.choices[0].message.content
    return json.loads(content)  # crashes on the first malformed generation
