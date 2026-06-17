"""Good: a crewAI BaseTool whose typed _run signature IS the input contract."""
from crewai.tools import BaseTool


class TypedTool(BaseTool):
    name: str = "typed"
    description: str = "looks things up"

    def _run(self, query: str, limit: int) -> dict:
        return {}
