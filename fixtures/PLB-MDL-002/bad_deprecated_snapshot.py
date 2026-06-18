"""A pinned dated chat snapshot that has been sunset. The call works today and
will start returning errors on the provider's cutoff date — a scheduled outage."""

from openai import OpenAI

client = OpenAI()


def classify(text: str) -> object:
    return client.chat.completions.create(
        model="gpt-3.5-turbo-0301",
        messages=[{"role": "user", "content": text}],
    )
