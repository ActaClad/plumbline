"""RES-001 false-positive stress: idiomatic OpenAI/Anthropic usage that must NOT
fire. No markers here -> any finding the scanner produces is a false positive."""
import os

import settings
from anthropic import Anthropic
from openai import AsyncOpenAI, OpenAI

# explicit numeric timeouts, various shapes
fast = OpenAI(timeout=10)
slow = OpenAI(timeout=30.0)
default_client = OpenAI()  # relies on the SDK's finite default timeout
configured = OpenAI(timeout=settings.LLM_TIMEOUT)  # unknown-from-config
async_client = AsyncOpenAI(timeout=20)
claude = Anthropic(timeout=15)


def with_call_timeout(text):
    return fast.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=5).choices[0].message.content


def with_client_timeout(text):
    return slow.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}]).choices[0].message.content


def relies_on_sdk_default(text):
    return default_client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}]).choices[0].message.content


def timeout_from_config(text):
    return configured.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}]).choices[0].message.content


def timeout_passed_through_kwargs(text, **opts):
    # **opts may carry timeout -> UNKNOWN, must stay silent (precision)
    return fast.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}], **opts).choices[0].message.content


async def async_with_timeout(text):
    resp = await async_client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=8)
    return resp.choices[0].message.content


def claude_with_client_timeout(prompt):
    return claude.messages.create(model="claude-3-5-sonnet", max_tokens=256, messages=[{"role": "user", "content": prompt}]).content[0].text


def embeddings_are_not_chat(text):
    return default_client.embeddings.create(model="text-embedding-3-small", input=text).data[0].embedding


def not_an_llm_call_at_all(path):
    return os.path.join("/tmp", path)
