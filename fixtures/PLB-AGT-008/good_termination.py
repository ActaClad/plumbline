"""A termination condition bounds the team — must stay silent."""
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat

writer = AssistantAgent("writer")
critic = AssistantAgent("critic")

team = RoundRobinGroupChat(
    [writer, critic],
    termination_condition=MaxMessageTermination(20),
)
