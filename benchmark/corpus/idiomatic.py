"""Clean across ALL reliability rules — no rule should fire. FP stress.
Every call sets timeout + max_tokens, keeps default retries, references a
centralized model, and guards JSON parsing."""
import json

import settings
from openai import AsyncOpenAI, OpenAI

MODEL = "gpt-4o"
fast = OpenAI(timeout=10)
configured = OpenAI(timeout=settings.LLM_TIMEOUT)
async_client = AsyncOpenAI(timeout=20)
MSGS = [{"role": "user", "content": "hi"}]


def clean_call():
    return fast.chat.completions.create(model=MODEL, messages=MSGS, timeout=5, max_tokens=256).choices[0].message.content


def config_timeout():
    return configured.chat.completions.create(model=MODEL, messages=MSGS, max_tokens=256).choices[0].message.content


def passthrough(**opts):
    return fast.chat.completions.create(model=MODEL, messages=MSGS, timeout=5, **opts).choices[0].message.content


async def async_ok():
    resp = await async_client.chat.completions.create(model=MODEL, messages=MSGS, timeout=8, max_tokens=128)
    return resp.choices[0].message.content


def guarded_parse():
    resp = fast.chat.completions.create(model=MODEL, messages=MSGS, timeout=5, max_tokens=256)
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {}


def logged_handler():
    try:
        return fast.chat.completions.create(model=MODEL, messages=MSGS, timeout=5, max_tokens=256)
    except Exception as exc:
        print("failed", exc)
        return None
