"""Bad: CrewAI agent with max_iter disabled — same defect, different framework."""
from crewai import Agent

researcher = Agent(
    role="researcher", goal="find facts", backstory="thorough", max_iter=None
)
