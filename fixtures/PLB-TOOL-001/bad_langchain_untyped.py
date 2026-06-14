"""Bad: a LangChain @tool with an untyped argument — the model can pass anything."""
from langchain_core.tools import tool


@tool
def lookup_order(order):
    """Look up an order by id."""
    return db.get(order)
