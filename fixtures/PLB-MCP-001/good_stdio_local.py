"""Default stdio transport (local, not network-exposed) — must stay silent."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server")


@mcp.tool()
def get_forecast(city: str) -> str:
    return f"forecast for {city}"


if __name__ == "__main__":
    mcp.run()  # stdio — local only
