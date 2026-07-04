"""Reasoning-model config: MDL-006/007/008 true positives + valid boundaries.

The valid-boundary functions at the bottom must produce NO reasoning-config
finding — they are the precision test for the family.
"""

import anthropic
from openai import OpenAI

oai = OpenAI()
ant = anthropic.Anthropic()
MSGS = [{"role": "user", "content": "hi"}]


def m6_openai_temperature():
    return oai.chat.completions.create(  # plumb-expect: PLB-MDL-006
        model="o3", messages=MSGS, max_completion_tokens=256, temperature=0.7
    )


def m6_anthropic_top_p():
    return ant.messages.create(  # plumb-expect: PLB-MDL-006
        model="claude-opus-4-8", max_tokens=1024, messages=MSGS, top_p=0.9
    )


def m8_openai_max_tokens():
    return oai.chat.completions.create(  # plumb-expect: PLB-MDL-008
        model="o3", messages=MSGS, max_tokens=2000
    )


def m7_bad_budget():
    return ant.messages.create(  # plumb-expect: PLB-MDL-007
        model="claude-sonnet-4-5",
        max_tokens=8000,
        thinking={"type": "enabled", "budget_tokens": 16000},
        messages=MSGS,
    )


# --- valid boundaries: must NOT fire any reasoning-config rule ---
def ok_chat_model_temperature():
    return oai.chat.completions.create(
        model="gpt-4o", messages=MSGS, max_tokens=256, temperature=0.5
    )


def ok_o3_correct():
    return oai.chat.completions.create(model="o3", messages=MSGS, max_completion_tokens=256)


def ok_claude_requires_max_tokens():
    return ant.messages.create(model="claude-opus-4-8", max_tokens=1024, messages=MSGS)
