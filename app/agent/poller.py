"""Long-poll worker: pulls messages from Zalo (getUpdates) and drives the agent.

Outbound-only — no public endpoint, no tunnel. Started as a background task on
app boot (see app/main.py lifespan). getUpdates long-polls up to `timeout`
seconds and returns pending events (same object shape as a webhook). There is no
offset/cursor in Zalo's API, so we dedupe on message_id to avoid re-processing.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

import httpx

from app.agent import chat
from app.config import settings

logger = logging.getLogger("uvicorn.error")

_POLL_TIMEOUT = 30  # seconds Zalo holds the request open
_SEEN_MAX = 500  # recent message_ids kept for dedupe


async def poll_loop() -> None:
    token = settings.zalo_bot_token
    if not token:
        logger.warning("HOMESTAY_ZALO_BOT_TOKEN unset — Zalo poller not started")
        return

    url = f"{chat.API_BASE}/bot{token}/getUpdates"
    seen: deque[str] = deque(maxlen=_SEEN_MAX)
    logger.info("Zalo poller started")

    async with httpx.AsyncClient(timeout=_POLL_TIMEOUT + 10) as client:
        while True:
            try:
                resp = await client.post(url, json={"timeout": _POLL_TIMEOUT})
                data = resp.json()
                # getUpdates returns one event in `result` (a dict), or ok:false
                # (408) when the long-poll times out with no messages.
                event = data.get("result")
                if not data.get("ok") or not isinstance(event, dict):
                    await asyncio.sleep(0.5)
                    continue
                parsed = chat.parse_text_event(event)
                if parsed is None:
                    continue
                mid = parsed["message_id"]
                if mid and mid in seen:
                    continue  # at-least-once delivery — skip duplicates
                if mid:
                    seen.append(mid)
                await chat.route_message(
                    parsed["chat_id"], parsed["text"], parsed["display_name"], client
                )
            except asyncio.CancelledError:
                logger.info("Zalo poller stopped")
                raise
            except Exception:
                logger.exception("Zalo poll error; retrying in 3s")
                await asyncio.sleep(3)
