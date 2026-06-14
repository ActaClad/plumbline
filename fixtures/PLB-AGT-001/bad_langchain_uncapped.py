"""Bad: LangChain AgentExecutor with its iteration cap explicitly removed."""
from langchain.agents import AgentExecutor, create_tool_calling_agent

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, max_iterations=None)
