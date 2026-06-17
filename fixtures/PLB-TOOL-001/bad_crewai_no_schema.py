"""Bad: a crewAI BaseTool with no args_schema and an untyped _run — no declared
input contract, so the model can pass malformed arguments. Must still fire."""
from crewai.tools import BaseTool


class UntypedTool(BaseTool):
    name: str = "untyped"
    description: str = "does a thing"

    def _run(self, query):
        return query
