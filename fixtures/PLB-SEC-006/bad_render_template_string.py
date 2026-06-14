"""Bad: model output rendered through an unescaped HTML sink — XSS."""
from flask import render_template_string

from openai import OpenAI

client = OpenAI()


def page(q: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    return render_template_string(resp.choices[0].message.content)
