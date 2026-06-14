"""AGT-001 TPs across three frameworks; the while-True loop is also an AGT-002 TP.
Every model call sets timeout + max_tokens and uses the centralized MODEL, so no
reliability/cost rule fires."""
from crewai import Agent
from langchain.agents import AgentExecutor
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"
MSGS = [{"role": "user", "content": "hi"}]

lc = AgentExecutor(agent=a, tools=t, max_iterations=None)  # plumb-expect: PLB-AGT-001

cw = Agent(role="r", goal="g", backstory="b", max_iter=None)  # plumb-expect: PLB-AGT-001


def handrolled(goal):
    msgs = list(MSGS)
    while True:  # plumb-expect: PLB-AGT-001, PLB-AGT-002
        r = client.chat.completions.create(model=MODEL, messages=msgs, timeout=10, max_tokens=256)
        msgs.append({"role": "assistant", "content": r.choices[0].message.content})
