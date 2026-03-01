"""Tests for MCP tool registration."""

import pytest


@pytest.mark.asyncio
async def test_mcp_list_tools() -> None:
    """Test that all 12 expected MCP tools are registered."""
    from mcp_server.server import mcp

    # Get registered tools from the tool manager
    tools = mcp._tool_manager._tools

    expected_tools = [
        # Room management (4 tools)
        "list_rooms",
        "get_room",
        "create_room",
        "update_room",
        # Availability (1 tool)
        "check_availability",
        # Booking lifecycle (7 tools)
        "create_booking",
        "get_booking",
        "list_bookings",
        "confirm_booking",
        "cancel_booking",
        "check_in",
        "check_out",
    ]

    # Verify count
    assert len(tools) == 12, f"Expected 12 tools, got {len(tools)}: {list(tools.keys())}"

    # Verify each expected tool is registered
    for tool_name in expected_tools:
        assert tool_name in tools, f"Missing tool: {tool_name}"
