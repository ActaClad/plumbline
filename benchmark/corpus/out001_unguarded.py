"""OUT-001 TP: LLM output parsed with json.loads and no error handling.
The create call itself is clean (timeout + max_tokens)."""
import json

from openai import OpenAI

MODEL = "gpt-4o"
client = OpenAI()
MSGS = [{"role": "user", "content": "hi"}]


def parse_output():
    resp = client.chat.completions.create(model=MODEL, messages=MSGS, timeout=30, max_tokens=256)
    content = resp.choices[0].message.content
    return json.loads(content)  # plumb-expect: PLB-OUT-001
