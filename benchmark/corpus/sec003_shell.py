"""SEC-003 TP: model output in a shell command."""
import os

from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def run(task):
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": task}], timeout=10, max_tokens=256
    )
    name = resp.choices[0].message.content
    os.system(f"convert {name} out.png")  # plumb-expect: PLB-SEC-003
