"""
Assistant Lab — multiplayer chat client (background thread + queue).

Connect to assistant_lab_chat_server.py so players can talk in the lab lobby.
"""

from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Any

from profanity_filter import contains_profanity, friendly_message

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
MAX_CHAT_LOG = 80
MAX_MESSAGE_LEN = 120


class ChatClient:
    """Thread-safe chat client; poll events from the main pygame loop."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._events: queue.Queue[dict[str, Any]] = queue.Queue()
        self.connected = False
        self.player_name = "Player"
        self.last_error = ""

    def _emit(self, event: dict[str, Any]) -> None:
        self._events.put(event)

    def poll_events(self) -> list[dict[str, Any]]:
        out = []
        while True:
            try:
                out.append(self._events.get_nowait())
            except queue.Empty:
                break
        return out

    def connect(self, player_name: str) -> bool:
        self.disconnect()
        self.player_name = (player_name or "Player").strip()[:20] or "Player"
        if contains_profanity(self.player_name):
            self.last_error = friendly_message()
            self._emit({"type": "error", "text": self.last_error})
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(8.0)
            sock.connect((self.host, self.port))
            sock.settimeout(0.5)
            self._sock = sock
            self._running = True
            self._send({"type": "join", "name": self.player_name})
            self._thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._thread.start()
            self.connected = True
            self.last_error = ""
            self._emit({"type": "status", "text": f"Connected to {self.host}:{self.port}"})
            return True
        except OSError as exc:
            self.last_error = str(exc)
            self._emit({
                "type": "error",
                "text": (
                    f"No chat server at {self.host}:{self.port}. "
                    "Solo play works without it. For chat, open another Terminal and run: "
                    "./run.sh server"
                ),
            })
            self.disconnect()
            return False

    def disconnect(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._send({"type": "leave"})
            except OSError:
                pass
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self.connected = False

    def _send(self, payload: dict[str, Any]) -> None:
        if not self._sock:
            return
        line = json.dumps(payload, ensure_ascii=True) + "\n"
        self._sock.sendall(line.encode("utf-8"))

    def send_message(self, text: str) -> tuple[bool, str | None]:
        msg = text.strip()
        if not msg:
            return False, "Type a message first."
        if len(msg) > MAX_MESSAGE_LEN:
            return False, f"Max {MAX_MESSAGE_LEN} characters."
        if contains_profanity(msg):
            return False, friendly_message()
        if not self.connected:
            return False, "Not connected to chat."
        try:
            self._send({"type": "msg", "text": msg})
            return True, None
        except OSError as exc:
            self.last_error = str(exc)
            self.disconnect()
            self._emit({"type": "error", "text": "Disconnected from chat server."})
            return False, "Disconnected."

    def _reader_loop(self) -> None:
        buf = ""
        while self._running and self._sock:
            try:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self._handle_server_message(data)
            except socket.timeout:
                continue
            except OSError:
                break
            time.sleep(0.01)
        self.connected = False
        self._emit({"type": "status", "text": "Disconnected from chat."})

    def _handle_server_message(self, data: dict[str, Any]) -> None:
        mtype = data.get("type")
        if mtype == "chat":
            self._emit({
                "type": "chat",
                "name": data.get("name", "?"),
                "text": data.get("text", ""),
                "ts": data.get("ts", ""),
            })
        elif mtype == "system":
            self._emit({"type": "system", "text": data.get("text", "")})
        elif mtype == "error":
            self._emit({"type": "error", "text": data.get("text", "Chat error")})
        elif mtype == "roster":
            names = data.get("players") or []
            self._emit({"type": "roster", "players": names})
        elif mtype == "crate_drop":
            self._emit({
                "type": "crate_drop",
                "name": data.get("name", "?"),
                "text": data.get("text", ""),
                "crate_id": data.get("crate_id", ""),
                "item_id": data.get("item_id", ""),
                "rarity": data.get("rarity", "common"),
                "duplicate": bool(data.get("duplicate")),
                "refund": int(data.get("refund") or 0),
                "ts": data.get("ts", ""),
            })
        elif mtype == "admin_gift":
            self._emit({
                "type": "admin_gift",
                "credits": int(data.get("credits") or 0),
                "items": data.get("items") or [],
                "message": data.get("message", ""),
                "from": data.get("from", "Admin"),
            })
        elif mtype in (
            "trade_offer", "trade_status", "trade_execute",
            "trade_cancelled",
            "world_joined", "world_state", "world_move",
            "world_player_left", "world_emote",
        ):
            self._emit(data)

    def send_world_join(self, profile: dict, x: int, y: int) -> tuple[bool, str | None]:
        if not self.connected:
            return False, "Connect first."
        try:
            self._send({"type": "world_join", "profile": profile, "x": x, "y": y})
            return True, None
        except OSError:
            self.disconnect()
            return False, "Disconnected."

    def send_world_move(self, x: int, y: int) -> None:
        if not self.connected:
            return
        try:
            self._send({"type": "world_move", "x": x, "y": y})
        except OSError:
            self.disconnect()

    def send_world_leave(self) -> None:
        if not self.connected:
            return
        try:
            self._send({"type": "world_leave"})
        except OSError:
            pass

    def send_world_emote(self) -> None:
        if not self.connected:
            return
        try:
            self._send({"type": "world_emote"})
        except OSError:
            self.disconnect()

    def send_world_flex_update(self, profile: dict) -> None:
        if not self.connected:
            return
        try:
            self._send({"type": "world_flex_update", "profile": profile})
        except OSError:
            self.disconnect()

    def send_crate_drop(
        self,
        *,
        crate_id: str,
        item_id: str,
        rarity: str,
        duplicate: bool = False,
        refund: int = 0,
    ) -> None:
        """Broadcast a crate open to all players (lab chat Drops tab)."""
        if not self.connected:
            return
        try:
            self._send({
                "type": "crate_drop",
                "crate_id": crate_id,
                "item_id": item_id,
                "rarity": rarity,
                "duplicate": bool(duplicate),
                "refund": int(refund or 0),
            })
        except OSError:
            self.disconnect()

    def send_trade_offer(self, to: str, give: dict, want: dict) -> tuple[bool, str | None]:
        if not self.connected:
            return False, "Connect to chat first."
        try:
            self._send({"type": "trade_offer", "to": to, "give": give, "want": want})
            return True, None
        except OSError:
            self.disconnect()
            return False, "Disconnected."

    def send_trade_confirm(self, trade_id: str) -> tuple[bool, str | None]:
        if not self.connected:
            return False, "Not connected."
        try:
            self._send({"type": "trade_confirm", "trade_id": trade_id})
            return True, None
        except OSError:
            self.disconnect()
            return False, "Disconnected."

    def send_trade_cancel(self, trade_id: str) -> tuple[bool, str | None]:
        if not self.connected:
            return False, "Not connected."
        try:
            self._send({"type": "trade_cancel", "trade_id": trade_id})
            return True, None
        except OSError:
            self.disconnect()
            return False, "Disconnected."