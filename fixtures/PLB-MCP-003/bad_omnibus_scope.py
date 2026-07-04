"""An omnibus `admin:*` scope alongside a fine-grained one — still over-broad."""
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

settings = AuthSettings(
    issuer_url="https://auth.example.com",
    required_scopes=["weather:read", "admin:*"],  # admin:* is over-broad
)

mcp = FastMCP("weather", auth=settings)
