"""A LangChain tool that makes an external HTTP call with no error handling.

If the orders service is down, slow, or returns a non-200, `requests.get` /
`.json()` raises straight out of the tool — which aborts the whole agent run
instead of letting the agent observe a structured error and recover.
"""

from langchain_core.tools import tool
import requests


@tool
def fetch_order(order_id: int) -> dict:
    """Fetch an order from the orders service."""
    resp = requests.get(f"https://api.example.com/orders/{order_id}")
    return resp.json()
