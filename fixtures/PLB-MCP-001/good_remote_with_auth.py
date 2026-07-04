"""Remote transport WITH authentication configured — must stay silent."""
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-server", auth=AuthSettings(issuer_url="https://auth.example.com"))


@mcp.tool()
def get_forecast(city: str) -> str:
    return f"forecast for {city}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
