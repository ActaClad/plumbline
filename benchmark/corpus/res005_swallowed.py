"""RES-005 TPs: a broad except swallows the model call. Call itself is clean."""
from openai import OpenAI

MODEL = "gpt-4o"
client = OpenAI()
MSGS = [{"role": "user", "content": "hi"}]


def swallow_bare():
    try:
        return client.chat.completions.create(model=MODEL, messages=MSGS, timeout=30, max_tokens=256)
    except Exception:  # plumb-expect: PLB-RES-005
        pass
    return None
