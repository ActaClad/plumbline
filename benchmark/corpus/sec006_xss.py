"""SEC-006 TP: model output rendered through an unescaped HTML sink."""
from flask import render_template_string

from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def page(q):
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    return render_template_string(resp.choices[0].message.content)  # plumb-expect: PLB-SEC-006
