"""
Assistant Lab — chat server admin protocol (owner-hosted servers only).

Remote admin is OFF unless the host sets:
    export ASSISTANT_LAB_ADMIN_PIN=your_secret_pin

The admin panel app is not distributed with the public game.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any

from assistant_lab_chat_log import chat_log_manager
from assistant_lab_data import (
    COSMETIC_CATALOG,
    PENDING_GRANTS_PATH,
    cosmetics_by_rarity,
    get_admin_server_pin,
    normalize_player_key,
)

MAX_ADMIN_BROADCAST = 200
MAX_ADMIN_CREDITS = 9999
MAX_ADMIN_ITEMS = 12


def admin_enabled() -> bool:
    return bool(get_admin_server_pin())


def _valid_item_ids(items) -> list[str]:
    if not isinstance(items, list):
        return []
    out = []
    for raw in items:
        iid = str(raw).strip()
        if iid in COSMETIC_CATALOG and iid not in out:
            out.append(iid)
        if len(out) >= MAX_ADMIN_ITEMS:
            break
    return out


def _load_pending() -> dict[str, list[dict[str, Any]]]:
    if not os.path.isfile(PENDING_GRANTS_PATH):
        return {}
    try:
        with open(PENDING_GRANTS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for key, grants in raw.items():
        if not isinstance(grants, list):
            continue
        clean = []
        for g in grants:
            if not isinstance(g, dict):
                continue
            try:
                credits = max(0, min(MAX_ADMIN_CREDITS, int(g.get("credits", 0))))
            except (TypeError, ValueError):
                credits = 0
            items = _valid_item_ids(g.get("items", []))
            if credits == 0 and not items:
                continue
            clean.append({
                "credits": credits,
                "items": items,
                "message": str(g.get("message", ""))[:120],
            })
        if clean:
            out[str(key)] = clean
    return out


def _save_pending(data: dict[str, list[dict[str, Any]]]) -> None:
    try:
        with open(PENDING_GRANTS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def _gift_label(credits: int, items: list[str]) -> str:
    parts = []
    if credits:
        parts.append(f"{credits} CR")
    for iid in items:
        parts.append(COSMETIC_CATALOG.get(iid, {}).get("name", iid))
    return ", ".join(parts) if parts else "a gift"


class AdminServerManager:
    """Handles admin_* packets on the chat server (disabled without ASSISTANT_LAB_ADMIN_PIN)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def handle_packet(self, handler, data: dict[str, Any], clients: list) -> None:
        if not admin_enabled():
            handler._send({"type": "admin_error", "text": "Admin is not enabled on this server."})
            return
        mtype = data.get("type")
        if mtype == "admin_login":
            self._login(handler, data)
        elif mtype == "admin_broadcast":
            self._broadcast(handler, data, clients)
        elif mtype == "admin_roster":
            self._roster(handler, data, clients)
        elif mtype == "admin_grant":
            self._grant(handler, data, clients)
        elif mtype == "admin_chatlogs":
            self._chatlogs(handler, data)
        elif mtype == "admin_clear_logs":
            self._clear_logs(handler, data)

    def on_player_join(self, handler, name: str) -> None:
        key = normalize_player_key(name)
        if not key:
            return
        with self._lock:
            pending = _load_pending()
            grants = pending.pop(key, [])
            if grants:
                _save_pending(pending)
        for gift in grants:
            handler._send({
                "type": "admin_gift",
                "credits": gift.get("credits", 0),
                "items": gift.get("items", []),
                "message": gift.get("message", ""),
                "from": "Admin",
            })

    def _check_pin(self, handler, data: dict[str, Any]) -> bool:
        expected = get_admin_server_pin()
        if not expected:
            handler._send({"type": "admin_error", "text": "Admin is not enabled on this server."})
            return False
        if getattr(handler, "_admin_authed", False):
            return True
        if str(data.get("pin", "")) == expected:
            handler._admin_authed = True
            return True
        handler._send({"type": "admin_error", "text": "Invalid admin PIN."})
        return False

    def _login(self, handler, data: dict[str, Any]) -> None:
        if self._check_pin(handler, data):
            handler._send({"type": "admin_ok", "text": "Admin session active."})

    def _broadcast(self, handler, data: dict[str, Any], clients: list) -> None:
        if not self._check_pin(handler, data):
            return
        text = str(data.get("text", "")).strip()
        if not text:
            handler._send({"type": "admin_error", "text": "Message is empty."})
            return
        if len(text) > MAX_ADMIN_BROADCAST:
            handler._send({"type": "admin_error", "text": f"Max {MAX_ADMIN_BROADCAST} characters."})
            return
        payload = {"type": "system", "text": f"★ ADMIN BROADCAST: {text}"}
        chat_log_manager.record_payload(payload)
        for client in clients:
            client._send(payload)
        handler._send({"type": "admin_ok", "text": "Broadcast sent to all players."})

    def _roster(self, handler, data: dict[str, Any], clients: list) -> None:
        if not self._check_pin(handler, data):
            return
        names = sorted({c.name for c in clients if c.name})
        handler._send({"type": "admin_roster", "players": names})

    def _grant(self, handler, data: dict[str, Any], clients: list) -> None:
        if not self._check_pin(handler, data):
            return
        target = str(data.get("target", "")).strip()[:20]
        if not target:
            handler._send({"type": "admin_error", "text": "Enter a player name."})
            return
        try:
            credits = max(0, min(MAX_ADMIN_CREDITS, int(data.get("credits", 0))))
        except (TypeError, ValueError):
            credits = 0
        items = _valid_item_ids(data.get("items", []))
        rarity = str(data.get("rarity", "")).strip().lower()
        if rarity and rarity != "none":
            for iid in cosmetics_by_rarity(rarity):
                if iid not in items:
                    items.append(iid)
            items = items[:MAX_ADMIN_ITEMS]
        if credits == 0 and not items:
            handler._send({"type": "admin_error", "text": "Add credits or at least one item."})
            return
        gift = {"credits": credits, "items": items, "message": str(data.get("message", ""))[:120]}
        label = _gift_label(credits, items)
        online = None
        for client in clients:
            if client.name and client.name.lower() == target.lower():
                online = client
                break
        if online:
            online._send({
                "type": "admin_gift",
                "credits": credits,
                "items": items,
                "message": gift.get("message", ""),
                "from": "Admin",
            })
            handler._send({
                "type": "admin_ok",
                "text": f"Granted {label} to {online.name} (online).",
            })
            return
        key = normalize_player_key(target)
        with self._lock:
            pending = _load_pending()
            pending.setdefault(key, []).append(gift)
            _save_pending(pending)
        handler._send({
            "type": "admin_ok",
            "text": f"Queued {label} for {target} (offline — delivers on join).",
        })

    def _chatlogs(self, handler, data: dict[str, Any]) -> None:
        if not self._check_pin(handler, data):
            return
        kind = str(data.get("filter", "all")).strip().lower() or "all"
        try:
            limit = int(data.get("limit", 300))
        except (TypeError, ValueError):
            limit = 300
        entries = chat_log_manager.get_entries(kind=kind, limit=limit)
        handler._send({
            "type": "admin_chatlogs",
            "entries": entries,
            "total": chat_log_manager.count(),
            "filter": kind,
        })

    def _clear_logs(self, handler, data: dict[str, Any]) -> None:
        if not self._check_pin(handler, data):
            return
        chat_log_manager.clear()
        handler._send({"type": "admin_ok", "text": "Chat logs cleared."})