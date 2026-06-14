"""RES-002 TPs: retries disabled. Timeout and max_tokens are set."""
from openai import OpenAI

MODEL = "gpt-4o"
client = OpenAI()
MSGS = [{"role": "user", "content": "hi"}]


def call_no_retries():
    return client.chat.completions.create(model=MODEL, messages=MSGS, timeout=30, max_tokens=256, max_retries=0)  # plumb-expect: PLB-RES-002


no_retry_client = OpenAI(max_retries=0)


def client_no_retries():
    return no_retry_client.chat.completions.create(model=MODEL, messages=MSGS, timeout=30, max_tokens=256)  # plumb-expect: PLB-RES-002
