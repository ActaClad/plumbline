"""Clean across ALL agent/tool rules — FP stress. No marker, so any finding here
is a false positive. Bounded framework agents, a range-capped loop, a
counter-bound loop, and a typed tool: none should fire AGT-001/002 or TOOL-001."""
from langchain.agents import AgentExecutor
from langchain_core.tools import tool
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"
MSGS = [{"role": "user", "content": "hi"}]

# Bare executor -> bounded by the framework default; explicit cap -> bounded.
bounded = AgentExecutor(agent=a, tools=t)
explicit = AgentExecutor(agent=a, tools=t, max_iterations=10)


def range_capped(goal):
    for _ in range(10):
        r = client.chat.completions.create(model=MODEL, messages=MSGS, timeout=10, max_tokens=256)
        if r.choices[0].message.content.startswith("FINAL"):
            return r
    raise RuntimeError("did not converge")


def counter_bound(goal):
    n = 0
    while n < 10:
        client.chat.completions.create(model=MODEL, messages=MSGS, timeout=10, max_tokens=256)
        n += 1


@tool
def typed_lookup(order_id: int) -> dict:
    """Look up an order by id."""
    return store.get(order_id)
