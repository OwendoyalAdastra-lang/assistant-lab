"""
Assistant Lab — Social World (shared lobby to flex your character).

Players join a 2D lab floor, walk around, and show off equipped cosmetics,
wallet, and last assistant build. Server broadcasts positions + flex profiles.
"""

from __future__ import annotations

import time
from typing import Any

from assistant_lab_chat_log import chat_log_manager
from assistant_lab_data import COSMETIC_CATALOG, RARITIES, format_world_join_message

WORLD_W = 880
WORLD_H = 480
WORLD_X_MIN, WORLD_X_MAX = 80, WORLD_W
WORLD_Y_MIN, WORLD_Y_MAX = 120, 520
MAX_FLEX_TITLE_LEN = 32


def clamp_pos(x: float, y: float) -> tuple[int, int]:
    return (
        max(WORLD_X_MIN, min(WORLD_X_MAX, int(x))),
        max(WORLD_Y_MIN, min(WORLD_Y_MAX, int(y))),
    )


def _valid_equipped(raw: dict | None, owned: list[str] | None = None) -> dict[str, str]:
    """Keep only real catalog slots; optionally require ownership."""
    if not isinstance(raw, dict):
        return {}
    owned_set = set(owned or [])
    out = {}
    for slot, iid in raw.items():
        if not isinstance(slot, str) or not isinstance(iid, str):
            continue
        if iid not in COSMETIC_CATALOG:
            continue
        if COSMETIC_CATALOG[iid].get("slot") != slot:
            continue
        if owned_set and iid not in owned_set:
            continue
        out[slot] = iid
    return out


def normalize_flex_profile(raw: dict | None) -> dict[str, Any]:
    raw = raw or {}
    owned = raw.get("owned_items") or raw.get("owned") or []
    if not isinstance(owned, list):
        owned = []
    owned = [str(i) for i in owned if str(i) in COSMETIC_CATALOG][:40]
    equipped = _valid_equipped(raw.get("equipped"), owned if owned else None)
    tags = raw.get("last_tags") or []
    if not isinstance(tags, list):
        tags = []
    title = str(raw.get("flex_title", "Lab Builder"))[:MAX_FLEX_TITLE_LEN]
    try:
        wallet = max(0, min(9999, int(raw.get("wallet", 0))))
    except (TypeError, ValueError):
        wallet = 0
    try:
        owned_count = max(0, int(raw.get("owned_count", len(owned))))
    except (TypeError, ValueError):
        owned_count = len(owned)
    try:
        legendary_count = max(0, int(raw.get("legendary_count", 0)))
    except (TypeError, ValueError):
        legendary_count = 0
    try:
        ultra_count = max(0, int(raw.get("ultra_count", 0)))
    except (TypeError, ValueError):
        ultra_count = 0
    try:
        mythic_count = max(0, int(raw.get("mythic_count", 0)))
    except (TypeError, ValueError):
        mythic_count = 0
    try:
        god_count = max(0, int(raw.get("god_count", 0)))
    except (TypeError, ValueError):
        god_count = 0
    return {
        "avatar_name": str(raw.get("avatar_name", "Mentor"))[:20],
        "equipped": equipped,
        "wallet": wallet,
        "owned_count": owned_count,
        "legendary_count": legendary_count,
        "ultra_count": ultra_count,
        "mythic_count": mythic_count,
        "god_count": god_count,
        "owned_items": owned[:12],
        "last_assistant": str(raw.get("last_assistant", ""))[:28],
        "last_rating": str(raw.get("last_rating", ""))[:24],
        "last_tags": [str(t)[:20] for t in tags[:6]],
        "flex_title": title or "Lab Builder",
    }


def flex_rarity_breakdown(owned_items: list[str]) -> dict[str, int]:
    counts = {k: 0 for k in RARITIES}
    for iid in owned_items:
        r = COSMETIC_CATALOG.get(iid, {}).get("rarity", "common")
        counts[r] = counts.get(r, 0) + 1
    return counts


class WorldManager:
    """Server-side social world roster."""

    def __init__(self):
        self._players: dict[str, dict[str, Any]] = {}

    def _snapshot(self) -> list[dict[str, Any]]:
        out = []
        for name, p in self._players.items():
            out.append({
                "name": name,
                "x": p.get("x", 400),
                "y": p.get("y", 300),
                "avatar_name": p.get("avatar_name", "Mentor"),
                "equipped": p.get("equipped", {}),
                "wallet": p.get("wallet", 0),
                "owned_count": p.get("owned_count", 0),
                "legendary_count": p.get("legendary_count", 0),
                "ultra_count": p.get("ultra_count", 0),
                "mythic_count": p.get("mythic_count", 0),
                "god_count": p.get("god_count", 0),
                "owned_items": p.get("owned_items", []),
                "last_assistant": p.get("last_assistant", ""),
                "last_rating": p.get("last_rating", ""),
                "last_tags": p.get("last_tags", []),
                "flex_title": p.get("flex_title", "Lab Builder"),
                "emote_until": p.get("emote_until", 0),
            })
        return out

    def _broadcast(self, clients: list, payload: dict) -> None:
        if payload.get("type") == "system":
            chat_log_manager.record_payload(payload)
        for client in clients:
            client._send(payload)

    def _broadcast_state(self, clients: list) -> None:
        self._broadcast(clients, {"type": "world_state", "players": self._snapshot()})

    def handle_packet(self, handler, data: dict, clients: list) -> None:
        mtype = data.get("type")
        if mtype == "world_join":
            self._join(handler, data, clients)
        elif mtype == "world_move":
            self._move(handler, data, clients)
        elif mtype == "world_leave":
            self._leave(handler.name, clients)
        elif mtype == "world_emote":
            self._emote(handler, clients)
        elif mtype == "world_flex_update":
            self._flex_update(handler, data, clients)

    def _join(self, handler, data: dict, clients: list) -> None:
        name = handler.name
        if not name:
            handler._send({"type": "error", "text": "Join chat before entering the world."})
            return
        profile = normalize_flex_profile(data.get("profile"))
        try:
            x, y = clamp_pos(data.get("x", 400), data.get("y", 300))
        except (TypeError, ValueError):
            x, y = 400, 300
        self._players[name] = {
            **profile,
            "x": x,
            "y": y,
            "joined": time.time(),
            "emote_until": 0,
        }
        handler._send({"type": "world_joined", "name": name, "x": x, "y": y})
        self._broadcast(clients, {
            "type": "system",
            "text": format_world_join_message(name),
        })
        self._broadcast_state(clients)

    def _move(self, handler, data: dict, clients: list) -> None:
        name = handler.name
        if name not in self._players:
            return
        x, y = clamp_pos(data.get("x", 0), data.get("y", 0))
        self._players[name]["x"] = x
        self._players[name]["y"] = y
        self._broadcast(clients, {"type": "world_move", "name": name, "x": x, "y": y})

    def _flex_update(self, handler, data: dict, clients: list) -> None:
        name = handler.name
        if name not in self._players:
            return
        profile = normalize_flex_profile(data.get("profile"))
        self._players[name].update(profile)
        self._broadcast_state(clients)

    def _emote(self, handler, clients: list) -> None:
        name = handler.name
        if name not in self._players:
            return
        until = time.time() + 2.5
        self._players[name]["emote_until"] = until
        self._broadcast(clients, {
            "type": "world_emote",
            "name": name,
            "until": until,
            "text": f"{name} is flexing their lab gear!",
        })

    def _leave(self, name: str, clients: list) -> None:
        if name not in self._players:
            return
        del self._players[name]
        self._broadcast(clients, {"type": "world_player_left", "name": name})
        self._broadcast(clients, {"type": "system", "text": f"{name} left the Social Lab."})
        self._broadcast_state(clients)

    def on_disconnect(self, name: str, clients: list) -> None:
        self._leave(name, clients)