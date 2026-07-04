"""A max_turns cap bounds the team — must stay silent."""
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat

writer = AssistantAgent("writer")
critic = AssistantAgent("critic")

team = SelectorGroupChat([writer, critic], max_turns=15)
