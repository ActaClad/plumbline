"""RES-010: a leaked streaming helper (TP) + the valid with-managed boundary."""

import anthropic

ant = anthropic.Anthropic()
MSGS = [{"role": "user", "content": "hi"}]


def leaked():
    stream = ant.messages.stream(  # plumb-expect: PLB-RES-010
        model="claude-sonnet-4-5", max_tokens=512, messages=MSGS
    )
    return "".join(str(e) for e in stream)


# boundary: correct context-manager use — must NOT fire
def managed():
    with ant.messages.stream(model="claude-sonnet-4-5", max_tokens=512, messages=MSGS) as s:
        return "".join(s.text_stream)
