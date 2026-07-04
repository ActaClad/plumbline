"""Remote transport bound to loopback — local only, must stay silent."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")


@mcp.tool()
def get_forecast(city: str) -> str:
    return f"forecast for {city}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1")  # loopback -> not exposed
