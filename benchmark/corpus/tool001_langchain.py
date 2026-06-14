"""TOOL-001 TP: an untyped LangChain @tool."""
from langchain_core.tools import tool


@tool
def lc_lookup(order):  # plumb-expect: PLB-TOOL-001
    return store.get(order)
