"""Package-dotted import of the agent module — the realistic shape."""
from myapp.agent import summarize


def test_summarize_returns_text():
    assert isinstance(summarize("the cat sat on the mat"), str)
