"""A wildcard OAuth scope — one token grants everything."""
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

settings = AuthSettings(
    issuer_url="https://auth.example.com",
    required_scopes=["*"],  # over-broad
)

mcp = FastMCP("weather", auth=settings)
