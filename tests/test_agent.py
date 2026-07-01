"""Agent loop + tool bridge checks. No real LLM or DB: the chat endpoint is a
MockTransport and dispatch is monkeypatched."""

import json

import httpx
import pytest

from app.agent import access, chat, loop, tools
from app.config import settings


async def test_build_tool_specs_has_all_tools():
    specs = await tools.build_tool_specs()
    names = {s["function"]["name"] for s in specs}
    assert len(specs) == 13
    assert {"create_booking", "get_booking_by_code"} <= names
    assert all(s["type"] == "function" and "parameters" in s["function"] for s in specs)


async def test_loop_dispatches_tool_then_returns_reply(monkeypatch):
    called = {}

    async def fake_dispatch(name, args):
        called["name"], called["args"] = name, args
        return {"available_rooms": [{"room_number": "101"}]}

    monkeypatch.setattr(loop, "dispatch", fake_dispatch)

    # First LLM turn asks for a tool; second turn (after tool result) answers.
    responses = iter(
        [
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "c1",
                                    "type": "function",
                                    "function": {
                                        "name": "check_availability",
                                        "arguments": json.dumps(
                                            {"check_in": "2026-07-01", "check_out": "2026-07-03"}
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
            {"choices": [{"message": {"role": "assistant", "content": "Phòng 101 còn trống."}}]},
        ]
    )

    def handler(request):
        return httpx.Response(200, json=next(responses))

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    reply, history = await run_with(client)

    assert called["name"] == "check_availability"
    assert called["args"]["check_in"] == "2026-07-01"
    assert reply == "Phòng 101 còn trống."
    # history carries the tool round-trip for the next turn
    assert any(m.get("role") == "tool" for m in history)
    await client.aclose()


async def run_with(client):
    return await loop.run_agent(
        [{"role": "user", "content": "Phòng trống 1-3/7 không?"}], client=client
    )


def test_parse_text_event_extracts_fields():
    event = {
        "event_name": "message.text.received",
        "message": {
            "from": {"id": "abc123", "display_name": "Ted"},
            "chat": {"id": "abc123", "chat_type": "PRIVATE"},
            "text": "Xin chào",
            "message_id": "m1",
        },
    }
    assert chat.parse_text_event(event) == {
        "chat_id": "abc123",
        "text": "Xin chào",
        "display_name": "Ted",
        "message_id": "m1",
    }
    # non-text events are ignored
    assert chat.parse_text_event({"event_name": "message.image.received"}) is None


def test_admin_approve_grants_access(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "media_root", str(tmp_path))  # store on temp dir
    monkeypatch.setattr(settings, "agent_admins", "owner1")
    monkeypatch.setattr(settings, "agent_allowed_senders", "")

    assert access.is_admin("owner1")
    assert access.is_allowed("owner1")  # admins always allowed
    assert not access.is_allowed("staff9")  # unknown -> blocked (fail closed)

    access.approve("staff9", "Lan")
    assert access.is_allowed("staff9")  # now persisted in the store
    assert access.approved_members()["staff9"] == "Lan"  # name shown in /list
    assert json.loads((tmp_path / ".zalo_allowed.json").read_text())["staff9"] == "Lan"

    access.revoke("staff9")
    assert not access.is_allowed("staff9")
