"""Good: a parameterized query — the query string is constant (untainted) and the
untrusted value is a bound parameter. The precision crux: this must NOT fire even
though `name` is user input."""
from flask import Flask

app = Flask(__name__)


@app.post("/lookup")
def lookup(name, conn):
    return conn.execute("SELECT * FROM users WHERE name = ?", (name,))
