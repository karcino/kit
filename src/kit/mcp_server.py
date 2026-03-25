"""Kit MCP Server — exposes all kit tools for Claude Code."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from kit.cal.mcp_tools import register_cal_tools
from kit.config import load_config
from kit.route.mcp_tools import register_route_tools

mcp = FastMCP("kit")


def _register_tools() -> None:
    """Load config and register all tool groups."""
    config = load_config()
    register_route_tools(mcp, config)
    register_cal_tools(mcp, config)


# Register tools at import time so they're available when the server starts.
_register_tools()


def run() -> None:
    """Entry-point for pyproject.toml: kit-mcp = 'kit.mcp_server:run'."""
    mcp.run(transport="stdio")
