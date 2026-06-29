"""Bridge the FastMCP tools to an OpenAI-compatible function-calling loop.

The 12 homestay tools are already defined and schema'd on the FastMCP object in
mcp_server.server. We reuse those definitions verbatim instead of re-declaring
them: `build_tool_specs` reads the registered schemas, `dispatch` runs a tool by
name. No per-tool boilerplate, and the REST/MCP/agent surfaces stay in sync.
"""

from __future__ import annotations

import json
from typing import Any

from mcp_server.server import mcp

# Write tools mutate state. The system prompt tells the agent to confirm with
# staff before calling these; the sender whitelist is the actual auth boundary.
WRITE_TOOLS = frozenset(
    {
        "create_booking",
        "confirm_booking",
        "cancel_booking",
        "create_room",
        "update_room",
        "check_in",
        "check_out",
    }
)


async def build_tool_specs() -> list[dict[str, Any]]:
    """OpenAI `tools=[...]` schema, generated from the registered MCP tools."""
    tools = await mcp.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.parameters,
            },
        }
        for t in tools
    ]


async def dispatch(name: str, arguments: dict[str, Any]) -> Any:
    """Run a tool by name with parsed arguments; returns its plain dict result."""
    tool = await mcp.get_tool(name)
    if tool is None:
        return {"error": "UNKNOWN_TOOL", "message": f"No tool named {name!r}"}
    return await tool.fn(**arguments)


def parse_arguments(raw: str | None) -> dict[str, Any]:
    """Parse the JSON arguments string from a tool_call (tolerates empty/None)."""
    if not raw:
        return {}
    return json.loads(raw)
