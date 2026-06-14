"""Good: bare AgentExecutor — bounded by the framework default (max_iterations=15)."""
from langchain.agents import AgentExecutor, create_tool_calling_agent

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
