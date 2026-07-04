"""PRM-003: a chat call with no system prompt (TP) + the with-system boundary."""
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def no_system(q):
    return client.chat.completions.create(  # plumb-expect: PLB-PRM-003
        model=MODEL,
        messages=[{"role": "user", "content": q}],
        max_tokens=256,
    )


# boundary: a system message is present — must NOT fire
def with_system(q):
    return client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a support agent. Refuse off-topic requests."},
            {"role": "user", "content": q},
        ],
        max_tokens=256,
    )
