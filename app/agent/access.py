"""Who may use the booking bot, and who may approve others.

Two tiers:
- admins: bootstrapped from env (HOMESTAY_AGENT_ADMINS). Always allowed, and the
  only ones who can approve/revoke others. Env-only so a compromised chat can't
  promote itself.
- approved staff: granted at runtime by an admin, persisted to a JSON file on the
  media volume so it survives restarts. Plus any static HOMESTAY_AGENT_ALLOWED_SENDERS.

ponytail: single JSON file, no lock — fine for the single-worker poller that's the
only writer. Move to a DB row if you ever run multiple workers.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings

# In-memory pending requests (chat_id -> display_name). Lost on restart; the
# person just messages again. ponytail: ephemeral on purpose, not worth persisting.
_pending: dict[str, str] = {}


def _csv(raw: str | None) -> set[str]:
    return {s.strip() for s in (raw or "").split(",") if s.strip()}


def admins() -> set[str]:
    return _csv(settings.agent_admins)


def _store_path() -> Path:
    return Path(settings.media_root) / ".zalo_allowed.json"


def _load_store() -> dict[str, str]:
    """Approved chat_id -> display_name. Tolerates the old list-of-ids format."""
    p = _store_path()
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    if isinstance(data, list):  # back-compat: old format had no names
        return {cid: "" for cid in data}
    return data


def _save_store(members: dict[str, str]) -> None:
    p = _store_path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(members, ensure_ascii=False))
    tmp.replace(p)  # atomic


def is_allowed(chat_id: str) -> bool:
    return chat_id in admins() or chat_id in _csv(settings.agent_allowed_senders) or chat_id in _load_store()


def is_admin(chat_id: str) -> bool:
    return chat_id in admins()


def approve(chat_id: str, display_name: str = "") -> None:
    members = _load_store()
    # keep an existing name if this approve call didn't bring one
    members[chat_id] = display_name or members.get(chat_id, "")
    _save_store(members)
    _pending.pop(chat_id, None)


def revoke(chat_id: str) -> None:
    members = _load_store()
    members.pop(chat_id, None)
    _save_store(members)


def add_pending(chat_id: str, display_name: str) -> bool:
    """Record an access request. Returns True if it's new (not already pending)."""
    if chat_id in _pending:
        return False
    _pending[chat_id] = display_name
    return True


def pending() -> dict[str, str]:
    return dict(_pending)


def approved_members() -> dict[str, str]:
    """Everyone currently allowed, chat_id -> display label (for /list)."""
    members = {cid: "(quản lý)" for cid in admins()}
    members.update({cid: "" for cid in _csv(settings.agent_allowed_senders)})
    members.update(_load_store())  # stored names win
    return members
