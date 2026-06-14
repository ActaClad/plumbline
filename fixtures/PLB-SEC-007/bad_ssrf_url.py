"""Bad: a model-controlled URL on an outbound request — SSRF."""
import requests

from openai import OpenAI

client = OpenAI()


def fetch(q: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    url = resp.choices[0].message.content
    return requests.get(url, timeout=10)
