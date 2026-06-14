"""TOOL-001 TP: an untyped CrewAI @tool — same defect, different framework."""
from crewai.tools import tool


@tool("Order Lookup")
def cw_lookup(order):  # plumb-expect: PLB-TOOL-001
    return store.get(order)
