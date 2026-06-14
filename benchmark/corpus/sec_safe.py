"""Safe forms across the SEC rules — all must stay silent. No markers, so any
finding here is a false positive: parameterized SQL, argv-list subprocess,
constant URL, env-var secret + placeholder, and autoescaped HTML rendering."""
import os
import subprocess

import requests
from flask import Flask, render_template

from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o"
app = Flask(__name__)

API_KEY = os.environ["OPENAI_API_KEY"]  # env, not a literal -> SEC-004 silent
PLACEHOLDER_KEY = "your-api-key-here"  # placeholder -> SEC-004 silent


@app.post("/lookup")
def lookup(name, conn):
    return conn.execute("SELECT * FROM users WHERE name = ?", (name,))  # parameterized


def safe_shell(name):
    subprocess.run(["convert", name, "out.png"], check=True)  # argv list -> no shell


def safe_fetch():
    return requests.get("https://api.example.com/v1", timeout=10)  # constant URL


def safe_page(q):
    resp = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": q}], timeout=10, max_tokens=256
    )
    return render_template("page.html", body=resp.choices[0].message.content)  # autoescaped
