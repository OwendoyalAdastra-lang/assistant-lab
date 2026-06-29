"""
Assistant Lab — persistent chat server logs.

Records player chat, system events, crate drops, and admin broadcasts.
Written by assistant_lab_chat_server.py; viewed in the admin panel Logs tab.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from assistant_lab_data import CHAT_LOG_PATH

MAX_LOG_ENTRIES = 1000
DEFAULT_FETCH_LIMIT = 300


def _kind_from_payload(payload: dict[str, Any]) -> str:
    mtype = payload.get("type", "")
    if mtype == "chat":
        return "chat"
    if mtype == "crate_drop":
        return "drops"
    if mtype == "system":
        return "system"
    return "other"


class ChatLogManager:
    """Thread-safe ring buffer persisted to disk."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[dict[str, Any]] = []
        self._load()

    def record_payload(self, payload: dict[str, Any]) -> None:
        """Log a broadcast packet from the chat server."""
        mtype = payload.get("type")
        if mtype not in ("chat", "system", "crate_drop"):
            return
        kind = _kind_from_payload(payload)
        name = str(payload.get("name", ""))[:20]
        text = str(payload.get("text", ""))[:240]
        if not text:
            return
        entry: dict[str, Any] = {
            "kind": kind,
            "name": name,
            "text": text,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if mtype == "crate_drop":
            entry["crate_id"] = payload.get("crate_id", "")
            entry["item_id"] = payload.get("item_id", "")
            entry["rarity"] = payload.get("rarity", "")
        self.append(entry)

    def append(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > MAX_LOG_ENTRIES:
                self._entries = self._entries[-MAX_LOG_ENTRIES:]
            self._save()

    def get_entries(
        self,
        *,
        kind: str = "all",
        limit: int = DEFAULT_FETCH_LIMIT,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(MAX_LOG_ENTRIES, int(limit)))
        with self._lock:
            rows = list(self._entries)
        if kind and kind != "all":
            rows = [r for r in rows if r.get("kind") == kind]
        return rows[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._entries = []
            self._save()

    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def _load(self) -> None:
        if not os.path.isfile(CHAT_LOG_PATH):
            return
        try:
            with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        if isinstance(raw, list):
            self._entries = [e for e in raw if isinstance(e, dict)][-MAX_LOG_ENTRIES:]

    def _save(self) -> None:
        try:
            with open(CHAT_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2)
        except OSError:
            pass


chat_log_manager = ChatLogManager()


def load_chat_logs_from_disk(
    *,
    kind: str = "all",
    limit: int = DEFAULT_FETCH_LIMIT,
) -> list[dict[str, Any]]:
    """Read logs from disk (for admin panel when server is on the same machine)."""
    if not os.path.isfile(CHAT_LOG_PATH):
        return []
    try:
        with open(CHAT_LOG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(raw, list):
        return []
    rows = [e for e in raw if isinstance(e, dict)]
    if kind and kind != "all":
        rows = [r for r in rows if r.get("kind") == kind]
    limit = max(1, min(MAX_LOG_ENTRIES, int(limit)))
    return rows[-limit:]