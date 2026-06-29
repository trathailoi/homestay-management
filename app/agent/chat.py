"""Shared Zalo Bot chat plumbing used by the polling worker.

Holds the per-chat conversation state, the staff allowlist, and the send/handle
helpers — the agent loop itself lives in loop.py. Kept transport-agnostic so the
poller (and a webhook, if ever re-added) can both drive it.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.agent import access
from app.agent.loop import run_agent
from app.config import settings

logger = logging.getLogger("uvicorn.error")

API_BASE = "https://bot-api.zaloplatforms.com"
TEXT_EVENT = "message.text.received"
_HISTORY_MAX = 24  # messages kept per chat

# ponytail: in-process history, single worker. Move to Redis/DB if you run >1
# uvicorn worker or need it to survive restarts.
_SESSIONS: dict[str, list[dict[str, Any]]] = {}


def parse_text_event(event: dict[str, Any]) -> dict[str, str] | None:
    """Return {chat_id, text, display_name, message_id} for a text event, else None."""
    if event.get("event_name") != TEXT_EVENT:
        return None
    msg = event.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "")
    if not chat_id or not text:
        return None
    return {
        "chat_id": chat_id,
        "text": text,
        "display_name": msg.get("from", {}).get("display_name", ""),
        "message_id": str(msg.get("message_id", "")),
    }


def _trim(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the recent tail, starting at a user turn so no orphan tool messages."""
    tail = history[-_HISTORY_MAX:]
    for i, m in enumerate(tail):
        if m.get("role") == "user":
            return tail[i:]
    return tail


async def send_message(chat_id: str, text: str, client: httpx.AsyncClient) -> None:
    url = f"{API_BASE}/bot{settings.zalo_bot_token}/sendMessage"
    await client.post(url, json={"chat_id": chat_id, "text": text[:2000]})


async def handle_message(chat_id: str, text: str, client: httpx.AsyncClient) -> None:
    """Run the agent for one incoming message and send its reply."""
    history = _SESSIONS.setdefault(chat_id, [])
    history.append({"role": "user", "content": text})
    try:
        reply, new_history = await run_agent(history)
        _SESSIONS[chat_id] = _trim(new_history)
    except Exception:
        logger.exception("agent failed for chat_id=%s", chat_id)
        reply = "Hệ thống đang bận, bạn thử lại sau giúp nhé."
    await send_message(chat_id, reply, client)


_HELP = (
    "Lệnh quản lý:\n"
    "/approve <id> — duyệt nhân viên\n"
    "/revoke <id> — thu hồi quyền\n"
    "/list — danh sách đã duyệt + đang chờ\n"
    "/help — trợ giúp"
)


async def route_message(
    chat_id: str, text: str, display_name: str, client: httpx.AsyncClient
) -> None:
    """Authorize, then dispatch to the agent or an admin command."""
    text = text.strip()
    if access.is_admin(chat_id) and text.startswith("/"):
        await _admin_command(chat_id, text, client)
        return
    if access.is_allowed(chat_id):
        logger.info("zalo message chat_id=%s", chat_id)
        await handle_message(chat_id, text, client)
        return
    await _request_access(chat_id, display_name, client)


async def _request_access(chat_id: str, display_name: str, client: httpx.AsyncClient) -> None:
    is_new = access.add_pending(chat_id, display_name)
    await send_message(
        chat_id,
        "Bạn chưa được cấp quyền dùng trợ lý đặt phòng. "
        "Mình đã gửi yêu cầu tới quản lý, vui lòng chờ duyệt nhé.",
        client,
    )
    if not is_new:
        return
    note = (
        "🔔 Yêu cầu truy cập mới:\n"
        f"Tên: {display_name or '(không tên)'}\n"
        f"ID: {chat_id}\n"
        f"Duyệt: /approve {chat_id}\n"
        f"Từ chối: /revoke {chat_id}"
    )
    admins = access.admins()
    if not admins:
        logger.warning("access request from %s but no HOMESTAY_AGENT_ADMINS set", chat_id)
    for admin_id in admins:
        await send_message(admin_id, note, client)


async def _admin_command(chat_id: str, text: str, client: httpx.AsyncClient) -> None:
    parts = text.split()
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/approve" and arg:
        name = access.pending().get(arg, "")  # remember the requester's name
        access.approve(arg, name)
        who = f"{name} ({arg})" if name else arg
        await send_message(chat_id, f"✅ Đã duyệt {who}.", client)
        await send_message(arg, "✅ Bạn đã được cấp quyền. Nhắn mình để bắt đầu nhé!", client)
    elif cmd == "/revoke" and arg:
        access.revoke(arg)
        await send_message(chat_id, f"Đã thu hồi quyền {arg}.", client)
    elif cmd == "/list":
        approved = access.approved_members()
        appr_txt = "\n".join(f"  {n or '(không tên)'} — {i}" for i, n in approved.items()) or "  (trống)"
        pend = access.pending()
        pend_txt = "\n".join(f"  {n or '(không tên)'} — {i}" for i, n in pend.items()) or "  (trống)"
        await send_message(chat_id, f"Đã duyệt:\n{appr_txt}\n\nĐang chờ:\n{pend_txt}", client)
    else:
        await send_message(chat_id, _HELP, client)
