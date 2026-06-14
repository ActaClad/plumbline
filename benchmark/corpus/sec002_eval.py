"""SEC-002 TP: eval of model output."""
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def run(task):
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": task}], timeout=10, max_tokens=256
    )
    return eval(resp.choices[0].message.content)  # plumb-expect: PLB-SEC-002
