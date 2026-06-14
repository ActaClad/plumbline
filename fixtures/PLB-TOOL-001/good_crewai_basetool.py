"""Good: a CrewAI BaseTool subclass declaring an explicit args_schema."""
from crewai.tools import BaseTool


class OrderLookupTool(BaseTool):
    name: str = "Order Lookup"
    description: str = "Look up an order by id."
    args_schema = OrderLookupArgs

    def _run(self, order_id):
        return db.get(order_id)
