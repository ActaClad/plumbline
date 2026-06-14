from openai import OpenAI

from .config import CHAT_MODEL

client = OpenAI()


def summarize(text: str) -> str:
    return client.chat.completions.create(
        model=CHAT_MODEL, messages=[{"role": "user", "content": text}], timeout=30, max_tokens=256
    ).choices[0].message.content
