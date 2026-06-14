"""Bad: a bare except swallows the model call's failure."""
from openai import OpenAI

client = OpenAI()


def answer(q: str) -> str | None:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": q}]
        )
        return resp.choices[0].message.content
    except:  # noqa: E722  -- the very anti-pattern under test
        pass
    return None
