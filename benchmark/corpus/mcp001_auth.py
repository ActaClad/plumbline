"""MCP-001: a remote FastMCP server with no authentication (TP).

The FP boundaries (stdio, loopback-bound, auth-configured) are covered by the
rule's good fixtures; they cannot live in this file because MCP-001 reasons about
the whole module's transport.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")  # plumb-expect: PLB-MCP-001


@mcp.tool()
def read_file(path: str) -> str:
    with open(path) as fh:
        return fh.read()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
