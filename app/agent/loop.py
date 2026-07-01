"""OpenAI-compatible function-calling loop driving the homestay tools.

Works against any OpenAI-compatible chat-completions endpoint (OpenAI, ZAI GLM,
etc.) selected via HOMESTAY_OPENAI_BASE_URL / _API_KEY / AGENT_MODEL. Hand-rolled
over httpx (already a runtime dep) — no openai SDK pulled in for one POST loop.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import httpx

from app.agent.tools import build_tool_specs, dispatch, parse_arguments
from app.config import settings

MAX_STEPS = 8  # tool-call rounds before giving up
_REPLY_MAX = 1900  # Zalo text messages cap ~2000 chars


def _system_prompt() -> str:
    return (
        "You are the booking assistant for a Vietnamese homestay, talking to "
        "front-desk staff (admin/receptionist) over chat. Help them check room "
        "availability, look up and create/confirm/cancel bookings, and answer "
        f"inventory questions. Today is {date.today().isoformat()}. "
        "Prices are in Vietnamese dong (VND); format them with thousands "
        "separators. Reply in the same language the staff member uses "
        "(usually Vietnamese). Keep replies short and chat-friendly.\n\n"
        "Tools: use read tools (list/get/check_availability) freely. Before any "
        "WRITE action (create_booking, confirm_booking, cancel_booking, "
        "create_room, update_room, check_in, check_out), first summarise the "
        "exact change — room, dates, guest, total VND — and wait for the staff "
        "member to say yes. Never invent room IDs or booking IDs; look them up "
        "with the tools. When a tool returns an 'error' field, explain it plainly.\n\n"
        "After creating or confirming a booking, ALWAYS tell the guest their "
        "booking code (the 'booking_code' field) clearly, and say to give it at "
        "check-in. To check a guest in, look them up with get_booking_by_code first."
    )


def _endpoint() -> str:
    return settings.openai_base_url.rstrip("/") + "/chat/completions"


async def run_agent(
    history: list[dict[str, Any]],
    *,
    client: httpx.AsyncClient | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the tool loop over a conversation `history` (no system message).

    Returns (reply_text, updated_history). The updated history includes the
    assistant/tool turns so the next call has context; trim it before storing.
    `client` is injectable for tests.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
        *history,
    ]
    specs = await build_tool_specs()
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=60)
    try:
        for _ in range(MAX_STEPS):
            resp = await client.post(
                _endpoint(),
                headers=headers,
                json={
                    "model": settings.agent_model,
                    "messages": messages,
                    "tools": specs,
                    "tool_choice": "auto",
                },
            )
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            messages.append(msg)

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                reply = (msg.get("content") or "").strip()[:_REPLY_MAX]
                return reply, messages[1:]

            for call in tool_calls:
                fn = call["function"]
                try:
                    result = await dispatch(fn["name"], parse_arguments(fn.get("arguments")))
                except Exception as exc:  # surface tool failure to the model, keep loop alive
                    result = {"error": "TOOL_FAILED", "message": str(exc)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result, default=str),
                    }
                )
        # ponytail: hit step cap — rare; tell staff to retry rather than loop forever.
        return "Xin lỗi, tôi chưa xử lý xong yêu cầu này. Bạn thử lại nhé.", messages[1:]
    finally:
        if owns_client:
            await client.aclose()
