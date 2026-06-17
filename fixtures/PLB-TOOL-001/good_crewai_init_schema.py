"""Good: a crewAI BaseTool that declares its schema dynamically in __init__ /
super().__init__ (common in crewai_tools) — not as a class-body attribute."""
from crewai.tools import BaseTool


class DynamicTool(BaseTool):
    name: str = "dynamic"
    description: str = "does a thing"

    def __init__(self, schema):
        super().__init__(name=self.name, description=self.description, args_schema=schema)

    def _run(self, **kwargs):
        return None
