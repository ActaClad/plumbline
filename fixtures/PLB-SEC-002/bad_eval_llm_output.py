"""Bad: model output is executed as code — remote code execution."""
from openai import OpenAI

client = OpenAI()


def run(task: str):
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": task}],
        timeout=10,
        max_tokens=256,
    )
    code = resp.choices[0].message.content
    return eval(code)
