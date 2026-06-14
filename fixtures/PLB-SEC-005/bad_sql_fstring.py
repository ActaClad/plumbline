"""Bad: a SQL query built by f-string interpolation of model output."""
from openai import OpenAI

client = OpenAI()


def lookup(task: str, conn):
    resp = client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": task}], timeout=10, max_tokens=256
    )
    name = resp.choices[0].message.content
    return conn.execute(f"SELECT * FROM users WHERE name = '{name}'")
