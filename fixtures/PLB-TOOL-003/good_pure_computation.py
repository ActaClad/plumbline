"""A tool that does no external I/O — pure, in-process computation. There is no
external dependency that can fail, so there is nothing to guard and the rule
must stay silent (firing here would be noise)."""

from langchain_core.tools import tool


@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
