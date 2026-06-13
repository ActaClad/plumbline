"""Good: an explicit, finite timeout on the call."""
from openai import OpenAI

client = OpenAI()


def summarize(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}],
        timeout=30,
    )
    return response.choices[0].message.content
