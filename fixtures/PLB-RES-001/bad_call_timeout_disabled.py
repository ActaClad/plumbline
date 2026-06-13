"""Bad: the call explicitly disables the timeout, so it can hang forever."""
from openai import OpenAI

client = OpenAI()


def summarize(text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": text}],
        timeout=None,  # PLB-RES-001: unbounded — can hang indefinitely
    )
    return response.choices[0].message.content
