"""RES-001 true positives: timeout explicitly disabled on real-looking calls."""
from openai import OpenAI
from anthropic import Anthropic

oai = OpenAI()
anthropic_client = Anthropic()

DISABLED = None


def summarize(text: str) -> str:
    # call-level disable
    resp = oai.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=None)  # plumb-expect: PLB-RES-001
    return resp.choices[0].message.content


def classify(text: str) -> str:
    # disable via a constant that resolves to None
    resp = oai.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}], timeout=DISABLED)  # plumb-expect: PLB-RES-001
    return resp.choices[0].message.content


def ask_claude(prompt: str) -> str:
    resp = anthropic_client.messages.create(model="claude-3-5-sonnet", max_tokens=512, messages=[{"role": "user", "content": prompt}], timeout=None)  # plumb-expect: PLB-RES-001
    return resp.content[0].text


unbounded = OpenAI(timeout=None)


def via_unbounded_client(text: str) -> str:
    # client-level disable -> the finding is on the call line
    return unbounded.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": text}])  # plumb-expect: PLB-RES-001
