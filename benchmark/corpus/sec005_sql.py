"""SEC-005 TP: a SQL query built by f-string from model output."""
from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"


def run(task, conn):
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": task}], timeout=10, max_tokens=256
    )
    name = resp.choices[0].message.content
    conn.execute(f"SELECT * FROM users WHERE name = '{name}'")  # plumb-expect: PLB-SEC-005
