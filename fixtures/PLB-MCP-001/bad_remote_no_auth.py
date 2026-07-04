"""FastMCP served over streamable-http with no auth — every tool exposed."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")


@mcp.tool()
def get_secrets(path: str) -> str:
    with open(path) as fh:
        return fh.read()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # no auth, network-exposed
