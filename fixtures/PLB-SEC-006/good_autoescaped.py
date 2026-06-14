"""Good: Jinja2 render_template autoescapes by default — passing model output as a
template variable is safe and must NOT fire."""
from flask import render_template

from openai import OpenAI

client = OpenAI()


def page(q: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    return render_template("page.html", body=resp.choices[0].message.content)
