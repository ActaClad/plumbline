"""Good: a generic tool wrapper with no named params (`*args, **kwargs`) has no
typable input contract — nothing for TOOL-001 to ask the author to annotate. A
real-repo FP class (gpt-researcher's `custom_tool`, crewAI's ZapierActionTool)."""
from langchain_core.tools import tool


@tool
def custom_tool(*args, **kwargs) -> str:
    return str(args)
