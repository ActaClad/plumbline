"""AutoGen team with neither max_turns nor termination_condition — can loop forever."""
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat

writer = AssistantAgent("writer")
critic = AssistantAgent("critic")

team = RoundRobinGroupChat([writer, critic])  # no bound -> unbounded conversation
