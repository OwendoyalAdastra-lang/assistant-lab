"""
Player settings for Assistant Lab — mute, keybinds, message timing.

Stored in assistant_lab_save.json under "settings" (not anti-cheat protected).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

try:
    import pygame
except ImportError:
    pygame = None  # type: ignore

DEFAULT_KEYBINDS = {
    "chat": "c",
    "trade": "t",
    "world": "l",
    "flex": "f",
    "build": "space",
    "settings": ",",
    "fullscreen": "f11",
}

KEYBIND_LABELS = {
    "chat": "Open Chat",
    "trade": "Open Trade",
    "world": "Social Lab",
    "flex": "Flex Emote",
    "build": "Start / Continue",
    "settings": "Settings",
    "fullscreen": "Fullscreen",
}

MESSAGE_DURATION_OPTIONS = (5, 10, 15, 20)


def default_settings() -> dict[str, Any]:
    return {
        "muted": False,
        "fullscreen": False,
        "message_duration": 10,
        "keybinds": dict(DEFAULT_KEYBINDS),
    }


def normalize_settings(raw: dict | None) -> dict[str, Any]:
    base = default_settings()
    if not isinstance(raw, dict):
        return base
    base["muted"] = bool(raw.get("muted", base["muted"]))
    base["fullscreen"] = bool(raw.get("fullscreen", base["fullscreen"]))
    try:
        dur = int(raw.get("message_duration", base["message_duration"]))
    except (TypeError, ValueError):
        dur = base["message_duration"]
    if dur not in MESSAGE_DURATION_OPTIONS:
        dur = 10 if dur < 8 else min(MESSAGE_DURATION_OPTIONS, key=lambda x: abs(x - dur))
    base["message_duration"] = dur
    binds = raw.get("keybinds")
    if isinstance(binds, dict):
        merged = dict(DEFAULT_KEYBINDS)
        for action, key in binds.items():
            if action in DEFAULT_KEYBINDS and isinstance(key, str) and key:
                merged[action] = key.lower()[:12]
        base["keybinds"] = merged
    return base


def format_key_display(key_name: str) -> str:
    labels = {
        "space": "Space",
        "escape": "Esc",
        "return": "Enter",
        "comma": ",",
        "period": ".",
        "f11": "F11",
    }
    k = (key_name or "?").lower()
    return labels.get(k, k.upper() if len(k) == 1 else k.title())


def event_to_key_name(event) -> str | None:
    if pygame is None or event.type != pygame.KEYDOWN:
        return None
    if event.key == pygame.K_SPACE:
        return "space"
    if event.key == pygame.K_F11:
        return "f11"
    if event.key == pygame.K_ESCAPE:
        return "escape"
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return "return"
    ch = (event.unicode or "").lower()
    if len(ch) == 1 and (ch.isalnum() or ch in ",."):
        return ch
    name = pygame.key.name(event.key)
    if name:
        return name.lower()
    return None


def keybind_matches(event, action: str, keybinds: dict[str, str]) -> bool:
    expected = keybinds.get(action, DEFAULT_KEYBINDS.get(action))
    if not expected:
        return False
    got = event_to_key_name(event)
    return got is not None and got == expected


def assign_keybind(keybinds: dict[str, str], action: str, key_name: str) -> tuple[bool, str]:
    key_name = (key_name or "").lower()
    if action not in DEFAULT_KEYBINDS:
        return False, "Unknown action."
    if not key_name:
        return False, "Invalid key."
    for other, bound in keybinds.items():
        if other != action and bound == key_name:
            return False, f"'{format_key_display(key_name)}' is already used for {KEYBIND_LABELS.get(other, other)}."
    keybinds[action] = key_name
    return True, f"{KEYBIND_LABELS.get(action, action)} → {format_key_display(key_name)}"