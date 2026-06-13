"""Good (precision): timeout comes from config and is not statically resolvable,
so the value is UNKNOWN and the High-confidence rule stays silent."""
from openai import OpenAI

import settings

client = OpenAI()


def answer(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": question}],
        timeout=settings.LLM_TIMEOUT,
    )
    return response.choices[0].message.content
