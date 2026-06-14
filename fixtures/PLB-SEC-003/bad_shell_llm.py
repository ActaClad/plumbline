"""Bad: model output is interpolated into a shell command."""
import os

from openai import OpenAI

client = OpenAI()


def run(task: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": task}], timeout=10, max_tokens=256
    )
    name = resp.choices[0].message.content
    os.system(f"convert {name} out.png")
