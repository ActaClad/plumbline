"""The same tool, but the external call is guarded and returns a structured
error the agent can reason about — so a transient failure degrades gracefully
instead of aborting the run."""

from langchain_core.tools import tool
import requests


@tool
def fetch_order(order_id: int) -> dict:
    """Fetch an order; returns a structured error on failure."""
    try:
        resp = requests.get(
            f"https://api.example.com/orders/{order_id}", timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}
