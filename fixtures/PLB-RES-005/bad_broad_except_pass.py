"""Bad: `except Exception: pass` around the call."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str | None:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": q}]
        )
        return resp.choices[0].message.content
    except Exception:
        pass
    return None
