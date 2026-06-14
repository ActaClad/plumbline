"""Bad: a CrewAI @tool with no typed signature."""
from crewai.tools import tool


@tool("Order Lookup")
def lookup_order(order):
    return db.get(order)
