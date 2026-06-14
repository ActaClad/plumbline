"""Robustness battery (H2 hardening).

Real repos contain the full range of Python syntax and the occasional broken
file. The engine must never crash on any of it: valid-but-gnarly code analyzes
cleanly, malformed code is contained as an AnalyzerError (CLAUDE.md §4), and the
result is always deterministic.
"""

from __future__ import annotations

from pathlib import Path

from plumbline.config import Config
from plumbline.engine import scan
from plumbline.reporters.json import render_json
from plumbline.rules.base import discover_rules

RULES = discover_rules()

# Valid across 3.11–3.13. Each must parse and analyze with no analyzer error.
_GNARLY_VALID: dict[str, str] = {
    "match.py": (
        "def handle(cmd):\n"
        "    match cmd:\n"
        "        case {'op': 'add', 'x': int(x)}:\n"
        "            return x + 1\n"
        "        case [a, *rest]:\n"
        "            return a\n"
        "        case _:\n"
        "            return None\n"
    ),
    "walrus_async.py": (
        "import asyncio\n"
        "async def run(items):\n"
        "    while (n := await anext(items, None)) is not None:\n"
        "        yield n\n"
    ),
    "posonly_kwonly.py": "def f(a, b, /, c, *args, d, **kwargs):\n    return (a, b, c, d)\n",
    "comprehensions.py": (
        "data = {k: [v for v in range(k) if v % 2] for k in range(10)}\n"
        "gen = (x async for x in aiter())\n"
        "nested = [[y for y in row] for row in data]\n"
    ),
    "fstrings.py": "name='x'\nval = f\"{name!r:>{10}} {f'{name}'} {{literal}}\"\n",
    "decorators_class.py": (
        "import functools\n"
        "class Meta(type):\n    pass\n"
        "class C(metaclass=Meta):\n"
        "    @functools.cached_property\n"
        "    def x(self):\n        return 1\n"
    ),
    "unicode.py": "café = 'caf\\u00e9'\nΣ = sum([1, 2, 3])\nemoji = '🤖 agent'\n",
    "exception_groups.py": (
        "def f():\n"
        "    try:\n        pass\n"
        "    except* ValueError:\n        pass\n"
        "    except* (TypeError, KeyError):\n        pass\n"
    ),
    "global_nonlocal_lambda.py": (
        "g = 0\n"
        "def outer():\n"
        "    x = 1\n"
        "    def inner():\n        nonlocal x\n        global g\n        x += 1\n"
        "    return lambda: x\n"
    ),
    "empty.py": "",
    "only_docstring.py": '"""Just a module docstring."""\n',
    "only_comments.py": "# a\n# b\n# c\n",
    "future_import.py": "from __future__ import annotations\nx: list[int] = []\n",
}

# Must be contained as an AnalyzerError — never a crash.
_MALFORMED: dict[str, str] = {
    "syntax_error.py": "def f(:\n    pass\n",
    "unterminated.py": 'x = "open\n',
    "bad_indent.py": "def f():\nreturn 1\n",
}


def _write(root: Path, files: dict[str, str]) -> None:
    for name, src in files.items():
        (root / name).write_text(src, encoding="utf-8")


def test_gnarly_valid_code_analyzes_without_errors(tmp_path: Path) -> None:
    _write(tmp_path, _GNARLY_VALID)
    result = scan(tmp_path, Config(), RULES)  # must not raise
    assert result.analyzer_errors == (), [
        (e.file, e.stage, e.message) for e in result.analyzer_errors
    ]
    assert result.files_scanned == len(_GNARLY_VALID)


def test_malformed_files_are_contained_not_crashes(tmp_path: Path) -> None:
    _write(tmp_path, _MALFORMED)
    result = scan(tmp_path, Config(), RULES)  # must not raise
    errored = {e.file for e in result.analyzer_errors}
    for name in _MALFORMED:
        assert name in errored, f"{name} should be a contained analyzer error"


def test_deeply_nested_expression_is_contained(tmp_path: Path) -> None:
    # Left-nested BinOp drives the taint engine's recursive evaluator; if it
    # overflows it must be CONTAINED (engine boundary), never crash the process.
    (tmp_path / "deep.py").write_text("x = " + "1 + " * 600 + "1\n")
    scan(tmp_path, Config(), RULES)  # must not raise


def test_mixed_repo_is_deterministic(tmp_path: Path) -> None:
    _write(tmp_path, {**_GNARLY_VALID, **_MALFORMED})
    a = scan(tmp_path, Config(), RULES)
    b = scan(tmp_path, Config(), RULES)
    assert render_json(a) == render_json(b)
