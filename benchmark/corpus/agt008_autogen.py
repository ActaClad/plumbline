"""AGT-008: an unbounded AutoGen team (TP) + a bounded boundary."""
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat

a = AssistantAgent("a")
b = AssistantAgent("b")

unbounded = RoundRobinGroupChat([a, b])  # plumb-expect: PLB-AGT-008

# boundary: a termination condition is set — must NOT fire
bounded = SelectorGroupChat([a, b], termination_condition=MaxMessageTermination(20))
