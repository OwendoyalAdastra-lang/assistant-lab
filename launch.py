#!/usr/bin/env python3
"""Assistant Lab launcher — no .command files, no Command Line Tools."""
from __future__ import annotations

import os
import subprocess
import sys


def _find_python() -> str:
    return sys.executable


def _ensure_pygame() -> None:
    try:
        import pygame  # noqa: F401
        return
    except ImportError:
        pass
    print("Installing pygame (one time)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "pygame"])


def _server_ip() -> str | None:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "mom-server-address.txt")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="ignore") as f:
        line = f.readline().strip()
    # Strip RTF junk if TextEdit saved rich text by mistake
    for part in line.replace("{", " ").replace("}", " ").split():
        if part.count(".") == 3 and all(p.isdigit() for p in part.split(".") if p):
            return part
    return line or None


def main() -> int:
    print("Assistant Lab launcher")
    print("Python:", _find_python())
    _ensure_pygame()

    env = os.environ.copy()
    ip = _server_ip()
    if not ip:
        print()
        print("Multiplayer? Save Owen's IP in mom-server-address.txt (plain text!)")
        print("Or type it now (Enter to skip — solo play):")
        typed = input("Server IP: ").strip()
        if typed:
            ip = typed
            here = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(here, "mom-server-address.txt"), "w", encoding="utf-8") as f:
                f.write(typed + "\n")
            print("Saved mom-server-address.txt")

    if ip and ip != "127.0.0.1":
        env["ASSISTANT_LAB_CHAT_HOST"] = ip
        env["ASSISTANT_LAB_CHAT_PORT"] = "9876"
        print(f"Multiplayer → {ip}:9876")
    else:
        print("Solo play (no chat server)")

    here = os.path.dirname(os.path.abspath(__file__))
    game = os.path.join(here, "build_your_own_smart_assistant_pygame.py")
    print("Starting game...")
    return subprocess.call([sys.executable, game], env=env)


if __name__ == "__main__":
    raise SystemExit(main())