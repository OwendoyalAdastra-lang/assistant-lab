#!/usr/bin/env python3
"""
Assistant Lab — Chat Server

Run this on a computer everyone can reach (same Wi‑Fi / LAN).
Players connect from the game chat panel (press C).

    python3 assistant_lab_chat_server.py
    python3 assistant_lab_chat_server.py --host 0.0.0.0 --port 9876

Default: 127.0.0.1:9876 (local testing — only same machine)
Use --host 0.0.0.0 for other players on your network.
"""

from __future__ import annotations

import argparse
import json
import socket
import socketserver
import threading
import time
from typing import Any

from profanity_filter import contains_profanity, friendly_message
from assistant_lab_data import (
    COSMETIC_CATALOG,
    CRATE_TYPES,
    format_crate_drop_line,
    format_lab_join_message,
)
from assistant_lab_owner_protocol import AdminServerManager
from assistant_lab_chat_log import chat_log_manager
from assistant_lab_host_auth import authorize_server_start
from assistant_lab_trade import TradeManager
from assistant_lab_world import WorldManager

MAX_MESSAGE_LEN = 120
MAX_NAME_LEN = 20

trade_manager = TradeManager()
world_manager = WorldManager()
admin_manager = AdminServerManager()


class ChatClientHandler(socketserver.StreamRequestHandler):
    name = ""
    lock = threading.Lock()
    clients: set["ChatClientHandler"] = set()

    def handle(self) -> None:
        with ChatClientHandler.lock:
            ChatClientHandler.clients.add(self)
        try:
            for raw in self.rfile:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    self._send({"type": "error", "text": "Bad message format."})
                    continue
                self._handle_packet(data)
        finally:
            self._leave()

    def _handle_packet(self, data: dict[str, Any]) -> None:
        mtype = data.get("type")
        if mtype == "join":
            name = str(data.get("name", "Player")).strip()[:MAX_NAME_LEN] or "Player"
            if contains_profanity(name):
                self._send({"type": "error", "text": friendly_message()})
                return
            self.name = name
            admin_manager.on_player_join(self, self.name)
            self._broadcast_system(format_lab_join_message(self.name))
            self._send_roster()
        elif mtype == "msg":
            if not self.name:
                self._send({"type": "error", "text": "Join first."})
                return
            text = str(data.get("text", "")).strip()
            if not text:
                return
            if len(text) > MAX_MESSAGE_LEN:
                self._send({"type": "error", "text": f"Max {MAX_MESSAGE_LEN} characters."})
                return
            if contains_profanity(text):
                self._send({"type": "error", "text": friendly_message()})
                return
            self._broadcast({
                "type": "chat",
                "name": self.name,
                "text": text,
                "ts": time.strftime("%H:%M"),
            })
        elif mtype == "leave":
            self._leave()
        elif mtype == "crate_drop":
            if not self.name:
                self._send({"type": "error", "text": "Join first."})
                return
            crate_id = str(data.get("crate_id", ""))
            item_id = str(data.get("item_id", ""))
            rarity = str(data.get("rarity", "common"))
            if crate_id not in CRATE_TYPES or item_id not in COSMETIC_CATALOG:
                return
            item = COSMETIC_CATALOG[item_id]
            if item.get("rarity") != rarity:
                rarity = str(item.get("rarity", "common"))
            duplicate = bool(data.get("duplicate"))
            try:
                refund = max(0, int(data.get("refund") or 0))
            except (TypeError, ValueError):
                refund = 0
            text = format_crate_drop_line(
                self.name, crate_id, item_id, rarity, duplicate=duplicate, refund=refund,
            )
            self._broadcast({
                "type": "crate_drop",
                "name": self.name,
                "text": text,
                "crate_id": crate_id,
                "item_id": item_id,
                "rarity": rarity,
                "duplicate": duplicate,
                "refund": refund,
                "ts": time.strftime("%H:%M"),
            })
        elif mtype in ("trade_offer", "trade_confirm", "trade_cancel"):
            with ChatClientHandler.lock:
                clients = list(ChatClientHandler.clients)
            trade_manager.handle_packet(self, data, clients)
        elif mtype in ("world_join", "world_move", "world_leave", "world_emote", "world_flex_update"):
            with ChatClientHandler.lock:
                clients = list(ChatClientHandler.clients)
            world_manager.handle_packet(self, data, clients)
        elif mtype in (
            "admin_login", "admin_broadcast", "admin_roster", "admin_grant",
            "admin_chatlogs", "admin_clear_logs",
        ):
            with ChatClientHandler.lock:
                clients = list(ChatClientHandler.clients)
            admin_manager.handle_packet(self, data, clients)

    def _send(self, payload: dict[str, Any]) -> None:
        try:
            line = json.dumps(payload, ensure_ascii=True) + "\n"
            self.wfile.write(line.encode("utf-8"))
            self.wfile.flush()
        except OSError:
            pass

    def _leave(self) -> None:
        with ChatClientHandler.lock:
            if self in ChatClientHandler.clients:
                ChatClientHandler.clients.remove(self)
        if self.name:
            with ChatClientHandler.lock:
                clients = list(ChatClientHandler.clients)
            trade_manager.on_disconnect(self.name, clients)
            world_manager.on_disconnect(self.name, clients)
            self._broadcast_system(f"{self.name} left the lab.")
            self.name = ""

    def _broadcast(self, payload: dict[str, Any]) -> None:
        chat_log_manager.record_payload(payload)
        with ChatClientHandler.lock:
            targets = list(ChatClientHandler.clients)
        for client in targets:
            client._send(payload)

    def _broadcast_system(self, text: str) -> None:
        self._broadcast({"type": "system", "text": text})
        self._send_roster()

    def _send_roster(self) -> None:
        with ChatClientHandler.lock:
            names = sorted({c.name for c in ChatClientHandler.clients if c.name})
        payload = {"type": "roster", "players": names}
        with ChatClientHandler.lock:
            targets = list(ChatClientHandler.clients)
        for client in targets:
            client._send(payload)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistant Lab chat server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (0.0.0.0 for LAN)")
    parser.add_argument("--port", type=int, default=9876, help="TCP port")
    args = parser.parse_args()

    ok, auth_msg = authorize_server_start(args.host)
    if not ok:
        print("")
        print("=== Chat server did not start ===")
        print(auth_msg)
        print("")
        return 1
    if auth_msg:
        print(auth_msg)

    try:
        server = ThreadedTCPServer((args.host, args.port), ChatClientHandler)
    except OSError as exc:
        if exc.errno in (98, 48):  # Linux EADDRINUSE, macOS EADDRINUSE
            print("")
            print("=== Chat server did not start ===")
            print(f"Port {args.port} is already in use.")
            print("")
            print("Another chat server is probably still running.")
            print("  macOS/Linux: pkill -f assistant_lab_chat_server.py")
            print("  Or close the other Terminal window running the server.")
            print(f"  Or use another port: ./run.sh server-lan  # then edit --port {args.port + 1}")
            print("")
            return 1
        raise

    with server:
        host_label = args.host if args.host != "0.0.0.0" else "all interfaces"
        print(f"Assistant Lab chat server on {host_label}:{args.port}")
        print("Players: C = chat  •  T = trade  •  L = Social Lab (WASD to walk)")
        print("Chat logs: assistant_lab_chat_log.json (server-side only)")
        if args.host == "127.0.0.1":
            print("LAN play: restart with --host 0.0.0.0")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nChat server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())