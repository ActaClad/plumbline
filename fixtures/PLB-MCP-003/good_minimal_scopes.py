"""Least-privilege, fully-qualified scopes — must stay silent."""
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

settings = AuthSettings(
    issuer_url="https://auth.example.com",
    required_scopes=["weather:read", "weather:write"],  # minimal, specific
)

mcp = FastMCP("weather", auth=settings)
