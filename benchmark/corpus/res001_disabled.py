"""RES-001 TPs: timeout explicitly disabled. All other params are clean."""
from openai import OpenAI

MODEL = "gpt-4o"
client = OpenAI()
MSGS = [{"role": "user", "content": "hi"}]


def call_disabled():
    return client.chat.completions.create(model=MODEL, messages=MSGS, timeout=None, max_tokens=256)  # plumb-expect: PLB-RES-001


unbounded = OpenAI(timeout=None)


def client_disabled():
    return unbounded.chat.completions.create(model=MODEL, messages=MSGS, max_tokens=256)  # plumb-expect: PLB-RES-001
