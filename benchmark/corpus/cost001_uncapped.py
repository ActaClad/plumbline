"""COST-001 TPs: no max_tokens. Timeout is set; retries default."""
from openai import OpenAI

MODEL = "gpt-4o"
client = OpenAI()
MSGS = [{"role": "user", "content": "hi"}]


def uncapped():
    return client.chat.completions.create(model=MODEL, messages=MSGS, timeout=30)  # plumb-expect: PLB-COST-001


def uncapped_again():
    return client.chat.completions.create(model=MODEL, messages=MSGS, timeout=10)  # plumb-expect: PLB-COST-001
