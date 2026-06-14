"""Good: a typed @tool — the framework validates arguments before the tool runs."""
from langchain_core.tools import tool


@tool
def lookup_order(order_id: int) -> dict:
    """Look up an order by id."""
    return db.get(order_id)
