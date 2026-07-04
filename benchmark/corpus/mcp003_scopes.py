"""MCP-003: an over-broad wildcard scope (TP) + a least-privilege boundary."""
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

bad = AuthSettings(
    issuer_url="https://auth.example.com",
    required_scopes=["admin:*"],  # plumb-expect: PLB-MCP-003
)

# boundary: minimal scopes — must NOT fire
ok = AuthSettings(
    issuer_url="https://auth.example.com",
    required_scopes=["weather:read", "weather:write"],
)

mcp = FastMCP("weather", auth=bad)
