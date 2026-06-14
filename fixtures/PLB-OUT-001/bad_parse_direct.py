"""Bad: parse the message content inline, still unguarded."""
import json

from openai import OpenAI

client = OpenAI()


def extract(text: str) -> dict:
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=30
    )
    return json.loads(resp.choices[0].message.content)
