"""Good: `.execute()` is not always a DB cursor. Here it's a function/task
executor (cf. crewAI, babyagi) — a tainted arg with no SQL query string must NOT
fire SEC-005. Found as a real false positive when scanning babyagi."""
from flask import Flask

app = Flask(__name__)


@app.post("/run/<function_name>")
def run(function_name):  # handler param -> USER_INPUT-tainted
    return task_executor.execute(function_name, retries=3)
