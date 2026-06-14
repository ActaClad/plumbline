"""Cross-module client detection (ADR-0016).

The dominant real-world structure is a centralized client module imported
elsewhere. These engine-level tests pin: the calls are now detected; the
explicit-disable case fires while the bare case stays silent (the precision
tripwire); and the `.messages.create` Twilio collision does NOT produce a false
positive.
"""

from __future__ import annotations

from pathlib import Path

from plumbline.config import Config
from plumbline.engine import scan
from plumbline.rules.base import discover_rules

RULES = discover_rules()

_CLIENT = "from openai import OpenAI\nclient = OpenAI(timeout=30)\n"


def _write(root: Path, files: dict[str, str]) -> None:
    for name, src in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)


def _rule_ids(result, file_suffix: str) -> set[str]:
    return {f.rule_id for f in result.findings if f.file.endswith(file_suffix)}


def test_cross_module_explicit_disable_fires(tmp_path: Path) -> None:
    # client imported (no `import openai` in caller); timeout EXPLICITLY None.
    _write(
        tmp_path,
        {
            "client.py": _CLIENT,
            "service.py": (
                "from client import client\n"
                "def f(q):\n"
                "    return client.chat.completions.create(\n"
                "        model='m', messages=[], timeout=None, max_tokens=10)\n"
            ),
        },
    )
    result = scan(tmp_path, Config(), RULES)
    assert "PLB-RES-001" in _rule_ids(result, "service.py")


def test_cross_module_bare_call_stays_silent(tmp_path: Path) -> None:
    # The precision tripwire: a bare cross-module call can't resolve the client's
    # timeout (it's in another file) -> UNKNOWN -> RES-001 must NOT fire.
    _write(
        tmp_path,
        {
            "client.py": _CLIENT,
            "service.py": (
                "from client import client\n"
                "def f(q):\n"
                "    return client.chat.completions.create(model='m', messages=[], max_tokens=10)\n"
            ),
        },
    )
    result = scan(tmp_path, Config(), RULES)
    assert "PLB-RES-001" not in _rule_ids(result, "service.py")


def test_twilio_messages_create_is_not_an_llm_call(tmp_path: Path) -> None:
    # `.messages.create` is also Twilio's SMS API. In a project that uses openai,
    # a Twilio call in a file with no SDK import must NOT be tagged (ADR-0016 D2).
    _write(
        tmp_path,
        {
            "client.py": _CLIENT,  # makes openai a project root
            "sms.py": (
                "from twilio.rest import Client\n"
                "tw = Client('sid', 'tok')\n"
                "def send(to, body):\n"
                "    return tw.messages.create(to=to, from_='+1', body=body)\n"
            ),
        },
    )
    result = scan(tmp_path, Config(), RULES)
    # No reliability/cost finding on the Twilio call — it isn't a model call.
    assert _rule_ids(result, "sms.py") == set()


def test_well_engineered_cross_module_app_has_no_false_positives(tmp_path: Path) -> None:
    # The H3 audit, locked: a realistic, correctly-built app — centralized client
    # with timeout+retries, max_tokens set, guarded JSON parse, a range-bounded
    # loop, parameterized SQL, tracing, and an eval test — produces ZERO findings,
    # even though detection now reaches its cross-module calls.
    _write(
        tmp_path,
        {
            "app/settings.py": "MODEL = 'gpt-4o'\nMAX_STEPS = 8\n",
            "app/client.py": (
                "from openai import OpenAI\nclient = OpenAI(timeout=30, max_retries=3)\n"
            ),
            "app/tracing.py": "from opentelemetry import trace\ntracer = trace.get_tracer('app')\n",
            "app/service.py": (
                "import json\n"
                "from .client import client\n"
                "from .settings import MODEL\n"
                "def summarize(text, **opts):\n"
                "    r = client.chat.completions.create(\n"
                "        model=MODEL, messages=[{'role': 'user', 'content': text}],\n"
                "        max_tokens=512, **opts)\n"
                "    try:\n"
                "        return json.loads(r.choices[0].message.content)\n"
                "    except json.JSONDecodeError:\n"
                "        return {}\n"
            ),
            "app/agent.py": (
                "from .client import client\n"
                "from .settings import MODEL, MAX_STEPS\n"
                "def run(goal):\n"
                "    history = [{'role': 'user', 'content': goal}]\n"
                "    for _ in range(MAX_STEPS):\n"
                "        r = client.chat.completions.create(\n"
                "            model=MODEL, messages=history[-10:], max_tokens=512)\n"
                "        reply = r.choices[0].message.content\n"
                "        if reply.startswith('FINAL:'):\n"
                "            return reply\n"
                "        history.append({'role': 'assistant', 'content': reply})\n"
                "    raise RuntimeError('no converge')\n"
            ),
            "app/db.py": (
                "def lookup(conn, name):\n"
                "    return conn.execute('SELECT * FROM t WHERE name = ?', (name,)).fetchall()\n"
            ),
            "tests/test_service.py": (
                "from app.service import summarize\ndef test_s():\n    assert summarize\n"
            ),
        },
    )
    result = scan(tmp_path, Config(), RULES)
    assert result.findings == (), [(f.rule_id, f.file, f.line) for f in result.findings]
    assert result.gate.passed


def test_framework_adapters_stay_per_file(tmp_path: Path) -> None:
    # A bare `@tool` decorator in a langchain project file must not be tagged from
    # another file's import — framework adapters are not project-triggered.
    _write(
        tmp_path,
        {
            "agent.py": "from langchain.agents import AgentExecutor\na = AgentExecutor()\n",
            "helpers.py": "@tool\ndef helper(x):\n    return x\n",  # no langchain import here
        },
    )
    result = scan(tmp_path, Config(), RULES)
    assert "PLB-TOOL-001" not in _rule_ids(result, "helpers.py")
