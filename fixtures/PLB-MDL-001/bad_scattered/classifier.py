"""Inlines the same model literal — module 2 of 2."""
from openai import OpenAI

client = OpenAI()


def classify(text: str) -> str:
    return client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=30, max_tokens=8
    ).choices[0].message.content
