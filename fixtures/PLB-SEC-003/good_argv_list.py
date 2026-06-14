"""Good: the argv-list form has no shell to inject, even with tainted elements."""
import subprocess

from openai import OpenAI

client = OpenAI()


def run(task: str):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": task}], timeout=10, max_tokens=256
    )
    name = resp.choices[0].message.content
    subprocess.run(["convert", name, "out.png"], check=True)
