#!/usr/bin/env python3
"""
Build Your Own Smart Assistant — Pygame Edition

A colorful graphical game for young programmers inspired by Grace Hopper.

You design your own smart assistant by answering 7 questions. Watch a live
preview update as you type! At the end, an if/else scoring system rates
your design and prints a full blueprint.

Run:
    python3 build_your_own_smart_assistant_pygame.py

Controls:
    - Click buttons and type in text boxes
    - Backspace to fix typing
    - ENTER to submit / continue
    - Earn or lose lab credits based on how your build looks, works, and what it does
    - Visit the Daily Avatar Shop and open rarity crates — all saved to disk
    - Strict kid-safe language filter on all typed text
    - F11 = fullscreen (scales to fit)  •  Settings: mute, keybinds, etc.
    - Save anti-cheat blocks hand-edited wallet / items
    - ESC = quit
    - BACK button to change earlier answers

Requires: pygame (pip install pygame)
"""

import pygame
import sys
import math
import random
import json
import os
import time
from datetime import date

from profanity_filter import check_text, contains_profanity, friendly_message, tag_filter_message, validate_tag
from assistant_lab_data import (
    COSMETIC_CATALOG,
    CRATE_TYPES,
    DAILY_SHOP_SIZE,
    RARITIES,
    SAVE_PATH,
    SAVE_VERSION,
    STARTING_CREDITS,
    apply_admin_gift,
    default_save,
    format_crate_drop_line,
    is_lab_owner,
)
from assistant_lab_chat import ChatClient, DEFAULT_HOST, DEFAULT_PORT, MAX_CHAT_LOG
from assistant_lab_settings import (
    DEFAULT_KEYBINDS,
    KEYBIND_LABELS,
    MESSAGE_DURATION_OPTIONS,
    assign_keybind,
    default_settings,
    event_to_key_name,
    format_key_display,
    keybind_matches,
    normalize_settings,
)
from assistant_lab_integrity import apply_integrity_on_load, prepare_save_for_write, verify_runtime_config
from assistant_lab_trade import (
    MAX_TRADE_CREDITS,
    MAX_TRADE_ITEMS,
    apply_trade_to_save,
    bundle_label,
    can_afford_side,
    normalize_bundle,
)
from assistant_lab_world import (
    WORLD_X_MAX,
    WORLD_X_MIN,
    WORLD_Y_MAX,
    WORLD_Y_MIN,
    clamp_pos,
    flex_rarity_breakdown,
    normalize_flex_profile,
)

# Shown when strict language filter blocks input (names, avatar, design answers)
FILTER_MESSAGE = friendly_message()

# =============================================================================
# OPTIONAL NUMPY FOR RICHER SOUND
# =============================================================================
HAS_NUMPY = False
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    pass

# =============================================================================
# WINDOW & THEME — retro-futuristic coding lab (Grace Hopper era meets today)
# =============================================================================
WIDTH, HEIGHT = 960, 640
FPS = 60

# Compact layout zones — shared coordinates to prevent overlap
MARGIN = 14
HDR_TOP, HDR_HEIGHT = 8, 42
CONTENT_Y = 54
MAIN_BOTTOM = 556
ACTION_Y = 572
COLLECTION_Y = 518
FOOTER_TEXT_Y = HEIGHT - 14
FILTER_BANNER_Y = HEIGHT - 50
BTN_H, BTN_SM = 34, 26
SIDEBAR_W = 256

DARK_BG = (14, 18, 32)
PANEL_BG = (24, 30, 52)
PANEL_BORDER = (65, 85, 130)
ACCENT = (100, 200, 255)       # Hopper blue
ACCENT2 = (130, 240, 170)      # Success green
ACCENT3 = (255, 190, 90)       # Warm gold
TEXT = (238, 242, 255)
TEXT_MUTED = (155, 170, 200)
BUTTON_BG = (38, 48, 75)
BUTTON_HOVER = (58, 75, 110)
GOOD = (90, 220, 150)
BAD = (235, 105, 100)
WHITE = (255, 255, 255)
GLOW = (160, 220, 255)
PREVIEW_BG = (18, 24, 42)
PREVIEW_BORDER = (90, 130, 180)

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
pygame.display.set_caption("Build Your Own Smart Assistant")
screen = pygame.display.set_mode((WIDTH, HEIGHT))
_display_fullscreen = False
clock = pygame.time.Clock()
try:
    title_font = pygame.font.SysFont("arial", 30, bold=True)
    header_font = pygame.font.SysFont("arial", 20, bold=True)
    question_font = pygame.font.SysFont("arial", 18, bold=True)
    body_font = pygame.font.SysFont("arial", 15)
    small_font = pygame.font.SysFont("arial", 13)
    button_font = pygame.font.SysFont("arial", 14, bold=True)
    name_font = pygame.font.SysFont("arial", 22, bold=True)
except Exception:
    title_font = pygame.font.Font(None, 36)
    header_font = pygame.font.Font(None, 24)
    question_font = pygame.font.Font(None, 22)
    body_font = pygame.font.Font(None, 18)
    small_font = pygame.font.Font(None, 16)
    button_font = pygame.font.Font(None, 18)
    name_font = pygame.font.Font(None, 26)

# =============================================================================
# DESIGN QUESTIONS (same data as the text version)
# =============================================================================
DESIGN_QUESTIONS = [
    {
        "id": "name",
        "text": "What should we name your smart assistant?",
        "hint": "Short, memorable names work best (e.g., Nova, Byte, Echo).",
        "keywords": ["nova", "byte", "echo", "lumen", "atlas", "spark"],
    },
    {
        "id": "purpose",
        "text": "What is its main purpose? What problem should it solve?",
        "hint": "Be specific — 'help with homework' beats just 'help people'.",
        "keywords": ["homework", "study", "learn", "organize", "remind", "schedule", "code", "research"],
    },
    {
        "id": "personality",
        "text": "What personality should it have?",
        "hint": "Friendly, witty, calm, encouraging — make it feel real!",
        "keywords": ["friendly", "kind", "patient", "witty", "calm", "encouraging", "helpful", "cheerful"],
    },
    {
        "id": "skills",
        "text": "What special skills should it have? List at least two.",
        "hint": "Translate, calculate, tell jokes, search the web, play music...",
        "keywords": ["translate", "calculate", "math", "code", "search", "remind", "joke", "weather", "music"],
    },
    {
        "id": "memory",
        "text": "Should it remember things? If yes, what?",
        "hint": "Good assistants remember names, preferences, and past chats.",
        "keywords": ["remember", "preferences", "name", "history", "notes", "birthday", "favorite"],
    },
    {
        "id": "voice",
        "text": "How should it communicate?",
        "hint": "Voice, text, both, sign language — more ways = more accessible.",
        "keywords": ["voice", "text", "both", "chat", "speak", "screen", "sign"],
    },
    {
        "id": "safety",
        "text": "What safety rules should it follow?",
        "hint": "Privacy, kindness, asking a grown-up — real AI needs rules!",
        "keywords": ["privacy", "kind", "safe", "permission", "parent", "teacher", "honest", "respect"],
    },
]

LABELS = {
    "name": "Assistant Name",
    "purpose": "Main Purpose",
    "personality": "Personality",
    "skills": "Special Skills",
    "memory": "Memory & Recall",
    "voice": "Communication Style",
    "safety": "Safety Rules",
}

MIN_ANSWER_LENGTH = 3
MAX_TAGS_TOTAL = 6
MAX_CUSTOM_TAGS = 3
MAX_TAG_LIBRARY = 12
CUSTOM_TAG_COST = 15  # Preset/default tags are free; typed + library custom tags cost CR

# Preset tags — click to toggle. Custom tags are typed and filter-checked.
PRESET_TAGS = (
    {"id": "homework", "label": "Homework", "color": (100, 200, 255)},
    {"id": "study", "label": "Study Buddy", "color": (130, 240, 170)},
    {"id": "coding", "label": "Coding", "color": (100, 200, 255)},
    {"id": "creative", "label": "Creative", "color": (255, 190, 90)},
    {"id": "music", "label": "Music", "color": (190, 140, 255)},
    {"id": "science", "label": "Science", "color": (90, 220, 200)},
    {"id": "reading", "label": "Reading", "color": (255, 170, 120)},
    {"id": "math", "label": "Math", "color": (130, 240, 170)},
    {"id": "organizer", "label": "Organizer", "color": (100, 200, 255)},
    {"id": "reminders", "label": "Reminders", "color": (255, 190, 90)},
    {"id": "friendly", "label": "Friendly", "color": (90, 220, 150)},
    {"id": "sports", "label": "Sports", "color": (255, 140, 100)},
)

FILTER_TAG_QUIP = tag_filter_message()

# Each answer is scored in one of three buckets that drive lab credits:
#   looks  — how polished and personable the assistant appears
#   does   — what problems it solves and what it can do
#   works  — how reliably it runs (memory, comms, safety)
QUESTION_CATEGORY = {
    "name": "looks",
    "personality": "looks",
    "purpose": "does",
    "skills": "does",
    "memory": "works",
    "voice": "works",
    "safety": "works",
}

CATEGORY_INFO = {
    "looks": {"label": "How It Looks", "color": (255, 170, 120), "icon": "◆"},
    "does": {"label": "What It Does", "color": (120, 220, 255), "icon": "⚙"},
    "works": {"label": "How It Works", "color": (140, 240, 170), "icon": "⚡"},
}

# Points (0–3 per answer) map to credit gains/losses per category
CREDIT_BY_POINTS = {3: 12, 2: 6, 1: 1, 0: -10}

# =============================================================================
# PERSISTENT SAVE + DAILY SHOP (anti-restart: written to disk immediately)
# =============================================================================
save_data = {}
_save_file_mtime = 0.0
chat_client = ChatClient()
CHAT_HOST = os.environ.get("ASSISTANT_LAB_CHAT_HOST", DEFAULT_HOST)
CHAT_PORT = int(os.environ.get("ASSISTANT_LAB_CHAT_PORT", str(DEFAULT_PORT)))

_SYNC_KEYS = (
    "wallet_credits", "owned_cosmetics", "equipped",
    "shop_date", "shop_items", "shop_bought_today",
    "crates_opened", "crate_seed", "last_crate_open",
    "runs_completed", "avatar_name", "player_name",
    "custom_tag_library", "settings", "save_hmac",
    "admin_signed", "integrity_ok", "last_build",
    "completed_trades", "trade_history",
)


def is_fullscreen() -> bool:
    return _display_fullscreen


def apply_display_mode(fullscreen: bool | None = None) -> None:
    """Windowed 960×640 or scaled fullscreen."""
    global screen, _display_fullscreen
    if fullscreen is None:
        fullscreen = bool(get_settings().get("fullscreen", False))
    _display_fullscreen = bool(fullscreen)
    if _display_fullscreen:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))


def toggle_fullscreen() -> None:
    s = get_settings()
    s["fullscreen"] = not s.get("fullscreen", False)
    save_settings(s)
    apply_display_mode(s["fullscreen"])
    if state.get("settings_open"):
        state["settings_status"] = "Fullscreen on." if s["fullscreen"] else "Windowed mode."


def get_settings() -> dict:
    return normalize_settings(save_data.get("settings"))


def save_settings(settings: dict) -> None:
    save_data["settings"] = normalize_settings(settings)
    write_save()


def set_avatar_message(msg: str) -> None:
    state["avatar_message"] = msg
    if msg:
        state["avatar_message_until"] = time.time() + get_settings().get("message_duration", 10)
    else:
        state["avatar_message_until"] = 0.0


def get_avatar_message() -> str:
    until = state.get("avatar_message_until", 0.0)
    if state.get("avatar_message") and until and time.time() > until:
        state["avatar_message"] = ""
        state["avatar_message_until"] = 0.0
    return state.get("avatar_message", "")


def set_shop_message(msg: str) -> None:
    state["shop_message"] = msg
    if msg:
        state["shop_message_until"] = time.time() + get_settings().get("message_duration", 10)
    else:
        state["shop_message_until"] = 0.0


def get_shop_message() -> str:
    until = state.get("shop_message_until", 0.0)
    if state.get("shop_message") and until and time.time() > until:
        state["shop_message"] = ""
        state["shop_message_until"] = 0.0
    return state.get("shop_message", "")


def purchases_allowed() -> bool:
    """Block shop/crates when save was tampered or game files were modified."""
    if not verify_runtime_config():
        return False
    if save_data.get("integrity_violation"):
        return False
    return bool(save_data.get("integrity_ok", True))


def _apply_loaded_save(merged: dict) -> dict:
    """Common path after reading JSON from disk."""
    global save_data
    merged["version"] = SAVE_VERSION
    merged, integrity_warning = apply_integrity_on_load(merged)
    save_data = merged
    save_data["settings"] = normalize_settings(save_data.get("settings"))
    if integrity_warning:
        state["integrity_warning"] = integrity_warning
    elif save_data.get("integrity_ok"):
        state.pop("integrity_warning", None)
    if not save_data.get("crate_seed"):
        save_data["crate_seed"] = str(random.randint(100000, 999999))
    ensure_daily_shop()
    return save_data


def _touch_save_mtime() -> None:
    global _save_file_mtime
    try:
        _save_file_mtime = os.path.getmtime(SAVE_PATH)
    except OSError:
        _save_file_mtime = 0.0


def sync_save_from_disk(*, force: bool = False) -> bool:
    """
    Reload wallet/shop/cosmetics when assistant_lab_save.json changes on disk.

    Picks up admin-panel edits without restarting the game.
    """
    global _save_file_mtime
    if not os.path.isfile(SAVE_PATH):
        return False
    try:
        mtime = os.path.getmtime(SAVE_PATH)
    except OSError:
        return False
    if not force and mtime == _save_file_mtime:
        return False
    _save_file_mtime = mtime
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False
    merged = {**default_save(), **data}
    if merged.get("version") not in (1, 2, 3, 4, SAVE_VERSION):
        return False
    in_progress = save_data.get("in_progress")
    _apply_loaded_save(merged)
    if in_progress is not None:
        save_data["in_progress"] = in_progress
    fs = bool(get_settings().get("fullscreen", False))
    if fs != _display_fullscreen:
        apply_display_mode(fs)
    return True


def load_save():
    """Load wallet/shop/cosmetics from disk. Survives game restarts."""
    global save_data, _save_file_mtime
    if os.path.isfile(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**default_save(), **data}
            if merged.get("version") in (1, 2, 3, 4, SAVE_VERSION):
                _apply_loaded_save(merged)
                write_save()
                _touch_save_mtime()
                return save_data
        except (json.JSONDecodeError, OSError):
            pass
    save_data = default_save()
    save_data["settings"] = normalize_settings(save_data.get("settings"))
    ensure_daily_shop()
    write_save()
    _touch_save_mtime()
    return save_data


def write_save():
    """Flush save to disk so restarting cannot reroll purchases or wallet."""
    global save_data
    try:
        save_data["version"] = SAVE_VERSION
        prepare_save_for_write(save_data, admin=False)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=2)
        _touch_save_mtime()
    except OSError:
        pass


def has_saved_session():
    """True when a build was interrupted and can be resumed."""
    prog = save_data.get("in_progress")
    return bool(prog and prog.get("screen") in ("name", "avatar_name", "design", "tags"))


def clear_saved_session():
    """Drop in-progress build from the save file."""
    save_data["in_progress"] = None
    write_save()


def persist_session():
    """Auto-save player progress (name, answers, credits) to disk."""
    screen = state.get("screen")
    if screen not in ("name", "avatar_name", "design", "tags"):
        return

    if state.get("player_name"):
        save_data["player_name"] = state["player_name"]

    save_data["in_progress"] = {
        "screen": screen,
        "player_name": state.get("player_name", ""),
        "answers": dict(state.get("answers", {})),
        "current_q": state.get("current_q", 0),
        "credits": state.get("credits", STARTING_CREDITS),
        "credit_log": list(state.get("credit_log", [])),
        "run_deposited": state.get("run_deposited", False),
        "current_input": state.get("current_input", ""),
        "avatar_mood": state.get("avatar_mood", "happy"),
        "avatar_message": state.get("avatar_message", ""),
        "selected_tags": list(state.get("selected_tags", [])),
        "custom_tags": list(state.get("custom_tags", [])),
        "tag_input": state.get("tag_input", ""),
    }
    write_save()


def resume_session():
    """Restore an interrupted build from the save file."""
    prog = save_data.get("in_progress")
    if not prog or prog.get("screen") not in ("name", "avatar_name", "design", "tags"):
        return False

    state["screen"] = prog["screen"]
    state["player_name"] = prog.get("player_name") or save_data.get("player_name", "")
    state["answers"] = dict(prog.get("answers", {}))
    state["current_q"] = prog.get("current_q", 0)
    state["credits"] = prog.get("credits", STARTING_CREDITS)
    state["credit_log"] = list(prog.get("credit_log", []))
    state["run_deposited"] = prog.get("run_deposited", False)
    state["avatar_mood"] = prog.get("avatar_mood", "happy")
    set_avatar_message(prog.get("avatar_message", ""))
    state["selected_tags"] = list(prog.get("selected_tags", []))
    state["custom_tags"] = list(prog.get("custom_tags", []))
    state["tag_input"] = prog.get("tag_input", "")
    state["input_active"] = True
    state["filter_message"] = ""

    if prog["screen"] == "design":
        load_question_input()
    elif prog["screen"] == "tags":
        state["input_active"] = True
    else:
        state["current_input"] = prog.get("current_input", "")
        if prog["screen"] == "avatar_name" and not state["current_input"]:
            av = get_avatar_name()
            state["current_input"] = "" if av == "Mentor" else av

    return True


def save_last_build(score_data):
    """Remember the most recent completed assistant blueprint."""
    if not score_data:
        return
    save_data["last_build"] = {
        "assistant_name": get_answer("name", "Assistant"),
        "player_name": state.get("player_name", ""),
        "rating": score_data.get("rating", ""),
        "total": score_data.get("total", 0),
        "max": score_data.get("max", 0),
        "date": today_str(),
        "tags": get_display_tags(),
    }
    write_save()


def today_str():
    return date.today().isoformat()


def ensure_daily_shop():
    """
    Lock today's shop to the calendar date.

    Same 5 items all day for everyone — stored in save file.
    Restarting the game reloads this file instead of rerolling.
    """
    global save_data
    today = today_str()
    if save_data.get("shop_date") != today:
        rng = random.Random(f"{today}_assistant_shop_v1")
        pool = [cid for cid, c in COSMETIC_CATALOG.items() if not c.get("crate_only")]
        rng.shuffle(pool)
        save_data["shop_date"] = today
        save_data["shop_items"] = pool[:DAILY_SHOP_SIZE]
        save_data["shop_bought_today"] = []
        write_save()


def get_wallet():
    return save_data.get("wallet_credits", 0)


def get_equipped():
    return dict(save_data.get("equipped", {}))


def get_owned():
    return list(save_data.get("owned_cosmetics", []))


def get_avatar_name():
    """Player-chosen name for the credit mentor avatar (saved to disk)."""
    return save_data.get("avatar_name", "Mentor") or "Mentor"


def format_display_name(raw):
    """Capitalize a name for display."""
    val = raw.strip()
    if not val:
        return ""
    return val[0].upper() + val[1:] if len(val) > 1 else val.upper()


def validate_player_text(text):
    """
    Strict kid-safe check — blocks curse words and leet/spaced tricks.

    Returns (is_ok, error_message). Uses profanity_filter.check_text.
    """
    blocked, _msg = check_text(text)
    if blocked:
        return False, FILTER_MESSAGE
    return True, None


def reject_filtered_text(message=None):
    """Flash filter warning and play error sound."""
    state["filter_message"] = message or FILTER_MESSAGE
    state["filter_flash"] = 2.5
    play_sound("coin_down")


def save_avatar_name(raw_name):
    """Persist the mentor avatar's name."""
    val = format_display_name(raw_name)
    if not val:
        return False, "Please enter a name for your avatar."
    ok, err = validate_player_text(val)
    if not ok:
        return False, err
    save_data["avatar_name"] = val[:20]
    write_save()
    return True, f"Your avatar is now named {save_data['avatar_name']}!"


def deposit_run_earnings(net_change):
    """Bank run profit into the persistent wallet (called once per finished build)."""
    if net_change == 0:
        return
    save_data["wallet_credits"] = max(0, get_wallet() + net_change)
    save_data["runs_completed"] = save_data.get("runs_completed", 0) + 1
    write_save()


def purchase_cosmetic(item_id):
    """Buy a daily-shop item. Saves instantly — no restart exploit."""
    if not purchases_allowed():
        return False, save_data.get("integrity_message", "Anti-cheat: shop purchases disabled.")
    item = COSMETIC_CATALOG.get(item_id)
    if not item:
        return False, "Unknown item."

    if item_id in get_owned():
        return False, "You already own that cosmetic."

    if item_id not in save_data.get("shop_items", []):
        return False, "That item isn't in today's shop!"

    if item_id in save_data.get("shop_bought_today", []):
        return False, "Already purchased today (saved to disk)."

    price = item["price"]
    if get_wallet() < price:
        return False, f"Need {price} CR — you have {get_wallet()} CR."

    save_data["wallet_credits"] = get_wallet() - price
    save_data.setdefault("owned_cosmetics", []).append(item_id)
    save_data.setdefault("shop_bought_today", []).append(item_id)

    # Auto-equip into the item's slot
    slot = item["slot"]
    save_data.setdefault("equipped", {})[slot] = item_id
    write_save()
    play_sound("coin_up")
    return True, f"Bought {item['name']}! Equipped automatically."


def toggle_equip(item_id):
    """Equip or unequip an owned cosmetic."""
    item = COSMETIC_CATALOG.get(item_id)
    if not item or item_id not in get_owned():
        return False, "You don't own that yet."

    slot = item["slot"]
    equipped = save_data.setdefault("equipped", {})
    if equipped.get(slot) == item_id:
        del equipped[slot]
        write_save()
        return True, f"Unequipped {item['name']}."
    equipped[slot] = item_id
    write_save()
    play_sound("ping")
    return True, f"Equipped {item['name']}!"


def rarity_info(rarity):
    return RARITIES.get(rarity, RARITIES["common"])


def cosmetic_rarity(item_id):
    return COSMETIC_CATALOG.get(item_id, {}).get("rarity", "common")


def get_rarity_pool_counts():
    """How many cosmetics exist per rarity tier (used to split drop %)."""
    counts = {}
    for _cid, item in COSMETIC_CATALOG.items():
        rarity = item.get("rarity", "common")
        counts[rarity] = counts.get(rarity, 0) + 1
    return counts


def get_crate_rarity_percent(crate_id, rarity):
    """Percent chance to roll a given rarity from this crate."""
    for r, percent in CRATE_TYPES[crate_id]["odds"]:
        if r == rarity:
            return percent
    return 0


def get_item_drop_chance(crate_id, item_id):
    """
    Percent chance to pull a specific cosmetic from a crate.

    Formula: (rarity % for crate) ÷ (number of items in that rarity pool)
    """
    item = COSMETIC_CATALOG.get(item_id)
    if not item:
        return 0.0
    rarity = item.get("rarity", "common")
    rarity_pct = get_crate_rarity_percent(crate_id, rarity)
    pool_size = get_rarity_pool_counts().get(rarity, 1)
    return rarity_pct / pool_size


def format_drop_pct(value):
    """Pretty-print a drop percentage."""
    if value <= 0:
        return "0%"
    if value >= 10:
        return f"{value:.0f}%"
    if value >= 1:
        return f"{value:.1f}%"
    return f"{value:.2f}%"


def get_crate_drop_table(crate_id):
    """All cosmetics sorted by drop chance (highest first)."""
    rows = []
    for item_id, item in COSMETIC_CATALOG.items():
        pct = get_item_drop_chance(crate_id, item_id)
        if pct > 0:
            rows.append({
                "id": item_id,
                "name": item["name"],
                "rarity": item.get("rarity", "common"),
                "pct": pct,
                "rarity_pct": get_crate_rarity_percent(crate_id, item.get("rarity", "common")),
            })
    rows.sort(key=lambda row: (-row["pct"], row["name"]))
    return rows


def roll_crate_rarity(crate_id, open_number):
    """Deterministic rarity roll — tied to save counter so restart can't reroll."""
    crate = CRATE_TYPES[crate_id]
    seed = f"{save_data.get('crate_seed', 'lab')}_{crate_id}_{open_number}"
    roll = random.Random(seed).randint(1, 100)
    cumulative = 0
    for rarity, percent in crate["odds"]:
        cumulative += percent
        if roll <= cumulative:
            return rarity
    return "common"


def pick_crate_item(rarity, open_number, crate_id):
    """Pick a cosmetic of the rolled rarity; deterministic from open counter."""
    pool = [cid for cid, c in COSMETIC_CATALOG.items() if c.get("rarity") == rarity]
    if not pool:
        pool = list(COSMETIC_CATALOG.keys())
    rng = random.Random(f"item_{save_data.get('crate_seed')}_{crate_id}_{open_number}_{rarity}")
    rng.shuffle(pool)
    owned = set(get_owned())
    for cid in pool:
        if cid not in owned:
            return cid, False
    return rng.choice(pool), True


def open_crate(crate_id):
    """
    Open a crate — result computed and saved to disk immediately.

    Restarting after opening cannot reroll; duplicate grants a CR refund.
    """
    if not purchases_allowed():
        return False, save_data.get("integrity_message", "Anti-cheat: crate opens disabled.")
    crate = CRATE_TYPES.get(crate_id)
    if not crate:
        return False, "Unknown crate."

    price = crate["price"]
    if get_wallet() < price:
        return False, f"Need {price} CR — you have {get_wallet()} CR."

    open_num = save_data.get("crates_opened", 0)
    rarity = roll_crate_rarity(crate_id, open_num)
    item_id, is_duplicate = pick_crate_item(rarity, open_num, crate_id)
    item = COSMETIC_CATALOG[item_id]

    save_data["wallet_credits"] = get_wallet() - price
    save_data["crates_opened"] = open_num + 1

    refund = 0
    if is_duplicate:
        refund = rarity_info(rarity)["refund"]
        save_data["wallet_credits"] = get_wallet() + refund
        msg = f"Duplicate {item['name']}! +{refund} CR refund."
    else:
        save_data.setdefault("owned_cosmetics", []).append(item_id)
        slot = item["slot"]
        save_data.setdefault("equipped", {})[slot] = item_id
        msg = f"You got {rarity_info(rarity)['label']} — {item['name']}!"

    rarity_pct = get_crate_rarity_percent(crate_id, rarity)
    item_pct = get_item_drop_chance(crate_id, item_id)

    save_data["last_crate_open"] = {
        "crate_id": crate_id,
        "item_id": item_id,
        "rarity": rarity,
        "duplicate": is_duplicate,
        "refund": refund,
        "open_number": open_num,
        "rarity_pct": rarity_pct,
        "item_pct": item_pct,
    }
    write_save()

    state["crate_reveal"] = dict(save_data["last_crate_open"])
    state["crate_reveal"]["message"] = msg
    state["crate_reveal_anim"] = 0.0
    state["screen"] = "crate_reveal"

    if rarity in ("epic", "legendary", "ultra", "mythic", "god"):
        play_sound("success")
    elif is_duplicate:
        play_sound("coin_down")
    else:
        play_sound("coin_up")

    announce_crate_drop(crate_id, item_id, rarity, is_duplicate, refund)
    return True, msg


def open_shop():
    ensure_daily_shop()
    state["shop_return"] = state.get("screen", "welcome")
    state["screen"] = "shop"
    state["shop_tab"] = state.get("shop_tab", "daily")
    state["avatar_name_input"] = get_avatar_name()
    state["shop_avatar_input_active"] = False
    set_shop_message((
        f"Hey, I'm {get_avatar_name()}! "
        f"You have {get_wallet()} CR in your saved wallet."
    ))


# =============================================================================
# SOUND
# =============================================================================
SOUNDS = {}
def _make_sound(buffer, volume=0.6):
    try:
        snd = pygame.mixer.Sound(buffer=buffer)
        snd.set_volume(volume)
        return snd
    except Exception:
        return None


def generate_tone(freq, duration, wave="sine", volume=0.5, attack=0.01, decay=0.18):
    n = max(1, int(22050 * duration))
    if HAS_NUMPY:
        t = np.linspace(0, duration, n, endpoint=False)
        if wave == "sine":
            w = np.sin(2 * np.pi * freq * t)
        elif wave == "square":
            w = np.sign(np.sin(2 * np.pi * freq * t))
        elif wave == "saw":
            w = 2 * (t * freq - np.floor(t * freq + 0.5))
        else:
            w = np.sin(2 * np.pi * freq * t)
        env = np.ones(n, dtype=np.float32)
        a = max(1, int(attack * 22050))
        d = max(1, int(decay * 22050))
        if a < n:
            env[:a] = np.linspace(0.0, 1.0, a)
        if d < n:
            env[-d:] = np.linspace(1.0, 0.02, d)
        w = w * env
        return (w * volume * 32767).astype(np.int16)
    import array
    buf = array.array("h")
    for i in range(n):
        tt = i / 22050
        val = math.sin(2 * math.pi * freq * tt)
        val *= max(0.02, 1.0 - (tt / max(duration, 0.001)) * 0.98)
        buf.append(int(val * volume * 32767))
    return buf


def init_sounds():
    global SOUNDS
    SOUNDS.clear()
    SOUNDS["click"] = _make_sound(generate_tone(920, 0.04, "square", 0.35), 0.4)
    SOUNDS["key"] = _make_sound(generate_tone(1100, 0.025, "sine", 0.2), 0.25)
    SOUNDS["success"] = _make_sound(generate_tone(620, 0.6, "sine", 0.4), 0.45)
    SOUNDS["ping"] = _make_sound(generate_tone(780, 0.18, "sine", 0.3), 0.35)
    SOUNDS["boot"] = _make_sound(generate_tone(440, 0.35, "square", 0.5), 0.5)
    SOUNDS["back"] = _make_sound(generate_tone(280, 0.12, "saw", 0.25), 0.3)
    SOUNDS["coin_up"] = _make_sound(generate_tone(880, 0.15, "sine", 0.35), 0.4)
    SOUNDS["coin_down"] = _make_sound(generate_tone(220, 0.2, "saw", 0.3), 0.35)


def play_sound(name):
    if get_settings().get("muted"):
        return
    snd = SOUNDS.get(name)
    if snd:
        try:
            snd.play()
        except Exception:
            pass


# =============================================================================
# DRAWING HELPERS
# =============================================================================
def wrap_text(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_rounded_rect(surf, rect, color, radius=8, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border > 0 and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)


def draw_text(surf, text, font, color, x, y, center=False):
    img = font.render(text, True, color)
    if center:
        surf.blit(img, img.get_rect(center=(x, y)))
    else:
        surf.blit(img, (x, y))


# =============================================================================
# SCORING FUNCTIONS (from the text version — teaches if/else)
# =============================================================================
def score_answer(answer, bonus_keywords):
    """Score one answer: 0–3 points based on length and keywords."""
    points = 0
    lower_answer = answer.lower()

    if len(answer) >= MIN_ANSWER_LENGTH:
        points += 1
    if len(answer.split()) >= 4:
        points += 1
    for keyword in bonus_keywords:
        if keyword in lower_answer:
            points += 1
            break
    return min(points, 3)


def calculate_design_score(answers_list):
    """
    Score the full design using if/else tiers.

    Returns: total_score, max_score, rating, message
    """
    total_score = 0
    max_score = len(DESIGN_QUESTIONS) * 3

    for entry in answers_list:
        keywords = []
        for q in DESIGN_QUESTIONS:
            if q["id"] == entry["key"]:
                keywords = q["keywords"]
                break
        total_score += score_answer(entry["answer"], keywords)

    if total_score >= max_score * 0.85:
        rating = "Outstanding Inventor"
        message = (
            "Your assistant is brilliantly designed! Grace Hopper would be proud. "
            "You thought about purpose, personality, skills, and safety."
        )
    elif total_score >= max_score * 0.65:
        rating = "Rising Programmer"
        message = (
            "Solid design! Your assistant has a clear identity and useful features. "
            "A few more details could make it world-class."
        )
    elif total_score >= max_score * 0.40:
        rating = "Curious Coder"
        message = (
            "Good start! You have the basics down. Next time, try longer, "
            "more specific answers for each question."
        )
    else:
        rating = "Lab Apprentice"
        message = (
            "Every great inventor starts somewhere! Design another assistant "
            "and add more detail to each answer."
        )

    return total_score, max_score, rating, message


def get_question_keywords(q_id):
    for q in DESIGN_QUESTIONS:
        if q["id"] == q_id:
            return q["keywords"]
    return []


def evaluate_answer_quality(q_id, answer):
    """Return quality points (0–3) and a short reason for the credit mentor."""
    points = score_answer(answer, get_question_keywords(q_id))
    category = QUESTION_CATEGORY.get(q_id, "works")
    cat_label = CATEGORY_INFO[category]["label"]

    if points >= 3:
        reason = f"Great {cat_label.lower()} choice — detailed and thoughtful!"
    elif points == 2:
        reason = f"Solid {cat_label.lower()} answer — add a bit more detail next time."
    elif points == 1:
        reason = f"Okay start for {cat_label.lower()}, but pretty vague."
    else:
        reason = f"Weak {cat_label.lower()} answer — investors aren't impressed."

    return points, reason


def credit_delta_for_answer(q_id, answer):
    """Convert answer quality into lab credits gained or lost."""
    points, reason = evaluate_answer_quality(q_id, answer)
    base = CREDIT_BY_POINTS.get(points, -10)
    category = QUESTION_CATEGORY.get(q_id, "works")

    # "What it does" answers are worth slightly more — purpose matters most
    if category == "does":
        base = int(base * 1.25)
    elif category == "looks" and points == 0:
        base = -12  # a bland look hurts market appeal extra

    return base, points, reason


def calculate_category_scores(answers_dict):
    """
    Score the three design pillars (each 0–100).

    looks  = name + personality
    does   = purpose + skills
    works  = memory + voice + safety
    """
    totals = {"looks": 0, "does": 0, "works": 0}
    counts = {"looks": 0, "does": 0, "works": 0}

    for q in DESIGN_QUESTIONS:
        answer = answers_dict.get(q["id"], "")
        if not answer:
            continue
        cat = QUESTION_CATEGORY[q["id"]]
        pts = score_answer(answer, q["keywords"])
        totals[cat] += pts
        counts[cat] += 3  # max per question

    scores = {}
    for cat in ("looks", "does", "works"):
        if counts[cat] > 0:
            scores[cat] = int(100 * totals[cat] / counts[cat])
        else:
            scores[cat] = 0
    return scores


def calculate_synergy_bonus(category_scores):
    """
    Reward balanced builds; penalize lopsided or broken designs.

    if/else teaches that a pretty assistant that does nothing still fails!
    """
    looks, does, works = category_scores["looks"], category_scores["does"], category_scores["works"]
    avg = (looks + does + works) / 3
    lowest = min(looks, does, works)

    if looks >= 70 and does >= 70 and works >= 70:
        return 25, "Synergy bonus! Your build looks great, works well, AND does useful things."
    if lowest < 30:
        return -20, "Penalty: one area is too weak — a broken build costs lab credits."
    if does < 40:
        return -15, "Penalty: investors ask 'but what does it DO?' — purpose was too vague."
    if works < 40:
        return -12, "Penalty: it looks fine but doesn't work safely or reliably."
    if looks < 35:
        return -8, "Penalty: personality and branding need more polish."
    if avg >= 55:
        return 10, "Balanced build bonus — all three pillars are decent."
    return 0, ""


def get_avatar_mood(credits, last_delta=0):
    """Pick mentor expression from credit balance and latest change."""
    if last_delta >= 10:
        return "excited"
    if last_delta <= -8:
        return "worried"
    if credits >= STARTING_CREDITS + 40:
        return "proud"
    if credits >= STARTING_CREDITS:
        return "happy"
    if credits >= STARTING_CREDITS - 25:
        return "neutral"
    return "disappointed"


def apply_credit_change(delta, reason, q_id=""):
    """Update credits, log the transaction, and set mentor feedback."""
    state["credits"] = max(0, state["credits"] + delta)
    state["credit_log"].append({
        "q_id": q_id,
        "delta": delta,
        "reason": reason,
        "category": QUESTION_CATEGORY.get(q_id, ""),
    })
    state["avatar_mood"] = get_avatar_mood(state["credits"], delta)
    set_avatar_message(reason)
    state["last_credit_delta"] = delta
    state["credit_flash"] = 1.2  # seconds to flash +/- on HUD
    if delta > 0:
        play_sound("coin_up")
    elif delta < 0:
        play_sound("coin_down")


def build_answers_list(answers_dict):
    """Convert the answers dict into a list for scoring and summary."""
    result = []
    for q in DESIGN_QUESTIONS:
        result.append({
            "key": q["id"],
            "question": q["text"],
            "answer": answers_dict.get(q["id"], ""),
        })
    tag_labels = get_display_tags(answers_dict)
    if tag_labels:
        result.append({
            "key": "tags",
            "question": "Assistant Tags",
            "answer": ", ".join(tag_labels),
        })
    return result


def get_preset_tag(tag_id):
    for tag in PRESET_TAGS:
        if tag["id"] == tag_id:
            return tag
    return None


def get_total_tag_count():
    return len(state.get("selected_tags", [])) + len(state.get("custom_tags", []))


def get_display_tags(answers=None):
    """All tag labels for preview, summary, and save."""
    if answers is None:
        preset_ids = state.get("selected_tags", [])
        custom = state.get("custom_tags", [])
    else:
        preset_ids = answers.get("preset_tags", [])
        custom = answers.get("custom_tags", [])
    labels = []
    for tid in preset_ids:
        tag = get_preset_tag(tid)
        if tag:
            labels.append(tag["label"])
    labels.extend(custom)
    return labels[:MAX_TAGS_TOTAL]


def sync_tags_to_answers():
    """Store chosen tags on the answers dict before scoring."""
    state["answers"]["preset_tags"] = list(state.get("selected_tags", []))
    state["answers"]["custom_tags"] = list(state.get("custom_tags", []))
    state["answers"]["tags"] = ", ".join(get_display_tags())


def add_tag_to_library(tag):
    """Remember a clean custom tag for future builds."""
    lib = save_data.setdefault("custom_tag_library", [])
    key = tag.strip().lower()
    if not key:
        return
    lib[:] = [t for t in lib if t.lower() != key]
    lib.insert(0, tag.strip()[:20])
    save_data["custom_tag_library"] = lib[:MAX_TAG_LIBRARY]
    write_save()


def can_afford_custom_tag():
    """Whether the player has enough lab credits for one custom tag."""
    return state.get("credits", STARTING_CREDITS) >= CUSTOM_TAG_COST


def charge_for_custom_tag(tag_name):
    """Deduct credits for adding a custom tag. Preset tags never call this."""
    if not can_afford_custom_tag():
        set_avatar_message((
            f"Custom tags cost {CUSTOM_TAG_COST} CR each — earn more credits or use free presets!"
        ))
        play_sound("coin_down")
        return False
    short = tag_name[:20]
    apply_credit_change(
        -CUSTOM_TAG_COST,
        f"Custom tag '{short}' — {CUSTOM_TAG_COST} CR",
        "custom_tag",
    )
    return True


def toggle_preset_tag(tag_id):
    """Click a preset tag chip on/off — presets are always free."""
    selected = state.setdefault("selected_tags", [])
    if tag_id in selected:
        selected.remove(tag_id)
        play_sound("back")
    elif get_total_tag_count() < MAX_TAGS_TOTAL:
        selected.append(tag_id)
        tag = get_preset_tag(tag_id)
        label = tag["label"] if tag else "tag"
        set_avatar_message(f"Added '{label}' — preset tags are free!")
        play_sound("click")
    else:
        set_avatar_message(f"Max {MAX_TAGS_TOTAL} tags per assistant!")
        play_sound("coin_down")
    persist_session()


def add_custom_tag_from_input():
    """Add a typed custom tag — runs through the friendly filter."""
    val = state.get("tag_input", "").strip()
    ok, err = validate_tag(val)
    if not ok:
        state["filter_message"] = err or FILTER_TAG_QUIP
        state["filter_flash"] = 2.5
        set_avatar_message(err or FILTER_TAG_QUIP)
        play_sound("coin_down")
        return
    if get_total_tag_count() >= MAX_TAGS_TOTAL:
        set_avatar_message(f"Max {MAX_TAGS_TOTAL} tags per assistant!")
        play_sound("coin_down")
        return
    custom = state.setdefault("custom_tags", [])
    if len(custom) >= MAX_CUSTOM_TAGS:
        set_avatar_message(f"Max {MAX_CUSTOM_TAGS} custom tags — use presets for the rest!")
        play_sound("coin_down")
        return
    if any(c.lower() == val.lower() for c in custom):
        set_avatar_message("You already added that tag!")
        return
    if not charge_for_custom_tag(val):
        return
    custom.append(val[:20])
    state["tag_input"] = ""
    add_tag_to_library(val)
    persist_session()


def add_library_tag(label):
    """Reuse a saved custom tag from a previous build."""
    ok, err = validate_tag(label)
    if not ok:
        state["filter_message"] = err or FILTER_TAG_QUIP
        state["filter_flash"] = 2.5
        play_sound("coin_down")
        return
    if get_total_tag_count() >= MAX_TAGS_TOTAL:
        set_avatar_message(f"Max {MAX_TAGS_TOTAL} tags!")
        return
    custom = state.setdefault("custom_tags", [])
    if len(custom) >= MAX_CUSTOM_TAGS:
        set_avatar_message(f"Max {MAX_CUSTOM_TAGS} custom tags!")
        play_sound("coin_down")
        return
    if any(c.lower() == label.lower() for c in custom):
        return
    if not charge_for_custom_tag(label):
        return
    custom.append(label[:20])
    persist_session()


def remove_custom_tag(label):
    custom = state.get("custom_tags", [])
    state["custom_tags"] = [c for c in custom if c != label]
    persist_session()
    play_sound("back")


# =============================================================================
# LIVE ASSISTANT PREVIEW
# =============================================================================
particles = []
_PARTICLE_COLOR_DEFAULT = (120, 220, 255)


def _normalize_rgb(color, fallback=_PARTICLE_COLOR_DEFAULT):
    """Always return a pygame-safe (R, G, B) tuple of ints in 0–255."""
    fb = tuple(max(0, min(255, int(c))) for c in fallback[:3])
    if not isinstance(color, (tuple, list)):
        return fb
    out = []
    for i in range(3):
        try:
            out.append(max(0, min(255, int(float(color[i])))))
        except (TypeError, ValueError, IndexError):
            out.append(fb[i])
    return tuple(out)


def spawn_particles(cx, cy, count=12, color=(120, 220, 255)):
    rgb = _normalize_rgb(color)
    for _ in range(count):
        life = random.uniform(0.5, 1.2)
        particles.append({
            "x": cx + random.uniform(-20, 20),
            "y": cy + random.uniform(-10, 10),
            "vx": random.uniform(-2.5, 2.5),
            "vy": random.uniform(-3.5, -1.0),
            "life": life,
            "maxlife": life,
            "color": rgb,
            "size": random.randint(2, 4),
        })


def update_particles(dt):
    global particles
    alive = []
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.1
        p["life"] -= dt
        if p["life"] > 0.02:
            alive.append(p)
    particles = alive


def draw_particles(surf):
    for p in particles:
        try:
            maxlife = max(float(p.get("maxlife", 1.0)), 0.001)
            life = float(p.get("life", 0.0))
            alpha = max(0.0, min(1.0, life / maxlife))
            base = _normalize_rgb(p.get("color"))
            col = tuple(max(0, min(255, int(ch * alpha))) for ch in base)
            if len(col) != 3:
                continue
            x = float(p.get("x", 0.0))
            y = float(p.get("y", 0.0))
            if not (math.isfinite(x) and math.isfinite(y)):
                continue
            radius = max(1, int(float(p.get("size", 2)) * alpha))
            pygame.draw.circle(surf, col, (int(x), int(y)), radius)
        except (ValueError, TypeError, OverflowError):
            continue


def draw_assistant_preview(surf, x, y, w, h, answers, t, booted=False):
    """Draw a cute robot assistant that updates live with design choices."""
    draw_rounded_rect(surf, pygame.Rect(x, y, w, h), PREVIEW_BG, radius=14, border=3, border_color=PREVIEW_BORDER)
    draw_rounded_rect(surf, pygame.Rect(x + 4, y + 4, w - 8, 20), (12, 18, 32), radius=6)
    draw_text(surf, "LIVE PREVIEW", small_font, ACCENT, x + w // 2, y + 8, center=True)

    cx = x + w // 2
    cy = y + h // 2 + 10

    name = answers.get("name", "Assistant") or "Assistant"
    personality = (answers.get("personality", "") or "").lower()
    skills = (answers.get("skills", "") or "").lower()
    voice = (answers.get("voice", "") or "").lower()
    memory = (answers.get("memory", "") or "").lower()
    safety = (answers.get("safety", "") or "").lower()

    # Shadow
    pygame.draw.ellipse(surf, (8, 12, 22), (cx - 55, cy + 58, 110, 24))

    # Body — color shifts with personality keywords
    if "calm" in personality:
        body_col = (90, 160, 220)
    elif "witty" in personality or "cheerful" in personality:
        body_col = (255, 170, 90)
    elif "friendly" in personality or "kind" in personality:
        body_col = (100, 210, 160)
    else:
        body_col = (110, 140, 200)

    body_rect = pygame.Rect(cx - 60, cy - 20, 120, 100)
    draw_rounded_rect(surf, body_rect, body_col, radius=16, border=3, border_color=(40, 50, 70))

    # Screen / face
    screen_rect = pygame.Rect(cx - 44, cy - 8, 88, 52)
    draw_rounded_rect(surf, screen_rect, (18, 24, 38), radius=8, border=2, border_color=(80, 110, 150))

    # Eyes — blink animation
    blink = (math.sin(t * 3.2) > 0.15)
    eye_col = GLOW if booted else (140, 200, 255)
    for ex in (cx - 18, cx + 18):
        if blink:
            pygame.draw.circle(surf, eye_col, (ex, cy + 10), 7)
            pygame.draw.circle(surf, (15, 20, 35), (ex, cy + 10), 3)
        else:
            pygame.draw.line(surf, eye_col, (ex - 6, cy + 10), (ex + 6, cy + 10), 3)

    # Smile or neutral based on personality
    if "friendly" in personality or "cheerful" in personality:
        pygame.draw.arc(surf, ACCENT2, (cx - 14, cy + 18, 28, 14), 0.2, math.pi - 0.2, 2)
    else:
        pygame.draw.line(surf, ACCENT, (cx - 10, cy + 28), (cx + 10, cy + 28), 2)

    # Antenna — pulses when assistant has memory
    ax, ay = cx, cy - 38
    pygame.draw.line(surf, (130, 150, 180), (ax, ay + 6), (ax, ay - 16), 3)
    if "remember" in memory or "name" in memory or "preferences" in memory:
        pulse = 0.6 + 0.4 * math.sin(t * 5.0)
        r = int(6 + pulse * 4)
        pygame.draw.circle(surf, (120, 230, 255), (ax, ay - 20), r)
        pygame.draw.circle(surf, WHITE, (ax, ay - 20), max(2, r - 3))

    # Speaker / mic for voice communication
    if "voice" in voice or "speak" in voice or "both" in voice:
        mic_x = cx - 72
        pygame.draw.circle(surf, (70, 85, 110), (mic_x, cy + 20), 10, 2)
        pygame.draw.line(surf, ACCENT, (mic_x, cy + 30), (mic_x, cy + 42), 2)
        # Sound waves
        wave = int(3 * math.sin(t * 8))
        pygame.draw.arc(surf, ACCENT, (mic_x - 14 - wave, cy + 8, 28 + wave, 28), -0.8, 0.8, 2)

    # Chat bubble for text communication
    if "text" in voice or "chat" in voice or "both" in voice:
        bx, by = cx + 58, cy - 30
        pygame.draw.ellipse(surf, (50, 60, 90), (bx, by - 12, 70, 28))
        pygame.draw.ellipse(surf, ACCENT, (bx, by - 12, 70, 28), 2)
        draw_text(surf, "Hi!", small_font, TEXT, bx + 35, by + 2, center=True)

    # Skill icons as little badges
    badge_y = cy + 48
    skill_icons = []
    if "code" in skills or "math" in skills or "calculate" in skills:
        skill_icons.append(("</>", ACCENT))
    if "translate" in skills:
        skill_icons.append(("Aa", ACCENT3))
    if "joke" in skills or "music" in skills:
        skill_icons.append(("♪", ACCENT2))
    if "weather" in skills or "search" in skills:
        skill_icons.append(("?", GOOD))

    for i, (icon, col) in enumerate(skill_icons[:4]):
        bx = cx - 36 + i * 24
        pygame.draw.circle(surf, (30, 38, 58), (bx, badge_y), 10)
        draw_text(surf, icon, small_font, col, bx, badge_y, center=True)

    # Safety shield
    if "safe" in safety or "privacy" in safety or "kind" in safety:
        shield = [(cx, cy - 55), (cx - 12, cy - 42), (cx - 12, cy - 30), (cx, cy - 22),
                  (cx + 12, cy - 30), (cx + 12, cy - 42)]
        pygame.draw.polygon(surf, (60, 180, 120), shield)
        pygame.draw.polygon(surf, GOOD, shield, 2)
        draw_text(surf, "✓", small_font, WHITE, cx, cy - 36, center=True)

    # Name plate
    plate_w = min(150, max(80, len(name) * 8 + 20))
    plate = pygame.Rect(cx - plate_w // 2, cy + 62, plate_w, 22)
    draw_rounded_rect(surf, plate, (35, 42, 62), radius=5, border=1, border_color=ACCENT)
    short_name = name[:16] + ("..." if len(name) > 16 else "")
    draw_text(surf, short_name, small_font, TEXT, cx, cy + 73, center=True)

    tag_labels = get_display_tags(answers)
    if tag_labels:
        tx = x + 8
        ty = y + h - 28
        for i, label in enumerate(tag_labels[:4]):
            chip_w = min(72, small_font.size(label[:10])[0] + 14)
            chip = pygame.Rect(tx, ty, chip_w, 18)
            draw_rounded_rect(surf, chip, (40, 50, 75), radius=4, border=1, border_color=ACCENT2)
            draw_text(surf, label[:10], small_font, ACCENT2, chip.centerx, chip.centery, center=True)
            tx += chip_w + 4
            if tx > x + w - 40:
                break

    # Boot glow ring
    if booted:
        glow_r = 72 + int(4 * math.sin(t * 4))
        pygame.draw.circle(surf, (255, 255, 200), (cx, cy + 15), glow_r, 2)


# =============================================================================
# CREDIT MENTOR AVATAR — Grace Hopper-inspired lab investor
# =============================================================================
def _cosmetic(item_id):
    return COSMETIC_CATALOG.get(item_id, {})


def draw_mentor_avatar(surf, x, y, size, mood, credits, t, message="", show_bubble=True, equipped=None, avatar_name=None):
    """
    Draw the credit mentor who awards or deducts lab credits.

    mood: excited, proud, happy, neutral, worried, disappointed
    equipped: dict of slot -> cosmetic id (from saved wallet shop)
    """
    if equipped is None:
        equipped = get_equipped()

    cx = x + size // 2
    head_r = size // 3

    # Optional glow aura cosmetic (drawn behind everything)
    aura_id = equipped.get("aura")
    if aura_id:
        ac = _cosmetic(aura_id).get("aura_color", (120, 200, 255))
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        glow_r = int(head_r + 18 + pulse * 8)
        glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*ac, int(55 + 40 * pulse)), (glow_r + 2, glow_r + 2), glow_r)
        surf.blit(glow_surf, (cx - glow_r - 2, y + head_r - glow_r))

    # Lab coat / shoulders — coat cosmetic overrides color
    coat_id = equipped.get("coat")
    coat_col = _cosmetic(coat_id).get("coat_color", (240, 242, 250)) if coat_id else (240, 242, 250)
    coat = pygame.Rect(cx - head_r - 8, y + head_r + 10, (head_r + 8) * 2, size // 2 + 10)
    draw_rounded_rect(surf, coat, coat_col, radius=10, border=2, border_color=(180, 190, 210))

    # Collar + tie — tie cosmetic overrides color
    tie_id = equipped.get("tie")
    tie_col = _cosmetic(tie_id).get("tie_color", (50, 70, 130)) if tie_id else (50, 70, 130)
    pygame.draw.polygon(surf, tie_col, [
        (cx - 12, y + head_r + 14), (cx + 12, y + head_r + 14), (cx, y + head_r + 32)
    ])

    # Badge cosmetic on coat
    badge_id = equipped.get("badge")
    if badge_id:
        bc = _cosmetic(badge_id).get("badge_color", ACCENT)
        pygame.draw.circle(surf, bc, (cx + head_r - 4, y + head_r + 28), 9)
        pygame.draw.circle(surf, WHITE, (cx + head_r - 4, y + head_r + 28), 9, 2)
        draw_text(surf, "★", small_font, WHITE, cx + head_r - 4, y + head_r + 28, center=True)

    # Head
    pygame.draw.circle(surf, (255, 220, 185), (cx, y + head_r), head_r)
    pygame.draw.circle(surf, (200, 170, 140), (cx, y + head_r), head_r, 2)

    # Hair — hair cosmetic overrides default bun colors
    hair_id = equipped.get("hair")
    hair_main = _cosmetic(hair_id).get("hair_color", (90, 60, 40)) if hair_id else (90, 60, 40)
    hair_shadow = tuple(max(0, c - 25) for c in hair_main)
    pygame.draw.circle(surf, hair_main, (cx, y + head_r - head_r // 2), head_r // 2 + 4)
    pygame.draw.circle(surf, hair_shadow, (cx + head_r // 3, y + head_r - 4), head_r // 3)

    # Hat cosmetic
    hat_id = equipped.get("hat")
    if hat_id:
        hc = _cosmetic(hat_id).get("hat_color", ACCENT3)
        hat_y = y + head_r - head_r - 6
        if hat_id == "hat_crown":
            pygame.draw.polygon(surf, hc, [
                (cx - 20, hat_y + 8), (cx - 12, hat_y - 8), (cx - 4, hat_y + 4),
                (cx + 4, hat_y - 12), (cx + 12, hat_y + 4), (cx + 20, hat_y + 8),
            ])
            pygame.draw.polygon(surf, (200, 160, 40), [
                (cx - 20, hat_y + 8), (cx - 12, hat_y - 8), (cx - 4, hat_y + 4),
                (cx + 4, hat_y - 12), (cx + 12, hat_y + 4), (cx + 20, hat_y + 8),
            ], 2)
        else:
            pygame.draw.ellipse(surf, hc, (cx - 22, hat_y, 44, 18))
            pygame.draw.rect(surf, hc, (cx - 14, hat_y - 10, 28, 14), border_radius=4)

    # Glasses — cosmetic can recolor frames
    glasses_id = equipped.get("glasses")
    frame_col = _cosmetic(glasses_id).get("frame_color", (60, 70, 90)) if glasses_id else (60, 70, 90)
    for gx in (cx - 16, cx + 16):
        pygame.draw.circle(surf, frame_col, (gx, y + head_r + 2), 11, 2)
        if glasses_id in ("glasses_star", "glasses_holo"):
            sym = "★" if glasses_id == "glasses_star" else "◇"
            draw_text(surf, sym, small_font, frame_col, gx, y + head_r + 2, center=True)
        else:
            pygame.draw.circle(surf, (30, 40, 55), (gx, y + head_r + 2), 4)
    pygame.draw.line(surf, frame_col, (cx - 5, y + head_r + 2), (cx + 5, y + head_r + 2), 2)

    # Eyes + expression by mood
    eye_y = y + head_r + 2
    if mood in ("excited", "proud", "happy"):
        for ex in (cx - 16, cx + 16):
            pygame.draw.circle(surf, (30, 40, 55), (ex, eye_y), 3)
        smile_y = y + head_r + 16
        pygame.draw.arc(surf, (180, 90, 90), (cx - 14, smile_y - 6, 28, 14), 0.2, math.pi - 0.2, 2)
    elif mood == "worried":
        for ex in (cx - 16, cx + 16):
            pygame.draw.circle(surf, (30, 40, 55), (ex, eye_y + 2), 3)
        pygame.draw.arc(surf, (180, 90, 90), (cx - 12, y + head_r + 20, 24, 10), math.pi + 0.3, -0.3, 2)
    elif mood == "disappointed":
        for ex in (cx - 16, cx + 16):
            pygame.draw.line(surf, (30, 40, 55), (ex - 4, eye_y), (ex + 4, eye_y), 2)
        pygame.draw.line(surf, (180, 90, 90), (cx - 8, y + head_r + 20), (cx + 8, y + head_r + 20), 2)
    else:
        for ex in (cx - 16, cx + 16):
            pygame.draw.circle(surf, (30, 40, 55), (ex, eye_y), 3)
        pygame.draw.line(surf, (180, 90, 90), (cx - 8, y + head_r + 18), (cx + 8, y + head_r + 18), 2)

    # Floating credit coin badge
    bob = int(3 * math.sin(t * 3.5))
    coin_x, coin_y = cx + head_r + 6, y + 8 + bob
    pygame.draw.circle(surf, ACCENT3, (coin_x, coin_y), 14)
    pygame.draw.circle(surf, (200, 150, 50), (coin_x, coin_y), 14, 2)
    draw_text(surf, "C", small_font, (80, 50, 10), coin_x, coin_y, center=True)

    # Avatar name plate + credit count
    av_name = avatar_name if avatar_name is not None else get_avatar_name()
    plate_w = min(130, max(70, len(av_name) * 7 + 16))
    name_plate = pygame.Rect(cx - plate_w // 2, y + size - 28, plate_w, 18)
    draw_rounded_rect(surf, name_plate, (35, 42, 62), radius=4, border=1, border_color=ACCENT2)
    short_av = av_name[:14] + ("..." if len(av_name) > 14 else "")
    draw_text(surf, short_av, small_font, ACCENT2, cx, y + size - 19, center=True)

    cred_col = GOOD if credits >= STARTING_CREDITS else ACCENT3 if credits >= STARTING_CREDITS - 20 else BAD
    draw_text(surf, f"{credits} CR", small_font, cred_col, cx, y + size - 6, center=True)

    # Speech bubble with mentor feedback (compact — max 2 short lines)
    if show_bubble and message:
        bubble_w = min(190, max(100, len(message) * 4 + 24))
        lines = wrap_text(message, small_font, bubble_w - 12)[:2]
        bubble_h = 14 + len(lines) * 14
        bubble = pygame.Rect(cx - bubble_w // 2, y - bubble_h - 10, bubble_w, bubble_h)
        draw_rounded_rect(surf, bubble, (35, 42, 65), radius=6, border=2, border_color=ACCENT3)
        pygame.draw.polygon(surf, (35, 42, 65), [
            (cx - 5, y - 8), (cx + 5, y - 8), (cx, y - 3)
        ])
        by = bubble.y + 8
        for ln in lines:
            draw_text(surf, ln, small_font, TEXT, cx, by, center=True)
            by += 14


def draw_category_meters(surf, x, y, category_scores):
    """Three compact bars showing Looks / Does / Works quality during design."""
    draw_text(surf, "BUILD QUALITY", small_font, TEXT_MUTED, x, y)
    my = y + 14
    for cat in ("looks", "does", "works"):
        info = CATEGORY_INFO[cat]
        score = category_scores.get(cat, 0)
        draw_text(surf, info["icon"], small_font, info["color"], x, my + 2)
        draw_text(surf, info["label"][:10], small_font, TEXT_MUTED, x + 16, my + 2)
        bar = pygame.Rect(x + 108, my, 88, 8)
        pygame.draw.rect(surf, (30, 38, 55), bar, border_radius=4)
        fill = int(88 * score / 100)
        if fill > 0:
            bar_col = GOOD if score >= 65 else ACCENT3 if score >= 40 else BAD
            pygame.draw.rect(surf, bar_col, (bar.x, bar.y, fill, 8), border_radius=4)
        draw_text(surf, f"{score}%", small_font, info["color"], x + 204, my + 2)
        my += 18


def draw_credits_panel(surf, x, y, w, h, credit_data):
    """Compact credit breakdown on the summary screen."""
    draw_rounded_rect(surf, pygame.Rect(x, y, w, h), PANEL_BG, radius=10, border=2, border_color=ACCENT3)
    draw_text(surf, "LAB CREDITS", header_font, ACCENT3, x + w // 2, y + 14, center=True)

    credits = credit_data["final_credits"]
    net = credit_data["net_change"]
    net_sign = "+" if net >= 0 else ""
    if credits >= STARTING_CREDITS:
        cred_col = GOOD
    elif credits >= 25:
        cred_col = ACCENT3
    else:
        cred_col = BAD
    draw_text(surf, f"{credits} CR ({net_sign}{net})", question_font, cred_col,
              x + w // 2, y + 36, center=True)

    scores = credit_data["category_scores"]
    draw_category_meters(surf, x + 10, y + 52, scores)

    draw_text(surf, "Log:", small_font, ACCENT2, x + 10, y + 118)
    ly = y + 134
    for entry in credit_data.get("log", [])[-4:]:
        sign = "+" if entry["delta"] >= 0 else ""
        col = GOOD if entry["delta"] > 0 else BAD if entry["delta"] < 0 else TEXT_MUTED
        label = LABELS.get(entry["q_id"], entry["q_id"])[:10]
        draw_text(surf, f"{sign}{entry['delta']} {label}", small_font, col, x + 10, ly)
        ly += 14

    synergy = credit_data.get("synergy_bonus", 0)
    if synergy != 0:
        sign = "+" if synergy > 0 else ""
        col = GOOD if synergy > 0 else BAD
        draw_text(surf, f"{sign}{synergy} synergy", small_font, col, x + 10, ly)

    mood = get_avatar_mood(credits)
    mentor_msg = credit_data.get("mentor_closing", "")
    draw_mentor_avatar(surf, x + w - 72, y + h - 88, 68, mood, credits, pygame.time.get_ticks() / 1000.0,
                       message=mentor_msg, show_bubble=True, equipped=get_equipped())


def draw_rarity_badge(surf, x, y, rarity, center=False):
    """Small colored rarity label."""
    info = rarity_info(rarity)
    label = info["label"]
    col = info["color"]
    tw = small_font.size(label)[0] + 14
    rect = pygame.Rect(x - tw // 2 if center else x, y - 8, tw, 18)
    draw_rounded_rect(surf, rect, tuple(max(0, c - 80) for c in col), radius=4, border=1, border_color=col)
    draw_text(surf, label, small_font, col, rect.centerx, rect.centery, center=True)


def draw_crate_box(surf, x, y, size, crate_id, t, shake=0):
    """Animated loot crate icon."""
    crate = CRATE_TYPES[crate_id]
    col = crate["color"]
    sx = x + int(shake * math.sin(t * 20))
    rect = pygame.Rect(sx, y, size, size - 10)
    draw_rounded_rect(surf, rect, tuple(max(0, c - 60) for c in col), radius=10, border=3, border_color=col)
    # Lid
    lid = pygame.Rect(sx + 6, y - 8 + int(3 * math.sin(t * 4)), size - 12, 18)
    draw_rounded_rect(surf, lid, col, radius=6, border=2, border_color=WHITE)
    draw_text(surf, "?", header_font, WHITE, sx + size // 2, y + size // 2 - 2, center=True)


def draw_crate_rarity_bars(surf, x, y, w, crate_id):
    """Visual rarity % bars — full labels with exact chances."""
    draw_text(surf, "Rarity chances:", small_font, TEXT_MUTED, x, y)
    bar_y = y + 16
    max_bar_w = w - 110
    for rarity, percent in CRATE_TYPES[crate_id]["odds"]:
        if percent <= 0:
            continue
        info = rarity_info(rarity)
        draw_text(surf, info["label"][:8], small_font, info["color"], x, bar_y + 3)
        bar = pygame.Rect(x + 72, bar_y, max_bar_w, 10)
        pygame.draw.rect(surf, (30, 38, 55), bar, border_radius=4)
        fill_w = max(2, int(max_bar_w * percent / 100))
        pygame.draw.rect(surf, info["color"], (bar.x, bar.y, fill_w, 10), border_radius=4)
        draw_text(surf, f"{percent}%", small_font, info["color"], x + 72 + max_bar_w + 8, bar_y + 3)
        bar_y += 16


def draw_crate_drop_table(surf, x, y, w, h, crate_id, scroll):
    """Scrollable list of every cosmetic and its exact % chance."""
    draw_rounded_rect(surf, pygame.Rect(x, y, w, h), (16, 22, 38), radius=8, border=2, border_color=PANEL_BORDER)
    crate_name = CRATE_TYPES[crate_id]["name"]
    draw_text(surf, f"DROP CHANCES — {crate_name}", small_font, ACCENT3, x + 10, y + 6)
    draw_crate_rarity_bars(surf, x + 8, y + 22, w - 16, crate_id)

    clip = pygame.Rect(x + 6, y + 98, w - 12, h - 108)
    surf.set_clip(clip)
    rows = get_crate_drop_table(crate_id)
    row_y = y + 102 - scroll
    for row in rows:
        if row_y > y + h - 10:
            break
        if row_y >= y + 96:
            rcol = rarity_info(row["rarity"])["color"]
            owned = row["id"] in get_owned()
            name = row["name"][:22]
            pct_text = format_drop_pct(row["pct"])
            draw_text(surf, pct_text, small_font, rcol, x + 12, row_y)
            draw_text(surf, name, small_font, GOOD if owned else TEXT, x + 58, row_y)
            draw_text(surf, rarity_info(row["rarity"])["label"][:9], small_font, TEXT_MUTED, x + w - 100, row_y)
        row_y += 16
    surf.set_clip(None)
    draw_text(surf, "UP/DOWN scroll", small_font, TEXT_MUTED, x + w - 90, y + h - 14)


def draw_shop_daily_tab(surf, wallet, shop_ids, owned, equipped, shop_buttons, panel_x, panel_w):
    """Today's direct-buy stock with rarity badges."""
    cx = panel_x + panel_w // 2
    draw_text(surf, "TODAY'S STOCK", header_font, ACCENT, cx, CONTENT_Y + 34, center=True)
    row_y = CONTENT_Y + 52
    row_h = 54
    for item_id in shop_ids:
        item = COSMETIC_CATALOG[item_id]
        rarity = item.get("rarity", "common")
        rcol = rarity_info(rarity)["color"]
        is_owned = item_id in owned
        is_equipped = equipped.get(item["slot"]) == item_id

        draw_rounded_rect(surf, pygame.Rect(panel_x + 8, row_y, panel_w - 16, row_h), (18, 24, 40), radius=6, border=2,
                          border_color=GOOD if is_equipped else rcol if not is_owned else ACCENT)

        draw_text(surf, item["name"], question_font, TEXT, panel_x + 18, row_y + 6)
        draw_rarity_badge(surf, panel_x + 150, row_y + 12, rarity)
        draw_text(surf, f"{item['slot'][:4]}  {item['price']}CR", small_font, TEXT_MUTED, panel_x + 18, row_y + 28)

        if is_owned:
            def make_equip(iid=item_id):
                return lambda: set_shop_message(toggle_equip(iid)[1])
            shop_buttons.append(Button(panel_x + panel_w - 96, row_y + 12, 80, BTN_SM,
                                       "OFF" if is_equipped else "ON", make_equip(), ACCENT2))
        else:
            def make_buy(iid=item_id):
                def _buy():
                    ok, msg = purchase_cosmetic(iid)
                    set_shop_message(msg)
                    if not ok:
                        play_sound("coin_down")
                return _buy
            btn = Button(panel_x + panel_w - 96, row_y + 12, 80, BTN_SM, "BUY", make_buy(), GOOD)
            btn.enabled = wallet >= item["price"]
            shop_buttons.append(btn)
        row_y += row_h + 6


def draw_shop_crates_tab(surf, wallet, t, shop_buttons, panel_x, panel_w):
    """Crate gacha — rolls saved to disk instantly, with full % odds."""
    cx = panel_x + panel_w // 2
    draw_text(surf, "LOOT CRATES", header_font, ACCENT3, cx, CONTENT_Y + 32, center=True)
    draw_text(surf, f"Opened: {save_data.get('crates_opened', 0)}", small_font, TEXT_MUTED, cx, CONTENT_Y + 50, center=True)

    detail_id = state.get("crate_detail_id", "code_crate")
    cy = CONTENT_Y + 62
    crate_h = 50

    for crate_id, crate in CRATE_TYPES.items():
        selected = crate_id == detail_id
        draw_rounded_rect(surf, pygame.Rect(panel_x + 8, cy, panel_w - 16, crate_h), (18, 24, 40), radius=6, border=2,
                          border_color=crate["color"] if selected else PANEL_BORDER)
        draw_crate_box(surf, panel_x + 14, cy + 6, 36, crate_id, t)
        draw_text(surf, crate["name"], question_font, crate["color"], panel_x + 56, cy + 6)
        draw_text(surf, f"{crate['price']}CR", small_font, ACCENT3, panel_x + panel_w - 90, cy + 6)
        odds_parts = [f"{rarity_info(r)['label'][:3]}{p}" for r, p in crate["odds"] if p > 0]
        draw_text(surf, " ".join(odds_parts), small_font, TEXT_MUTED, panel_x + 56, cy + 28)

        def make_open(cid=crate_id):
            def _open():
                ok, msg = open_crate(cid)
                if not ok:
                    set_shop_message(msg)
                    play_sound("coin_down")
            return _open

        def make_rates(cid=crate_id):
            return lambda: state.update({"crate_detail_id": cid, "crate_drop_scroll": 0})

        shop_buttons.append(Button(panel_x + panel_w - 148, cy + 14, 48, BTN_SM, "%", make_rates(), ACCENT))
        ob = Button(panel_x + panel_w - 94, cy + 14, 80, BTN_SM, "OPEN", make_open(), crate["color"])
        ob.enabled = wallet >= crate["price"]
        shop_buttons.append(ob)
        cy += crate_h + 4

    drop_h = COLLECTION_Y - cy - 8
    if drop_h > 60:
        draw_crate_drop_table(surf, panel_x + 8, cy + 4, panel_w - 16, drop_h, detail_id, state.get("crate_drop_scroll", 0))


def draw_crate_reveal_screen(surf, t):
    """Show last crate result — already saved; click to continue."""
    draw_background(surf, t)
    reveal = state.get("crate_reveal") or save_data.get("last_crate_open") or {}
    if not reveal:
        state["screen"] = "shop"
        return

    state["crate_reveal_anim"] = min(1.0, state.get("crate_reveal_anim", 0) + 0.02)
    anim = state["crate_reveal_anim"]

    item_id = reveal.get("item_id", "")
    rarity = reveal.get("rarity", "common")
    item = COSMETIC_CATALOG.get(item_id, {})
    rinfo = rarity_info(rarity)
    rcol = rinfo["color"]
    is_dup = reveal.get("duplicate", False)

    # Rarity flash background — stronger pulse for top tiers
    tier_pulse = {"god": 1.5, "mythic": 1.3, "ultra": 1.15, "legendary": 1.0, "epic": 0.85}.get(rarity, 0.7)
    pulse = 0.3 + 0.7 * anim * abs(math.sin(t * 6)) * tier_pulse
    flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    flash.fill((*rcol, int(35 * pulse)))
    surf.blit(flash, (0, 0))
    if rarity in ("ultra", "mythic", "god") and anim > 0.3:
        spark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range({"ultra": 5, "mythic": 8, "god": 12}.get(rarity, 6)):
            sx = int((math.sin(t * 3 + i * 1.7) * 0.5 + 0.5) * WIDTH)
            sy = int((math.cos(t * 2.5 + i * 2.1) * 0.5 + 0.5) * HEIGHT)
            pygame.draw.circle(spark, (*rcol, int(40 * anim)), (sx, sy), 4 + i % 3)
        surf.blit(spark, (0, 0))

    draw_text(surf, "CRATE OPENED!", title_font, rcol, WIDTH // 2, CONTENT_Y + 10, center=True)
    draw_rarity_badge(surf, WIDTH // 2, CONTENT_Y + 38, rarity, center=True)

    shake = (1.0 - anim) * 6
    crate_id = reveal.get("crate_id", "code_crate")
    draw_crate_box(surf, WIDTH // 2 - 40, CONTENT_Y + 58, 80, crate_id, t, shake=shake)

    if anim > 0.45:
        card = pygame.Rect(WIDTH // 2 - 220, CONTENT_Y + 160, 440, 200)
        draw_rounded_rect(surf, card, PANEL_BG, radius=12, border=2, border_color=rcol)
        draw_text(surf, item.get("name", "???"), header_font, TEXT, WIDTH // 2, card.y + 28, center=True)
        draw_text(surf, f"{rinfo['label']}  •  {item.get('slot', '').title()}", question_font, rcol, WIDTH // 2, card.y + 54, center=True)

        rarity_pct = reveal.get("rarity_pct", get_crate_rarity_percent(crate_id, rarity))
        item_pct = reveal.get("item_pct", get_item_drop_chance(crate_id, item_id))
        odds_line = f"Rarity {format_drop_pct(rarity_pct)}  •  Item {format_drop_pct(item_pct)}"
        draw_text(surf, odds_line, small_font, TEXT_MUTED, WIDTH // 2, card.y + 78, center=True)

        if is_dup:
            refund = reveal.get("refund", rinfo["refund"])
            draw_text(surf, f"DUPLICATE +{refund} CR refund", body_font, ACCENT3, WIDTH // 2, card.y + 100, center=True)
        else:
            draw_text(surf, "Added & equipped!", body_font, GOOD, WIDTH // 2, card.y + 100, center=True)
            draw_mentor_avatar(surf, WIDTH // 2 - 36, card.y + 108, 72, "excited", get_wallet(), t,
                               show_bubble=False, equipped=get_equipped())

        msg = reveal.get("message", "")
        if msg:
            for i, ln in enumerate(wrap_text(msg, body_font, 400)[:2]):
                draw_text(surf, ln, small_font, TEXT_MUTED, WIDTH // 2, card.y + 168 + i * 16, center=True)

    if anim > 0.7:
        cont = Button(WIDTH // 2 - 80, ACTION_Y, 160, BTN_H, "CONTINUE", lambda: state.update({"screen": "shop"}), ACCENT2)
        cont.update(pygame.mouse.get_pos())
        cont.draw(surf, button_font)
        buttons[:] = [cont]
        draw_text(surf, "ENTER to continue", small_font, TEXT_MUTED, WIDTH // 2, FOOTER_TEXT_Y, center=True)
    else:
        buttons[:] = []
        draw_text(surf, "Opening...", body_font, TEXT_MUTED, WIDTH // 2, ACTION_Y + 10, center=True)


def draw_shop_screen(surf, t):
    """Daily shop + rarity crates — all persisted to save file."""
    draw_background(surf, t)
    draw_header(surf, "Avatar Shop & Crates", t=t)

    ensure_daily_shop()
    wallet = get_wallet()
    shop_ids = save_data.get("shop_items", [])
    owned = set(get_owned())
    equipped = get_equipped()
    tab = state.get("shop_tab", "daily")

    side_x = MARGIN
    draw_rounded_rect(surf, pygame.Rect(side_x, CONTENT_Y, SIDEBAR_W, MAIN_BOTTOM - CONTENT_Y),
                      PREVIEW_BG, radius=10, border=2, border_color=PREVIEW_BORDER)
    draw_text(surf, get_avatar_name()[:14], small_font, ACCENT, side_x + SIDEBAR_W // 2, CONTENT_Y + 10, center=True)
    draw_mentor_avatar(surf, side_x + 48, CONTENT_Y + 24, 72, "happy", wallet, t,
                       get_shop_message(), show_bubble=True, equipped=equipped)

    name_y = CONTENT_Y + 118
    draw_text(surf, "Name:", small_font, TEXT_MUTED, side_x + 10, name_y)
    name_box = pygame.Rect(side_x + 10, name_y + 14, SIDEBAR_W - 20, 30)
    av_active = state.get("shop_avatar_input_active", False)
    draw_rounded_rect(surf, name_box, (16, 22, 38), radius=6, border=2,
                      border_color=ACCENT if av_active else PANEL_BORDER)
    av_txt = state.get("avatar_name_input", get_avatar_name()) or "Type name..."
    av_col = TEXT if state.get("avatar_name_input") else TEXT_MUTED
    draw_text(surf, av_txt, body_font, av_col, side_x + 16, name_y + 29)

    if av_active and (pygame.time.get_ticks() // 450) % 2 == 0:
        tw = body_font.size(state.get("avatar_name_input", ""))[0]
        pygame.draw.line(surf, ACCENT, (side_x + 16 + tw + 2, name_y + 18), (side_x + 16 + tw + 2, name_y + 40), 2)

    def focus_avatar_name():
        state["shop_avatar_input_active"] = True
        if not state.get("avatar_name_input"):
            state["avatar_name_input"] = get_avatar_name()

    def save_shop_avatar_name():
        ok, msg = save_avatar_name(state.get("avatar_name_input", ""))
        set_shop_message(msg)
        if ok:
            state["avatar_name_input"] = get_avatar_name()
            play_sound("ping")
        else:
            play_sound("coin_down")

    shop_buttons = []
    edit_av_btn = Button(side_x + 10, name_y + 52, 108, BTN_SM, "EDIT", focus_avatar_name, ACCENT)
    save_av_btn = Button(side_x + 126, name_y + 52, 108, BTN_SM, "SAVE", save_shop_avatar_name, ACCENT2)
    av_typed = state.get("avatar_name_input", "").strip()
    save_av_btn.enabled = bool(av_typed) and not contains_profanity(av_typed)
    shop_buttons.extend([edit_av_btn, save_av_btn])

    panel_x = side_x + SIDEBAR_W + MARGIN
    panel_w = WIDTH - panel_x - MARGIN
    draw_rounded_rect(surf, pygame.Rect(panel_x, CONTENT_Y, panel_w, COLLECTION_Y - CONTENT_Y - 6),
                      PANEL_BG, radius=10, border=2, border_color=PANEL_BORDER)

    def set_tab_daily():
        state["shop_tab"] = "daily"
    def set_tab_crates():
        state["shop_tab"] = "crates"

    tab_daily = Button(panel_x + 8, CONTENT_Y + 4, 110, BTN_SM, "DAILY", set_tab_daily, ACCENT if tab == "daily" else PANEL_BORDER)
    tab_crates = Button(panel_x + 124, CONTENT_Y + 4, 110, BTN_SM, "CRATES", set_tab_crates, ACCENT3 if tab == "crates" else PANEL_BORDER)
    tab_daily.update(pygame.mouse.get_pos())
    tab_crates.update(pygame.mouse.get_pos())
    tab_daily.draw(surf, button_font)
    tab_crates.draw(surf, button_font)
    shop_buttons.extend([tab_daily, tab_crates])

    if tab == "crates":
        draw_shop_crates_tab(surf, wallet, t, shop_buttons, panel_x, panel_w)
    else:
        draw_shop_daily_tab(surf, wallet, shop_ids, owned, equipped, shop_buttons, panel_x, panel_w)

    coll_h = MAIN_BOTTOM - COLLECTION_Y
    draw_rounded_rect(surf, pygame.Rect(panel_x, COLLECTION_Y, panel_w, coll_h), (20, 28, 48), radius=8, border=2, border_color=ACCENT)
    draw_text(surf, "Collection:", small_font, ACCENT2, panel_x + 10, COLLECTION_Y + 6)
    col_x = panel_x + 10
    for item_id in get_owned():
        item = COSMETIC_CATALOG.get(item_id)
        if not item:
            continue
        is_on = equipped.get(item["slot"]) == item_id
        rcol = rarity_info(item.get("rarity", "common"))["color"]
        short = item["name"][:7]

        def make_eq(iid=item_id):
            return lambda: set_shop_message(toggle_equip(iid)[1])

        chip = Button(col_x, COLLECTION_Y + 22, 82, BTN_SM, short, make_eq(), rcol if is_on else PANEL_BORDER)
        shop_buttons.append(chip)
        col_x += 88
        if col_x > panel_x + panel_w - 90:
            break

    def leave_shop():
        state["screen"] = state.get("shop_return", "welcome")

    def shop_start_build():
        reset_game()
        start_name()

    back_btn = Button(side_x, ACTION_Y, 118, BTN_H, "BACK", leave_shop, ACCENT3)
    build_btn = Button(side_x + 128, ACTION_Y, 118, BTN_H, "BUILD", shop_start_build, ACCENT2)

    for b in shop_buttons + [back_btn, build_btn]:
        b.update(pygame.mouse.get_pos())
        b.draw(surf, button_font)
    buttons[:] = shop_buttons + [back_btn, build_btn]

    footer = "Saves to disk"
    if tab == "crates":
        footer = "% = drop odds  •  UP/DOWN scroll"
    draw_text(surf, footer, small_font, TEXT_MUTED, WIDTH // 2, FOOTER_TEXT_Y, center=True)
    draw_filter_warning(surf)


# =============================================================================
# BUTTON CLASS
# =============================================================================
class Button:
    def __init__(self, x, y, w, h, text, action=None, color=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.action = action
        self.color = color or ACCENT
        self.hovered = False
        self.enabled = True

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled

    def draw(self, surf, font):
        if not self.enabled:
            bg, brd, tc = (35, 40, 55), (60, 70, 90), (110, 120, 140)
        elif self.hovered:
            bg, brd, tc = BUTTON_HOVER, self.color, TEXT
        else:
            bg, brd, tc = BUTTON_BG, self.color, TEXT
        draw_rounded_rect(surf, self.rect, bg, radius=8, border=2, border_color=brd)
        draw_text(surf, self.text, font, tc, self.rect.centerx, self.rect.centery, center=True)

    def handle(self, event):
        if not self.enabled:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                play_sound("click")
                if self.action:
                    self.action()
                return self.action
        return None


# =============================================================================
# GAME STATE
# =============================================================================
state = {
    "screen": "welcome",
    "player_name": "",
    "answers": {},
    "current_q": 0,
    "current_input": "",
    "input_active": True,
    "score_data": None,
    "boot_anim": 0.0,
    "scroll_offset": 0,
    "credits": STARTING_CREDITS,
    "credit_log": [],
    "avatar_mood": "happy",
    "avatar_message": "You have 50 lab credits. Design wisely!",
    "last_credit_delta": 0,
    "credit_flash": 0.0,
    "run_deposited": False,
    "shop_message": "",
    "shop_return": "welcome",
    "shop_tab": "daily",
    "crate_reveal": None,
    "crate_reveal_anim": 0.0,
    "crate_detail_id": "code_crate",
    "crate_drop_scroll": 0,
    "avatar_name_input": "",
    "shop_avatar_input_active": False,
    "filter_message": "",
    "filter_flash": 0.0,
    "selected_tags": [],
    "custom_tags": [],
    "tag_input": "",
    "integrity_warning": "",
    "chat_open": False,
    "chat_tab": "all",
    "chat_input": "",
    "chat_messages": [],
    "chat_status": "Press C to open lab chat",
    "chat_players": [],
    "chat_input_active": False,
    "trade_open": False,
    "trade_partner": "",
    "trade_give_credits": 0,
    "trade_want_credits": 0,
    "trade_give_items": [],
    "trade_want_items": [],
    "trade_active": None,
    "trade_role": "",
    "trade_status_msg": "Anti-scam: both players confirm the same trade.",
    "trade_review_until": 0.0,
    "world_players": {},
    "world_x": 400,
    "world_y": 320,
    "world_selected": "",
    "world_move_cooldown": 0.0,
    "world_in": False,
    "world_message": "",
    "settings_open": False,
    "settings_rebind": "",
    "settings_status": "",
    "avatar_message_until": 0.0,
    "shop_message_until": 0.0,
}

buttons = []


def reset_game():
    global state, particles, buttons
    clear_saved_session()
    state = {
        "screen": "welcome",
        "player_name": "",
        "answers": {},
        "current_q": 0,
        "current_input": "",
        "input_active": True,
        "score_data": None,
        "boot_anim": 0.0,
        "scroll_offset": 0,
        "credits": STARTING_CREDITS,
        "credit_log": [],
        "avatar_mood": "happy",
        "avatar_message": f"You have {STARTING_CREDITS} lab credits. Design wisely!",
        "last_credit_delta": 0,
        "credit_flash": 0.0,
        "run_deposited": False,
        "shop_message": "",
        "shop_return": "welcome",
        "shop_tab": "daily",
        "crate_reveal": None,
        "crate_reveal_anim": 0.0,
        "crate_detail_id": "code_crate",
        "crate_drop_scroll": 0,
        "avatar_name_input": "",
        "shop_avatar_input_active": False,
        "filter_message": "",
        "filter_flash": 0.0,
        "selected_tags": [],
        "custom_tags": [],
        "tag_input": "",
        "integrity_warning": state.get("integrity_warning", ""),
        "chat_open": state.get("chat_open", False),
        "chat_tab": state.get("chat_tab", "all"),
        "chat_input": "",
        "chat_messages": state.get("chat_messages", [])[-MAX_CHAT_LOG:],
        "chat_status": state.get("chat_status", "Press C to open lab chat"),
        "chat_players": state.get("chat_players", []),
        "chat_input_active": False,
        "trade_open": state.get("trade_open", False),
        "trade_partner": state.get("trade_partner", ""),
        "trade_give_credits": 0,
        "trade_want_credits": 0,
        "trade_give_items": [],
        "trade_want_items": [],
        "trade_active": state.get("trade_active"),
        "trade_role": state.get("trade_role", ""),
        "trade_status_msg": state.get("trade_status_msg", ""),
        "trade_review_until": 0.0,
    }
    particles.clear()
    buttons.clear()


def get_answer(qid, default=""):
    return state["answers"].get(qid, default)


def set_answer(qid, value):
    state["answers"][qid] = value


# =============================================================================
# NAVIGATION & INPUT
# =============================================================================
def start_name():
    """Begin a fresh build (clears any saved in-progress session)."""
    clear_saved_session()
    state["screen"] = "name"
    state["player_name"] = ""
    state["answers"] = {}
    state["current_q"] = 0
    state["selected_tags"] = []
    state["custom_tags"] = []
    state["tag_input"] = ""
    state["current_input"] = save_data.get("player_name", "")
    state["input_active"] = True
    persist_session()


def continue_build():
    """Resume an interrupted build from disk."""
    if resume_session():
        play_sound("ping")
    else:
        start_name()


def start_avatar_name():
    """Step 2 — name the credit mentor avatar (persisted to save file)."""
    state["screen"] = "avatar_name"
    state["current_input"] = get_avatar_name() if get_avatar_name() != "Mentor" else ""
    state["input_active"] = True


def submit_name():
    val = state["current_input"].strip()
    if not val:
        return
    ok, err = validate_player_text(val)
    if not ok:
        reject_filtered_text(err)
        return
    state["player_name"] = format_display_name(val)
    save_data["player_name"] = state["player_name"]
    state["filter_message"] = ""
    play_sound("ping")
    persist_session()
    start_avatar_name()


def submit_avatar_name():
    val = state["current_input"].strip()
    if not val:
        return
    ok, err = validate_player_text(val)
    if not ok:
        reject_filtered_text(err)
        set_avatar_message(err)
        return
    ok, msg = save_avatar_name(val)
    if ok:
        play_sound("ping")
        set_avatar_message(msg)
        persist_session()
        start_design()
    else:
        set_avatar_message(msg)
        play_sound("coin_down")


def start_design():
    state["screen"] = "design"
    if not state.get("answers"):
        state["current_q"] = 0
        state["credits"] = STARTING_CREDITS
        state["credit_log"] = []
        state["avatar_mood"] = "happy"
        set_avatar_message((
            f"Hi, I'm {get_avatar_name()}! You start with {STARTING_CREDITS} credits. "
            "Strong answers earn more — weak ones cost you."
        ))
    load_question_input()
    persist_session()


def load_question_input():
    q = DESIGN_QUESTIONS[state["current_q"]]
    state["current_input"] = ""
    state["input_active"] = True
    existing = get_answer(q["id"])
    if existing:
        state["current_input"] = existing


def award_credits_for_answer(q_id, answer, is_update=False):
    """Give or take credits when an answer is submitted."""
    delta, points, reason = credit_delta_for_answer(q_id, answer)

    # Re-answering after going BACK: undo old transaction first
    if is_update:
        for i, entry in enumerate(state["credit_log"]):
            if entry["q_id"] == q_id:
                state["credits"] = max(0, state["credits"] - entry["delta"])
                state["credit_log"].pop(i)
                break

    apply_credit_change(delta, reason, q_id)
    return delta


def submit_current_text():
    q = DESIGN_QUESTIONS[state["current_q"]]
    val = state["current_input"].strip()
    if not val:
        return
    ok, err = validate_player_text(val)
    if not ok:
        reject_filtered_text(err)
        set_avatar_message(err)
        return
    is_update = bool(get_answer(q["id"]))
    set_answer(q["id"], val)
    award_credits_for_answer(q["id"], val, is_update=is_update)
    persist_session()
    advance_question()


def advance_question():
    if state["current_q"] < len(DESIGN_QUESTIONS) - 1:
        state["current_q"] += 1
        load_question_input()
        persist_session()
        play_sound("ping")
    else:
        go_to_tags_screen()


def go_to_tags_screen():
    """After the 7 design questions — pick preset + custom tags."""
    q = DESIGN_QUESTIONS[state["current_q"]]
    if state["current_input"].strip():
        val = state["current_input"].strip()
        ok, err = validate_player_text(val)
        if not ok:
            reject_filtered_text(err)
            set_avatar_message(err)
            return
        is_update = bool(get_answer(q["id"]))
        set_answer(q["id"], val)
        award_credits_for_answer(q["id"], val, is_update=is_update)

    state["screen"] = "tags"
    state["tag_input"] = ""
    state["input_active"] = True
    set_avatar_message((
        f"Preset tags are FREE! Custom tags cost {CUSTOM_TAG_COST} CR each "
        f"(and go through the friendly filter — no tricks. :D)"
    ))
    persist_session()
    play_sound("ping")


def go_back_from_tags():
    state["screen"] = "design"
    state["current_q"] = len(DESIGN_QUESTIONS) - 1
    load_question_input()
    persist_session()
    play_sound("back")


def submit_tags_and_finish():
    """Finish build after tags — needs at least one tag."""
    if get_total_tag_count() < 1:
        set_avatar_message("Pick at least one tag (preset or custom)!")
        play_sound("coin_down")
        return
    sync_tags_to_answers()
    if get_total_tag_count() >= 3:
        apply_credit_change(5, "Tag bonus — your assistant is easy to find!", "tags")
    persist_session()
    finish_design()


def go_back_question():
    if state["current_q"] > 0:
        state["current_q"] -= 1
        load_question_input()
        persist_session()
        play_sound("back")


def finish_design():
    """Score the design and show the summary screen."""
    # Capture any text still in the input box and award credits if needed
    q = DESIGN_QUESTIONS[state["current_q"]]
    if state["current_input"].strip():
        val = state["current_input"].strip()
        ok, err = validate_player_text(val)
        if not ok:
            reject_filtered_text(err)
            set_avatar_message(err)
            return
        old = get_answer(q["id"])
        set_answer(q["id"], val)
        if not any(e["q_id"] == q["id"] for e in state["credit_log"]):
            award_credits_for_answer(q["id"], val)
        elif old != val:
            award_credits_for_answer(q["id"], val, is_update=True)

    answers_list = build_answers_list(state["answers"])
    total, max_score, rating, message = calculate_design_score(answers_list)
    category_scores = calculate_category_scores(state["answers"])
    synergy, synergy_msg = calculate_synergy_bonus(category_scores)

    if synergy != 0:
        apply_credit_change(synergy, synergy_msg or "Build synergy adjustment.", "synergy")

    final_credits = state["credits"]
    net_change = final_credits - STARTING_CREDITS

    if final_credits >= STARTING_CREDITS + 35:
        mentor_closing = "Outstanding! I'd fund your assistant tomorrow."
    elif final_credits >= STARTING_CREDITS:
        mentor_closing = "Nice work — you earned your credits fair and square."
    elif final_credits >= 25:
        mentor_closing = "Hmm… some good ideas, but the build needs work."
    else:
        mentor_closing = "Back to the lab! This design lost too many credits."

    state["score_data"] = {
        "total": total,
        "max": max_score,
        "rating": rating,
        "message": message,
        "answers_list": answers_list,
        "category_scores": category_scores,
        "final_credits": final_credits,
        "net_change": net_change,
        "log": list(state["credit_log"]),
        "synergy_bonus": synergy,
        "synergy_message": synergy_msg,
        "mentor_closing": mentor_closing,
    }
    state["avatar_mood"] = get_avatar_mood(final_credits)
    set_avatar_message(mentor_closing)

    # Bank run earnings to the persistent wallet once (saved to disk immediately)
    if not state.get("run_deposited"):
        deposit_run_earnings(net_change)
        state["run_deposited"] = True
        if net_change > 0:
            mentor_closing += f"  +{net_change} CR deposited to your saved wallet!"
        elif net_change < 0:
            mentor_closing += f"  {net_change} CR deducted from your saved wallet."
        state["score_data"]["mentor_closing"] = mentor_closing

    save_last_build(state["score_data"])
    clear_saved_session()

    state["screen"] = "summary"
    state["boot_anim"] = 0.0
    state["scroll_offset"] = 0
    particles.clear()
    play_sound("success")
    spawn_particles(WIDTH // 2, 320, count=20, color=(120, 220, 255))


def handle_text_input(event):
    if not state["input_active"]:
        return
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_BACKSPACE:
            if state["screen"] == "shop" and state.get("shop_avatar_input_active"):
                state["avatar_name_input"] = state.get("avatar_name_input", "")[:-1]
                play_sound("key")
                return
            if state["screen"] == "tags":
                state["tag_input"] = state.get("tag_input", "")[:-1]
                play_sound("key")
                if contains_profanity(state.get("tag_input", "")):
                    state["filter_message"] = FILTER_TAG_QUIP
                    state["filter_flash"] = 1.5
                persist_session()
                return
            state["current_input"] = state["current_input"][:-1]
            play_sound("key")
            if state["screen"] in ("name", "avatar_name", "design"):
                persist_session()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if state["screen"] == "name":
                submit_name()
            elif state["screen"] == "avatar_name":
                submit_avatar_name()
            elif state["screen"] == "tags":
                add_custom_tag_from_input()
            elif state["screen"] == "shop" and state.get("shop_avatar_input_active"):
                av_val = state.get("avatar_name_input", "").strip()
                ok_text, err = validate_player_text(av_val)
                if not ok_text:
                    reject_filtered_text(err)
                    set_shop_message(err)
                else:
                    ok, msg = save_avatar_name(av_val)
                    set_shop_message(msg)
                    state["shop_avatar_input_active"] = False
                    if ok:
                        state["avatar_name_input"] = get_avatar_name()
                        play_sound("ping")
            else:
                submit_current_text()
        else:
            if state["screen"] == "tags":
                if len(state.get("tag_input", "")) < 20:
                    ch = event.unicode
                    if ch and (ch.isprintable() or ch == " "):
                        state["tag_input"] = state.get("tag_input", "") + ch
                        play_sound("key")
                        if contains_profanity(state.get("tag_input", "")):
                            state["filter_message"] = FILTER_TAG_QUIP
                            state["filter_flash"] = 1.5
                        persist_session()
                return
            if state["screen"] == "shop" and state.get("shop_avatar_input_active"):
                max_len = 20
                if len(state.get("avatar_name_input", "")) < max_len:
                    ch = event.unicode
                    if ch and (ch.isprintable() or ch == " "):
                        state["avatar_name_input"] = state.get("avatar_name_input", "") + ch
                        play_sound("key")
                        if contains_profanity(state.get("avatar_name_input", "")):
                            state["filter_message"] = FILTER_MESSAGE
                            state["filter_flash"] = 1.5
                return
            max_len = 28 if state["screen"] in ("name", "avatar_name") else 48
            if len(state["current_input"]) < max_len:
                ch = event.unicode
                if ch and (ch.isprintable() or ch == " "):
                    state["current_input"] += ch
                    play_sound("key")
                    if contains_profanity(state["current_input"]):
                        state["filter_message"] = FILTER_MESSAGE
                        state["filter_flash"] = 1.5
                    # Live-update preview for name question
                    if state["screen"] == "design":
                        q = DESIGN_QUESTIONS[state["current_q"]]
                        if q["id"] == "name":
                            set_answer("name", state["current_input"])
                    if state["screen"] in ("name", "avatar_name", "design"):
                        persist_session()


# =============================================================================
# BACKGROUND — subtle circuit / code pattern
# =============================================================================
circuit_lines = [
    (random.randint(0, WIDTH), random.randint(0, HEIGHT),
     random.randint(0, WIDTH), random.randint(0, HEIGHT))
    for _ in range(18)
]


# =============================================================================
# LAB CHAT — talk to other players (assistant_lab_chat_server.py)
# =============================================================================
def toggle_chat():
    state["chat_open"] = not state.get("chat_open", False)
    if state["chat_open"]:
        state["chat_input_active"] = True
        if not chat_client.connected:
            name = state.get("player_name") or save_data.get("player_name") or "Builder"
            chat_client.host = CHAT_HOST
            chat_client.port = CHAT_PORT
            chat_client.connect(name)
    else:
        state["chat_input_active"] = False


def disconnect_chat():
    chat_client.disconnect()
    state["chat_status"] = "Chat closed."


CHAT_TABS = ("all", "chat", "drops")


def append_chat_line(kind: str, text: str, name: str = "", **extra):
    lines = state.setdefault("chat_messages", [])
    lines.append({"kind": kind, "text": text, "name": name, **extra})
    state["chat_messages"] = lines[-MAX_CHAT_LOG:]


def announce_crate_drop(crate_id: str, item_id: str, rarity: str, duplicate: bool, refund: int) -> None:
    """Post crate pull to lab chat Drops tab (local + broadcast if online)."""
    player = (
        state.get("player_name")
        or save_data.get("player_name")
        or chat_client.player_name
        or "Builder"
    )
    if chat_client.connected:
        chat_client.send_crate_drop(
            crate_id=crate_id, item_id=item_id, rarity=rarity,
            duplicate=duplicate, refund=refund,
        )
    else:
        text = format_crate_drop_line(
            player, crate_id, item_id, rarity, duplicate=duplicate, refund=refund,
        )
        append_chat_line(
            "crate_drop", text, player,
            crate_id=crate_id, item_id=item_id, rarity=rarity,
            duplicate=duplicate, refund=refund,
        )


def chat_messages_for_tab(tab: str | None = None) -> list[dict]:
    tab = tab or state.get("chat_tab", "all")
    messages = state.get("chat_messages", [])
    if tab == "chat":
        return [m for m in messages if m.get("kind") == "chat"]
    if tab == "drops":
        return [m for m in messages if m.get("kind") == "crate_drop"]
    return messages


def set_chat_tab(tab: str):
    if tab in CHAT_TABS:
        state["chat_tab"] = tab


def process_chat_events():
    for ev in chat_client.poll_events():
        et = ev.get("type")
        if et == "chat":
            who = ev.get("name", "?")
            append_chat_line("chat", ev.get("text", ""), who)
        elif et == "system":
            append_chat_line("system", ev.get("text", ""))
            state["chat_status"] = ev.get("text", "")
        elif et == "status":
            state["chat_status"] = ev.get("text", "")
        elif et == "error":
            append_chat_line("error", ev.get("text", ""))
            state["chat_status"] = ev.get("text", "")
            state["trade_status_msg"] = ev.get("text", "")
        elif et == "roster":
            state["chat_players"] = ev.get("players", [])
        elif et == "trade_offer":
            state["trade_active"] = {
                "trade_id": ev.get("trade_id"),
                "from": ev.get("from"),
                "to": ev.get("to"),
                "a_gives": ev.get("a_gives", {}),
                "a_wants": ev.get("a_wants", {}),
                "a_confirmed": False,
                "b_confirmed": False,
            }
            state["trade_role"] = ev.get("role", "receiver")
            state["trade_review_until"] = float(ev.get("review_until", 0))
            state["trade_open"] = True
            state["trade_status_msg"] = ev.get("anti_scam", "Review the trade carefully!")
            append_chat_line("system", ev.get("text", "Trade offer received."))
        elif et == "trade_status":
            if state.get("trade_active", {}).get("trade_id") == ev.get("trade_id"):
                state["trade_active"]["a_confirmed"] = ev.get("a_confirmed", False)
                state["trade_active"]["b_confirmed"] = ev.get("b_confirmed", False)
                state["trade_status_msg"] = (
                    f"Confirmations: {ev.get('from')}={'YES' if ev.get('a_confirmed') else 'no'} "
                    f"{ev.get('to')}={'YES' if ev.get('b_confirmed') else 'no'}"
                )
        elif et == "trade_execute":
            my_name = state.get("player_name") or save_data.get("player_name") or chat_client.player_name
            ok, msg = apply_trade_to_save(
                save_data,
                my_name=my_name,
                trade_id=ev.get("trade_id", ""),
                from_player=ev.get("from", ""),
                to_player=ev.get("to", ""),
                a_gives=ev.get("a_gives", {}),
                a_wants=ev.get("a_wants", {}),
            )
            if ok:
                write_save()
                state["trade_status_msg"] = msg
                append_chat_line("system", msg)
                play_sound("success")
            else:
                state["trade_status_msg"] = msg
                append_chat_line("error", msg)
                play_sound("coin_down")
            state["trade_active"] = None
            state["trade_give_items"] = []
            state["trade_want_items"] = []
            state["trade_give_credits"] = 0
            state["trade_want_credits"] = 0
        elif et == "trade_cancelled":
            if not state.get("trade_active") or state["trade_active"].get("trade_id") == ev.get("trade_id"):
                state["trade_active"] = None
                state["trade_status_msg"] = ev.get("reason", "Trade cancelled.")
                append_chat_line("system", state["trade_status_msg"])
        elif et == "world_joined":
            state["world_in"] = True
            state["world_x"] = ev.get("x", 400)
            state["world_y"] = ev.get("y", 320)
            state["world_message"] = "Welcome to the Social Lab — flex your gear!"
        elif et == "world_state":
            roster = {}
            my_name = state.get("player_name") or save_data.get("player_name") or chat_client.player_name
            for p in ev.get("players", []):
                pname = p.get("name")
                if pname and pname != my_name:
                    roster[pname] = p
            state["world_players"] = roster
        elif et == "world_move":
            pname = ev.get("name")
            if pname and pname in state.get("world_players", {}):
                state["world_players"][pname]["x"] = ev.get("x", 400)
                state["world_players"][pname]["y"] = ev.get("y", 320)
        elif et == "world_player_left":
            pname = ev.get("name")
            state.get("world_players", {}).pop(pname, None)
            if state.get("world_selected") == pname:
                state["world_selected"] = ""
        elif et == "world_emote":
            pname = ev.get("name")
            if pname in state.get("world_players", {}):
                state["world_players"][pname]["emote_until"] = ev.get("until", 0)
            append_chat_line("system", ev.get("text", f"{pname} flexed!"))
        elif et == "crate_drop":
            append_chat_line(
                "crate_drop", ev.get("text", ""),
                ev.get("name", "?"),
                crate_id=ev.get("crate_id", ""),
                item_id=ev.get("item_id", ""),
                rarity=ev.get("rarity", "common"),
                duplicate=ev.get("duplicate", False),
                refund=ev.get("refund", 0),
            )
        elif et == "admin_gift":
            ok, msg = apply_admin_gift(
                save_data,
                credits=ev.get("credits", 0),
                items=ev.get("items", []),
            )
            if ok:
                write_save()
                append_chat_line("system", msg)
                state["chat_status"] = msg
                note = (ev.get("message") or "").strip()
                if note:
                    append_chat_line("system", f"Admin note: {note}")
                play_sound("success")
            else:
                append_chat_line("error", msg)
                state["chat_status"] = msg


def send_chat_message():
    ok, err = chat_client.send_message(state.get("chat_input", ""))
    if ok:
        state["chat_input"] = ""
    elif err:
        state["chat_status"] = err
        if "filter" in (err or "").lower() or "friendly" in (err or "").lower():
            state["filter_message"] = err
            state["filter_flash"] = 2.0


def handle_chat_key(event):
    if not state.get("chat_open"):
        return False
    if event.type != pygame.KEYDOWN:
        return False
    if event.key == pygame.K_ESCAPE:
        state["chat_open"] = False
        state["chat_input_active"] = False
        return True
    if event.key == pygame.K_BACKSPACE:
        state["chat_input"] = state.get("chat_input", "")[:-1]
        return True
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        send_chat_message()
        return True
    if len(state.get("chat_input", "")) < 120:
        ch = event.unicode
        if ch and (ch.isprintable() or ch == " "):
            state["chat_input"] = state.get("chat_input", "") + ch
            if contains_profanity(state["chat_input"]):
                state["filter_message"] = FILTER_MESSAGE
                state["filter_flash"] = 1.5
        return True
    return True


def control_hints_line() -> str:
    binds = get_settings().get("keybinds", DEFAULT_KEYBINDS)
    fs = format_key_display(binds.get("fullscreen", "f11"))
    return (
        f"{format_key_display(binds.get('build', 'space'))} = build  •  "
        f"{format_key_display(binds.get('world', 'l'))} = world  •  "
        f"{format_key_display(binds.get('chat', 'c'))} = chat  •  "
        f"{fs} = fullscreen  •  ESC = quit"
    )


def toggle_settings():
    state["settings_open"] = not state.get("settings_open", False)
    state["settings_rebind"] = ""
    state["settings_status"] = ""


def toggle_mute_setting():
    s = get_settings()
    s["muted"] = not s.get("muted", False)
    save_settings(s)
    state["settings_status"] = "Sound muted." if s["muted"] else "Sound on."
    if not s["muted"]:
        play_sound("ping")


def toggle_fullscreen_setting():
    toggle_fullscreen()


def set_message_duration_setting(secs: int):
    s = get_settings()
    s["message_duration"] = secs
    save_settings(s)
    state["settings_status"] = f"Character messages fade after {secs}s."


def reset_settings_defaults():
    save_settings(default_settings())
    state["settings_rebind"] = ""
    state["settings_status"] = "Settings reset to defaults."


def start_keybind_rebind(action: str):
    state["settings_rebind"] = action
    state["settings_status"] = f"Press a key for {KEYBIND_LABELS.get(action, action)}..."


def handle_settings_key(event) -> bool:
    if not state.get("settings_open"):
        return False
    if event.type != pygame.KEYDOWN:
        return True
    if event.key == pygame.K_ESCAPE:
        if state.get("settings_rebind"):
            state["settings_rebind"] = ""
            state["settings_status"] = "Rebind cancelled."
        else:
            state["settings_open"] = False
        return True
    action = state.get("settings_rebind")
    if action:
        key_name = event_to_key_name(event)
        if not key_name or key_name == "escape":
            state["settings_status"] = "Pick a letter, number, or Space."
            return True
        s = get_settings()
        binds = dict(s.get("keybinds", DEFAULT_KEYBINDS))
        ok, msg = assign_keybind(binds, action, key_name)
        state["settings_status"] = msg
        if ok:
            s["keybinds"] = binds
            save_settings(s)
            state["settings_rebind"] = ""
            play_sound("click")
    return True


def draw_settings_panel(surf):
    if not state.get("settings_open"):
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((8, 12, 24, 200))
    surf.blit(overlay, (0, 0))

    pw, ph = 520, 500
    px, py = (WIDTH - pw) // 2, (HEIGHT - ph) // 2
    panel = pygame.Rect(px, py, pw, ph)
    draw_rounded_rect(surf, panel, (18, 24, 42), radius=14, border=2, border_color=ACCENT2)
    draw_text(surf, "SETTINGS", header_font, ACCENT2, px + 16, py + 12)

    s = get_settings()
    y = py + 44

    draw_text(surf, "Audio", question_font, ACCENT3, px + 16, y)
    mute_lbl = "MUTED" if s.get("muted") else "SOUND ON"
    mute_col = BAD if s.get("muted") else GOOD
    mute_btn = Button(px + 16, y + 18, 120, 30, mute_lbl, toggle_mute_setting, mute_col)
    mute_btn.update(pygame.mouse.get_pos())
    mute_btn.draw(surf, button_font)
    buttons.append(mute_btn)
    fs_lbl = "FULLSCREEN" if s.get("fullscreen") else "WINDOWED"
    fs_col = ACCENT2 if s.get("fullscreen") else PANEL_BORDER
    fs_btn = Button(px + 144, y + 18, 120, 30, fs_lbl, toggle_fullscreen_setting, fs_col)
    fs_btn.update(pygame.mouse.get_pos())
    fs_btn.draw(surf, button_font)
    buttons.append(fs_btn)

    y += 62
    draw_text(surf, "Character message time", question_font, ACCENT3, px + 16, y)
    dx = px + 16
    for secs in MESSAGE_DURATION_OPTIONS:
        col = ACCENT2 if s.get("message_duration") == secs else PANEL_BORDER
        def make_dur(d=secs):
            return lambda: set_message_duration_setting(d)
        dbtn = Button(dx, y + 18, 52, 28, f"{secs}s", make_dur(), col)
        dbtn.update(pygame.mouse.get_pos())
        dbtn.draw(surf, button_font)
        buttons.append(dbtn)
        dx += 58

    y += 58
    draw_text(surf, "Keybinds (click to change)", question_font, ACCENT3, px + 16, y)
    binds = s.get("keybinds", DEFAULT_KEYBINDS)
    row_y = y + 22
    for action in DEFAULT_KEYBINDS:
        label = KEYBIND_LABELS.get(action, action)
        key_lbl = format_key_display(binds.get(action, DEFAULT_KEYBINDS[action]))
        active = state.get("settings_rebind") == action
        draw_text(surf, f"{label}", body_font, TEXT, px + 24, row_y + 14)
        col = ACCENT if active else ACCENT3
        def make_rb(a=action):
            return lambda: start_keybind_rebind(a)
        kbtn = Button(px + pw - 120, row_y + 4, 96, 26, key_lbl, make_rb(), col)
        kbtn.update(pygame.mouse.get_pos())
        kbtn.draw(surf, button_font)
        buttons.append(kbtn)
        row_y += 30

    status = state.get("settings_status", "")
    if status:
        draw_text(surf, status[:58], small_font, TEXT_MUTED, px + 16, py + ph - 72)

    reset_btn = Button(px + 16, py + ph - 44, 130, 32, "RESET", reset_settings_defaults, ACCENT3)
    close_btn = Button(px + pw - 146, py + ph - 44, 130, 32, "CLOSE", toggle_settings, ACCENT2)
    for b in (reset_btn, close_btn):
        b.update(pygame.mouse.get_pos())
        b.draw(surf, button_font)
        buttons.append(b)


def draw_chat_panel(surf):
    if not state.get("chat_open"):
        return
    pw, ph = 340, 360
    px, py = WIDTH - pw - MARGIN, CONTENT_Y
    panel = pygame.Rect(px, py, pw, ph)
    draw_rounded_rect(surf, panel, (18, 24, 42), radius=12, border=2, border_color=ACCENT2)
    draw_text(surf, "LAB CHAT", header_font, ACCENT2, px + 12, py + 10)
    trade_lbl = "TRADE*" if state.get("trade_open") else "TRADE"
    trade_tog = Button(px + pw - 72, py + 4, 64, 24, trade_lbl, toggle_trade, ACCENT3 if state.get("trade_open") else PANEL_BORDER)
    trade_tog.update(pygame.mouse.get_pos())
    trade_tog.draw(surf, button_font)
    buttons.append(trade_tog)
    status = state.get("chat_status", "")
    draw_text(surf, status[:42], small_font, TEXT_MUTED, px + 12, py + 30)

    players = state.get("chat_players") or []
    if players:
        draw_text(surf, f"Online: {', '.join(players[:5])}", small_font, ACCENT, px + 12, py + 46)

    tab_y = py + 58
    tab_labels = (("all", "All"), ("chat", "Chat"), ("drops", "Drops"))
    tab_x = px + 8
    for tid, label in tab_labels:
        active = state.get("chat_tab", "all") == tid
        col = ACCENT2 if active else PANEL_BORDER
        def make_tab(t=tid):
            return lambda: set_chat_tab(t)
        tab_btn = Button(tab_x, tab_y, 72, 22, label, make_tab(), col)
        tab_btn.update(pygame.mouse.get_pos())
        tab_btn.draw(surf, button_font)
        buttons.append(tab_btn)
        tab_x += 76

    log_rect = pygame.Rect(px + 8, py + 86, pw - 16, ph - 142)
    draw_rounded_rect(surf, log_rect, (12, 16, 28), radius=6, border=1, border_color=PANEL_BORDER)
    filtered = chat_messages_for_tab()
    y = log_rect.y + 6
    if not filtered:
        empty = {
            "chat": "No chat messages yet.",
            "drops": "No crate drops yet — open a crate!",
        }.get(state.get("chat_tab", "all"), "No messages yet.")
        draw_text(surf, empty, small_font, TEXT_MUTED, log_rect.x + 6, y)
    for msg in filtered[-14:]:
        if y > log_rect.bottom - 14:
            break
        kind = msg.get("kind", "chat")
        if kind == "chat":
            line = f"{msg.get('name', '?')}: {msg.get('text', '')}"
            col = TEXT
        elif kind == "crate_drop":
            line = msg.get("text", "")
            col = rarity_info(msg.get("rarity", "common"))["color"]
        elif kind == "system":
            line = f"* {msg.get('text', '')}"
            col = ACCENT3
        else:
            line = msg.get("text", "")
            col = BAD
        for wrap in wrap_text(line[:100], small_font, log_rect.width - 8)[:2]:
            draw_text(surf, wrap, small_font, col, log_rect.x + 6, y)
            y += 14

    box_y = py + ph - 48
    box = pygame.Rect(px + 10, box_y, pw - 20, 32)
    active = state.get("chat_input_active", True)
    dirty = state.get("chat_input", "")
    box_col = BAD if dirty and contains_profanity(dirty) else (ACCENT if active else PANEL_BORDER)
    draw_rounded_rect(surf, box, (16, 22, 38), radius=6, border=2, border_color=box_col)
    draw_text(surf, dirty or "Say something friendly...", body_font,
              TEXT if dirty else TEXT_MUTED, box.x + 8, box.centery, center=False)
    draw_text(surf, "ENTER send  •  TRADE button  •  ESC close", small_font, TEXT_MUTED, px + pw // 2, py + ph - 10, center=True)


def toggle_trade():
    if not chat_client.connected:
        name = state.get("player_name") or save_data.get("player_name") or "Builder"
        chat_client.connect(name)
    state["trade_open"] = not state.get("trade_open", False)
    state["chat_open"] = True
    if not state["trade_open"]:
        state["trade_status_msg"] = "Trade panel closed."


def _trade_my_give_receive():
    """What local player gives/receives in the active server trade."""
    t = state.get("trade_active") or {}
    my_name = state.get("player_name") or save_data.get("player_name") or chat_client.player_name
    a_gives = normalize_bundle(t.get("a_gives"))
    a_wants = normalize_bundle(t.get("a_wants"))
    if my_name == t.get("from"):
        return a_gives, a_wants
    if my_name == t.get("to"):
        return a_wants, a_gives
    return a_gives, a_wants


def trade_review_ready() -> bool:
    return time.time() >= state.get("trade_review_until", 0)


def trade_seconds_left() -> int:
    return max(0, int(state.get("trade_review_until", 0) - time.time()) + 1)


def send_trade_offer():
    if not purchases_allowed():
        state["trade_status_msg"] = save_data.get("integrity_message", "Trading disabled.")
        return
    partner = state.get("trade_partner", "").strip()
    if not partner:
        state["trade_status_msg"] = "Pick a partner from the list."
        return
    give = normalize_bundle({
        "credits": state.get("trade_give_credits", 0),
        "items": state.get("trade_give_items", []),
    })
    want = normalize_bundle({
        "credits": state.get("trade_want_credits", 0),
        "items": state.get("trade_want_items", []),
    })
    owned = set(get_owned())
    wallet = get_wallet()
    ok, err = can_afford_side(give, wallet, owned)
    if not ok:
        state["trade_status_msg"] = err
        return
    ok, err = chat_client.send_trade_offer(partner, give, want)
    if ok:
        state["trade_status_msg"] = f"Offer sent to {partner}!"
        play_sound("ping")
    else:
        state["trade_status_msg"] = err or "Could not send offer."


def confirm_active_trade():
    t = state.get("trade_active")
    if not t:
        state["trade_status_msg"] = "No active trade."
        return
    if not trade_review_ready():
        state["trade_status_msg"] = f"Review {trade_seconds_left()}s more (anti-scam timer)."
        play_sound("coin_down")
        return
    give, _recv = _trade_my_give_receive()
    owned = set(get_owned())
    ok, err = can_afford_side(give, get_wallet(), owned)
    if not ok:
        state["trade_status_msg"] = err
        return
    ok, err = chat_client.send_trade_confirm(t.get("trade_id", ""))
    if ok:
        state["trade_status_msg"] = "You confirmed! Waiting for partner..."
        play_sound("ping")
    else:
        state["trade_status_msg"] = err or "Confirm failed."


def cancel_active_trade():
    t = state.get("trade_active")
    if t:
        chat_client.send_trade_cancel(t.get("trade_id", ""))
    state["trade_active"] = None
    state["trade_status_msg"] = "Trade cancelled."


def toggle_trade_item(item_id: str, side: str):
    key = "trade_give_items" if side == "give" else "trade_want_items"
    items = list(state.get(key, []))
    if item_id in items:
        items.remove(item_id)
    elif len(items) < MAX_TRADE_ITEMS:
        items.append(item_id)
    state[key] = items


def draw_trade_panel(surf):
    if not state.get("trade_open"):
        return
    pw, ph = 420, 420
    px, py = MARGIN, CONTENT_Y
    panel = pygame.Rect(px, py, pw, ph)
    draw_rounded_rect(surf, panel, (20, 26, 44), radius=12, border=2, border_color=ACCENT3)
    draw_text(surf, "SAFE TRADING", header_font, ACCENT3, px + 12, py + 10)
    draw_text(surf, "Anti-scam: BOTH confirm • 5s review • frozen offer", small_font, TEXT_MUTED, px + 12, py + 30)

    trade_buttons = []
    t = state.get("trade_active")
    my_name = state.get("player_name") or save_data.get("player_name") or chat_client.player_name

    if t:
        give, receive = _trade_my_give_receive()
        other = t.get("to") if my_name == t.get("from") else t.get("from")
        draw_text(surf, f"Trade #{t.get('trade_id', '')} with {other}",
                  small_font, ACCENT2, px + 12, py + 50)
        draw_text(surf, f"YOU GIVE: {bundle_label(give)}", body_font, BAD, px + 12, py + 72)
        draw_text(surf, f"YOU GET:  {bundle_label(receive)}", body_font, GOOD, px + 12, py + 94)
        a_ok = t.get("a_confirmed", False)
        b_ok = t.get("b_confirmed", False)
        draw_text(surf, f"{t.get('from')}: {'CONFIRMED' if a_ok else 'waiting'}  |  "
                  f"{t.get('to')}: {'CONFIRMED' if b_ok else 'waiting'}",
                  small_font, TEXT_MUTED, px + 12, py + 116)
        if not trade_review_ready():
            draw_text(surf, f"Review timer: {trade_seconds_left()}s (read carefully!)", small_font, ACCENT3, px + 12, py + 134)
        conf = Button(px + 12, py + ph - 44, 120, 32, "CONFIRM", confirm_active_trade, GOOD)
        conf.enabled = trade_review_ready()
        can = Button(px + 140, py + ph - 44, 100, 32, "CANCEL", cancel_active_trade, BAD)
        trade_buttons.extend([conf, can])
    else:
        draw_text(surf, "New offer — pick partner:", small_font, TEXT_MUTED, px + 12, py + 48)
        players = [p for p in state.get("chat_players", []) if p != my_name]
        bx, by = px + 12, py + 64
        for pname in players[:4]:
            def make_pick(n=pname):
                return lambda: state.update({"trade_partner": n})
            sel = state.get("trade_partner") == pname
            trade_buttons.append(Button(bx, by, 88, 24, pname[:10], make_pick(), ACCENT2 if sel else PANEL_BORDER))
            bx += 94

        gy = py + 98
        draw_text(surf, f"YOU OFFER (max {MAX_TRADE_CREDITS} CR, {MAX_TRADE_ITEMS} items):", small_font, BAD, px + 12, gy)
        gc = state.get("trade_give_credits", 0)
        trade_buttons.append(Button(px + 12, gy + 18, 36, 24, "-", lambda: state.update({"trade_give_credits": max(0, gc - 10)}), ACCENT))
        draw_text(surf, f"{gc} CR", body_font, TEXT, px + 56, gy + 30)
        trade_buttons.append(Button(px + 100, gy + 18, 36, 24, "+", lambda: state.update({"trade_give_credits": min(MAX_TRADE_CREDITS, gc + 10)}), ACCENT))

        lx, ly = px + 12, gy + 48
        for iid in get_owned()[:8]:
            item = COSMETIC_CATALOG.get(iid, {})
            short = item.get("name", iid)[:11]
            sel = iid in state.get("trade_give_items", [])
            def make_g(i=iid):
                return lambda: toggle_trade_item(i, "give")
            bw = min(98, small_font.size(short)[0] + 16)
            trade_buttons.append(Button(lx, ly, bw, 22, short, make_g(), ACCENT2 if sel else PANEL_BORDER))
            lx += bw + 4
            if lx > px + pw - 100:
                lx = px + 12
                ly += 26

        wy = py + 220
        draw_text(surf, "YOU WANT:", small_font, GOOD, px + 12, wy)
        wc = state.get("trade_want_credits", 0)
        trade_buttons.append(Button(px + 12, wy + 18, 36, 24, "-", lambda: state.update({"trade_want_credits": max(0, wc - 10)}), ACCENT))
        draw_text(surf, f"{wc} CR", body_font, TEXT, px + 56, wy + 30)
        trade_buttons.append(Button(px + 100, wy + 18, 36, 24, "+", lambda: state.update({"trade_want_credits": min(MAX_TRADE_CREDITS, wc + 10)}), ACCENT))
        wx, wy2 = px + 12, wy + 50
        for iid, item in list(COSMETIC_CATALOG.items())[:10]:
            short = item.get("name", iid)[:11]
            sel = iid in state.get("trade_want_items", [])
            def make_w(i=iid):
                return lambda: toggle_trade_item(i, "want")
            bw = min(98, small_font.size(short)[0] + 16)
            trade_buttons.append(Button(wx, wy2, bw, 22, short, make_w(), GOOD if sel else PANEL_BORDER))
            wx += bw + 4
            if wx > px + pw - 100:
                wx = px + 12
                wy2 += 26

        partner = state.get("trade_partner", "?")
        trade_buttons.append(Button(px + pw - 130, py + ph - 44, 118, 32, "SEND OFFER", send_trade_offer, ACCENT3))

    msg = state.get("trade_status_msg", "")
    if msg:
        draw_text(surf, msg[:55], small_font, ACCENT2, px + 12, py + ph - 72)

    for b in trade_buttons:
        b.update(pygame.mouse.get_pos())
        b.draw(surf, button_font)
    buttons.extend(trade_buttons)


# =============================================================================
# SOCIAL LAB WORLD — walk around and flex your character
# =============================================================================
def build_world_profile() -> dict:
    owned = get_owned()
    equipped = {k: v for k, v in get_equipped().items() if v in owned}
    breakdown = flex_rarity_breakdown(owned)
    gods = breakdown.get("god", 0)
    mythics = breakdown.get("mythic", 0)
    ultras = breakdown.get("ultra", 0)
    legendaries = breakdown.get("legendary", 0)
    last = save_data.get("last_build") or {}
    player = state.get("player_name") or save_data.get("player_name") or ""
    if is_lab_owner(player):
        title = "Lab Owner"
    elif gods >= 1:
        title = "God Tier"
    elif mythics >= 2:
        title = "Mythic Hunter"
    elif mythics >= 1:
        title = "Mythic Flex"
    elif ultras >= 2:
        title = "Ultra Collector"
    elif ultras >= 1:
        title = "Ultra Flex"
    elif legendaries >= 2:
        title = "Legendary Collector"
    elif legendaries >= 1:
        title = "Legendary Flex"
    elif len(owned) >= 10:
        title = "Style Pro"
    elif get_wallet() >= 100:
        title = "Credit Boss"
    else:
        title = "Lab Builder"
    return normalize_flex_profile({
        "avatar_name": get_avatar_name(),
        "equipped": equipped,
        "wallet": get_wallet(),
        "owned_count": len(owned),
        "legendary_count": legendaries,
        "ultra_count": ultras,
        "mythic_count": mythics,
        "god_count": gods,
        "owned_items": owned,
        "last_assistant": last.get("assistant_name", ""),
        "last_rating": last.get("rating", ""),
        "last_tags": last.get("tags", []),
        "flex_title": title,
    })


def enter_world():
    if not purchases_allowed() and save_data.get("integrity_violation"):
        state["world_message"] = "Enter the world after fixing save integrity."
        return
    name = state.get("player_name") or save_data.get("player_name")
    if not name:
        state["world_message"] = "Set your player name in a build first!"
        return
    if not chat_client.connected:
        chat_client.host = CHAT_HOST
        chat_client.port = CHAT_PORT
        if not chat_client.connect(name):
            state["world_message"] = chat_client.last_error or "Could not connect."
            return
    profile = build_world_profile()
    x, y = clamp_pos(state.get("world_x", 400), state.get("world_y", 320))
    state["world_x"], state["world_y"] = x, y
    ok, err = chat_client.send_world_join(profile, x, y)
    if not ok:
        state["world_message"] = err or "Could not join world."
        return
    state["screen"] = "world"
    state["world_in"] = True
    state["world_selected"] = ""
    state["world_message"] = "Walk with arrow keys — click players to inspect their flex!"
    set_avatar_message("That's you!")
    play_sound("ping")


def leave_world():
    chat_client.send_world_leave()
    state["world_in"] = False
    state["world_players"] = {}
    state["world_selected"] = ""
    state["screen"] = "welcome"
    state["world_message"] = ""
    set_avatar_message("")
    play_sound("back")


def world_flex_emote():
    chat_client.send_world_emote()
    state["world_message"] = "You flexed your lab gear!"
    play_sound("success")


def update_world_movement(dt):
    if state.get("screen") != "world":
        return
    keys = pygame.key.get_pressed()
    speed = 180 * dt
    mx = my = 0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        mx -= speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        mx += speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        my -= speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        my += speed
    if mx or my:
        nx, ny = clamp_pos(state.get("world_x", 400) + mx, state.get("world_y", 320) + my)
        state["world_x"], state["world_y"] = nx, ny
        state["world_move_cooldown"] -= dt
        if state["world_move_cooldown"] <= 0:
            chat_client.send_world_move(nx, ny)
            state["world_move_cooldown"] = 0.12


def _world_player_at_mouse(mx, my):
    """Return player name if click hits their avatar."""
    my_name = state.get("player_name") or save_data.get("player_name") or chat_client.player_name
    for pname, p in state.get("world_players", {}).items():
        px, py = p.get("x", 400), p.get("y", 320)
        if math.hypot(mx - px, my - (py - 40)) < 42:
            return pname
    if math.hypot(mx - state.get("world_x", 400), my - (state.get("world_y", 320) - 40)) < 42:
        return my_name
    return ""


def draw_world_flex_card(surf, player: dict, title: str):
    """Sidebar showing another player's flex profile."""
    sx = WIDTH - SIDEBAR_W - MARGIN
    sy = CONTENT_Y
    sh = MAIN_BOTTOM - CONTENT_Y
    draw_rounded_rect(surf, pygame.Rect(sx, sy, SIDEBAR_W, sh), PANEL_BG, radius=12, border=2, border_color=ACCENT3)
    draw_text(surf, "FLEX CARD", header_font, ACCENT3, sx + SIDEBAR_W // 2, sy + 14, center=True)
    draw_text(surf, title[:18], question_font, ACCENT2, sx + SIDEBAR_W // 2, sy + 38, center=True)
    draw_text(surf, player.get("flex_title", "Lab Builder"), small_font, TEXT_MUTED, sx + SIDEBAR_W // 2, sy + 58, center=True)

    draw_mentor_avatar(surf, sx + SIDEBAR_W // 2 - 40, sy + 68, 80, "proud",
                       player.get("wallet", 0), pygame.time.get_ticks() / 1000.0,
                       "", show_bubble=False,
                       equipped=player.get("equipped", {}),
                       avatar_name=player.get("avatar_name", "Mentor"))

    y = sy + 168
    draw_text(surf, f"Wallet: {player.get('wallet', 0)} CR", body_font, GOOD, sx + 12, y)
    y += 20
    stats = f"Items: {player.get('owned_count', 0)}  •  Leg: {player.get('legendary_count', 0)}"
    if player.get("ultra_count") or player.get("mythic_count") or player.get("god_count"):
        stats += (f"  Ult: {player.get('ultra_count', 0)}"
                  f"  Myt: {player.get('mythic_count', 0)}"
                  f"  God: {player.get('god_count', 0)}")
    draw_text(surf, stats, small_font, ACCENT, sx + 12, y)
    y += 22
    if player.get("last_assistant"):
        draw_text(surf, f"Assistant: {player['last_assistant'][:22]}", small_font, TEXT, sx + 12, y)
        y += 18
    if player.get("last_rating"):
        draw_text(surf, f"Rating: {player['last_rating']}", small_font, ACCENT2, sx + 12, y)
        y += 18
    tags = player.get("last_tags") or []
    if tags:
        draw_text(surf, f"Tags: {', '.join(tags[:4])}", small_font, TEXT_MUTED, sx + 12, y)
        y += 18

    y += 8
    draw_text(surf, "Equipped:", small_font, ACCENT2, sx + 12, y)
    y += 16
    for slot, iid in player.get("equipped", {}).items():
        item = COSMETIC_CATALOG.get(iid, {})
        rar = item.get("rarity", "common")
        rcol = RARITIES.get(rar, RARITIES["common"])["color"]
        draw_text(surf, f"  {item.get('name', iid)[:20]}", small_font, rcol, sx + 12, y)
        y += 14

    owned = player.get("owned_items") or []
    if owned:
        y += 6
        draw_text(surf, "Collection:", small_font, TEXT_MUTED, sx + 12, y)
        y += 14
        for iid in owned[:5]:
            item = COSMETIC_CATALOG.get(iid, {})
            draw_text(surf, f"  • {item.get('name', iid)[:18]}", small_font, TEXT, sx + 12, y)
            y += 13


def draw_world_screen(surf, t):
    draw_background(surf, t)
    draw_header(surf, "Social Lab World", t=t)

    floor = pygame.Rect(MARGIN, CONTENT_Y, WIDTH - SIDEBAR_W - MARGIN * 3, MAIN_BOTTOM - CONTENT_Y)
    draw_rounded_rect(surf, floor, (16, 22, 38), radius=14, border=2, border_color=ACCENT)
    draw_text(surf, "SOCIAL LAB — flex your mentor & cosmetics!", question_font, ACCENT2,
              floor.centerx, CONTENT_Y + 12, center=True)
    draw_text(surf, "Arrows/WASD move  •  Click player  •  F flex  •  ESC leave",
              small_font, TEXT_MUTED, floor.centerx, CONTENT_Y + 32, center=True)

    # Floor tiles
    for row in range(6):
        for col in range(10):
            tx = floor.x + 20 + col * 72
            ty = floor.y + 52 + row * 68
            col_shade = (22, 30, 50) if (row + col) % 2 == 0 else (18, 26, 44)
            pygame.draw.rect(surf, col_shade, (tx, ty, 68, 64), border_radius=4)

    my_name = state.get("player_name") or save_data.get("player_name") or chat_client.player_name
    world_buttons = []

    # Other players
    for pname, p in state.get("world_players", {}).items():
        px, py = p.get("x", 400), p.get("y", 320)
        emote = float(p.get("emote_until", 0)) > time.time()
        mood = "excited" if emote else "happy"
        msg = p.get("flex_title", "") if emote else ""
        draw_mentor_avatar(surf, px - 36, py - 70, 72, mood, p.get("wallet", 0), t,
                           msg, show_bubble=emote,
                           equipped=p.get("equipped", {}),
                           avatar_name=p.get("avatar_name", "Mentor"))
        draw_text(surf, pname[:14], small_font, ACCENT2, px, py + 8, center=True)
        if emote:
            pygame.draw.circle(surf, ACCENT3, (px, py - 80), 28, 2)

    # Local player (you)
    lx, ly = state.get("world_x", 400), state.get("world_y", 320)
    profile = build_world_profile()
    you_bubble = get_avatar_message()
    draw_mentor_avatar(surf, lx - 40, ly - 78, 80, "proud", profile["wallet"], t,
                       you_bubble, show_bubble=bool(you_bubble),
                       equipped=profile["equipped"],
                       avatar_name=profile["avatar_name"])
    draw_text(surf, f"{my_name} (you)"[:16], small_font, GOOD, lx, ly + 10, center=True)

    # Flex card for selected player
    sel = state.get("world_selected", "")
    if sel == my_name:
        draw_world_flex_card(surf, profile, my_name)
    elif sel and sel in state.get("world_players", {}):
        draw_world_flex_card(surf, state["world_players"][sel], sel)

    msg = state.get("world_message", "")
    if msg:
        draw_text(surf, msg[:60], small_font, ACCENT3, floor.centerx, MAIN_BOTTOM - 28, center=True)

    nav_y = ACTION_Y
    world_buttons.append(Button(MARGIN, nav_y, 100, BTN_H, "LEAVE", leave_world, BAD))
    world_buttons.append(Button(MARGIN + 108, nav_y, 90, BTN_H, "CHAT", toggle_chat, ACCENT2))
    world_buttons.append(Button(MARGIN + 206, nav_y, 90, BTN_H, "TRADE", toggle_trade, ACCENT3))
    world_buttons.append(Button(MARGIN + 304, nav_y, 100, BTN_H, "FLEX!", world_flex_emote, GOOD))

    for b in world_buttons:
        b.update(pygame.mouse.get_pos())
        b.draw(surf, button_font)
    buttons[:] = world_buttons

    draw_trade_panel(surf)
    draw_chat_panel(surf)


def draw_integrity_banner(surf):
    msg = state.get("integrity_warning") or save_data.get("integrity_message")
    if not msg:
        return
    banner_h = 30
    by = HDR_TOP + HDR_HEIGHT + 4
    draw_rounded_rect(surf, pygame.Rect(MARGIN, by, WIDTH - MARGIN * 2, banner_h),
                      (80, 35, 40), radius=6, border=2, border_color=BAD)
    draw_text(surf, msg[:90], small_font, WHITE, WIDTH // 2, by + 15, center=True)


def draw_filter_warning(surf):
    """Red banner when strict language filter detects bad words."""
    if not state.get("filter_message"):
        return
    alpha = min(1.0, state.get("filter_flash", 0) / 0.5) if state.get("filter_flash", 0) > 0 else 1.0
    banner_h = 34
    banner = pygame.Surface((WIDTH - MARGIN * 2, banner_h), pygame.SRCALPHA)
    col = (180, 50, 60, int(220 * alpha))
    banner.fill(col)
    surf.blit(banner, (MARGIN, FILTER_BANNER_Y))
    draw_rounded_rect(surf, pygame.Rect(MARGIN, FILTER_BANNER_Y, WIDTH - MARGIN * 2, banner_h),
                      (120, 40, 50), radius=6, border=2, border_color=BAD)
    draw_text(surf, state["filter_message"], small_font, WHITE, WIDTH // 2, FILTER_BANNER_Y + 17, center=True)


def draw_background(surf, t):
    surf.fill(DARK_BG)
    for i, (x1, y1, x2, y2) in enumerate(circuit_lines):
        alpha = 30 + int(15 * math.sin(t * 0.5 + i))
        col = (alpha, alpha + 20, alpha + 40)
        pygame.draw.line(surf, col, (x1, y1), (x2, y2), 1)
        pygame.draw.circle(surf, col, (x2, y2), 2)


# =============================================================================
# SCREEN DRAW FUNCTIONS
# =============================================================================
def draw_header(surf, subtitle="", t=0.0):
    draw_rounded_rect(surf, pygame.Rect(MARGIN, HDR_TOP, WIDTH - MARGIN * 2, HDR_HEIGHT),
                      PANEL_BG, radius=8, border=2, border_color=ACCENT)
    draw_text(surf, "BUILD YOUR OWN SMART ASSISTANT", title_font, ACCENT, WIDTH // 2, HDR_TOP + 16, center=True)
    if subtitle:
        draw_text(surf, subtitle, small_font, TEXT_MUTED, WIDTH // 2, HDR_TOP + 32, center=True)
    if state.get("player_name"):
        badge = f"{state['player_name'][:12]}"
        draw_text(surf, badge, small_font, ACCENT2, WIDTH - 168, HDR_TOP + 24, center=True)

    chat_lbl = "CHAT ON" if state.get("chat_open") else "CHAT"
    draw_text(surf, chat_lbl, small_font, ACCENT2 if state.get("chat_open") else TEXT_MUTED,
              WIDTH - MARGIN - 36, HDR_TOP + 24, center=True)

    if state["screen"] in ("welcome", "shop", "summary"):
        wallet = get_wallet()
        wcol = GOOD if wallet >= 30 else ACCENT3 if wallet >= 10 else TEXT_MUTED
        draw_rounded_rect(surf, pygame.Rect(MARGIN + 4, HDR_TOP + 6, 96, 28), (20, 26, 42), radius=6, border=2, border_color=ACCENT3)
        draw_text(surf, f"{wallet} CR", small_font, wcol, MARGIN + 52, HDR_TOP + 20, center=True)

    elif state["screen"] == "design":
        cred = state.get("credits", STARTING_CREDITS)
        cred_col = GOOD if cred >= STARTING_CREDITS else ACCENT3 if cred >= 25 else BAD
        draw_rounded_rect(surf, pygame.Rect(MARGIN + 4, HDR_TOP + 6, 88, 28), (20, 26, 42), radius=6, border=2, border_color=ACCENT3)
        draw_text(surf, f"{cred} CR", small_font, cred_col, MARGIN + 48, HDR_TOP + 20, center=True)
        if state.get("credit_flash", 0) > 0:
            delta = state.get("last_credit_delta", 0)
            if delta != 0:
                sign = "+" if delta > 0 else ""
                flash_col = GOOD if delta > 0 else BAD
                draw_text(surf, f"{sign}{delta}", small_font, flash_col, MARGIN + 100, HDR_TOP + 20, center=True)


def draw_welcome(surf, t):
    draw_background(surf, t)
    draw_header(surf, t=t)

    panel = pygame.Rect(MARGIN, CONTENT_Y, WIDTH - SIDEBAR_W - MARGIN * 3, MAIN_BOTTOM - CONTENT_Y)
    draw_rounded_rect(surf, panel, PANEL_BG, radius=12, border=2, border_color=ACCENT)

    draw_text(surf, "Welcome, Young Programmer!", header_font, ACCENT2, panel.centerx, CONTENT_Y + 22, center=True)

    lines = [
        "Inspired by Grace Hopper — inventor of the first compiler.",
        "Answer 7 design questions and watch your assistant come alive!",
        "Progress auto-saves to disk — wallet, shop, and builds.",
        "Learn functions, loops, and if/else — the same tools Grace used.",
    ]
    y = CONTENT_Y + 48
    for ln in lines:
        draw_text(surf, ln, body_font, TEXT, panel.centerx, y, center=True)
        y += 20

    last = save_data.get("last_build")
    if last:
        tags_hint = ""
        if last.get("tags"):
            tags_hint = f"  Tags: {', '.join(last['tags'][:3])}"
        hint = (
            f"Last build: {last.get('assistant_name', 'Assistant')} "
            f"({last.get('rating', '')}) — {last.get('date', '')}{tags_hint}"
        )
        draw_text(surf, hint, small_font, ACCENT3, panel.centerx, y + 4, center=True)

    for i in range(10):
        col = ACCENT if i % 3 == 0 else (50, 70, 100)
        pygame.draw.circle(surf, col, (panel.x + 24 + i * 12, MAIN_BOTTOM - 36), 3)

    mentor_x = WIDTH - SIDEBAR_W - MARGIN
    draw_mentor_avatar(surf, mentor_x, CONTENT_Y + 40, 78, "happy", get_wallet(), t,
                       f"I'm {get_avatar_name()}! Build to earn CR!",
                       show_bubble=True, equipped=get_equipped())

    welcome_buttons = []
    btn_y = ACTION_Y
    if has_saved_session():
        prog = save_data.get("in_progress", {})
        q_num = prog.get("current_q", 0) + 1 if prog.get("screen") == "design" else 0
        if prog.get("screen") == "tags":
            label = "CONTINUE TAGS"
        elif q_num:
            label = f"CONTINUE (Q{q_num})"
        else:
            label = "CONTINUE BUILD"
        cont_btn = Button(panel.centerx - 280, btn_y, 120, BTN_H, label, continue_build, ACCENT)
        new_btn = Button(panel.centerx - 148, btn_y, 100, BTN_H, "NEW", start_name, ACCENT2)
        shop_btn = Button(panel.centerx - 38, btn_y, 90, BTN_H, "SHOP", open_shop, ACCENT3)
        world_btn = Button(panel.centerx + 60, btn_y, 100, BTN_H, "WORLD", enter_world, GOOD)
        welcome_buttons = [cont_btn, new_btn, shop_btn, world_btn]
    else:
        new_btn = Button(panel.centerx - 220, btn_y, 148, BTN_H, "START BUILDING", start_name, ACCENT2)
        shop_btn = Button(panel.centerx - 58, btn_y, 148, BTN_H, "AVATAR SHOP", open_shop, ACCENT3)
        world_btn = Button(panel.centerx + 104, btn_y, 148, BTN_H, "SOCIAL LAB", enter_world, GOOD)
        welcome_buttons = [new_btn, shop_btn, world_btn]

    for b in welcome_buttons:
        b.update(pygame.mouse.get_pos())
        b.draw(surf, button_font)
    buttons[:] = welcome_buttons

    draw_text(surf, control_hints_line(), small_font, TEXT_MUTED, WIDTH // 2, FOOTER_TEXT_Y, center=True)


def draw_tags_screen(surf, t):
    """Step 8 — preset tags + custom tags (filter-checked)."""
    draw_background(surf, t)
    draw_header(surf, "Step 8 — Tag your assistant", t=t)

    left_w = 468
    left_h = MAIN_BOTTOM - CONTENT_Y
    left_x = MARGIN
    draw_rounded_rect(surf, pygame.Rect(left_x, CONTENT_Y, left_w, left_h), PANEL_BG, radius=10, border=2, border_color=ACCENT3)

    qx = left_x + 12
    draw_text(surf, "Add tags so people know what your assistant does!", question_font, ACCENT3, qx, CONTENT_Y + 10)
    draw_text(
        surf,
        f"Presets = FREE  •  Custom = {CUSTOM_TAG_COST} CR each  •  Max {MAX_TAGS_TOTAL} tags",
        small_font, TEXT_MUTED, qx, CONTENT_Y + 32,
    )

    tag_buttons = []
    col_w, row_h = 108, 30
    tx, ty = qx, CONTENT_Y + 52
    for i, tag in enumerate(PRESET_TAGS):
        selected = tag["id"] in state.get("selected_tags", [])
        col = tag["color"] if selected else PANEL_BORDER
        def make_toggle(tid=tag["id"]):
            return lambda: toggle_preset_tag(tid)
        btn = Button(tx, ty, col_w, row_h, tag["label"][:11], make_toggle(), col)
        tag_buttons.append(btn)
        tx += col_w + 6
        if (i + 1) % 4 == 0:
            tx = qx
            ty += row_h + 5

    lib_y = ty + 8
    library = save_data.get("custom_tag_library", [])
    if library:
        draw_text(surf, f"Your saved custom tags ({CUSTOM_TAG_COST} CR each):", small_font, ACCENT2, qx, lib_y)
        lx, ly = qx, lib_y + 16
        for label in library[:6]:
            def make_lib(lbl=label):
                return lambda: add_library_tag(lbl)
            short = label[:12]
            bw = min(100, small_font.size(short)[0] + 20)
            tag_buttons.append(Button(lx, ly, bw, BTN_SM, short, make_lib(), ACCENT))
            lx += bw + 5
            if lx > left_x + left_w - 100:
                lx = qx
                ly += BTN_SM + 4
        lib_y = ly + BTN_SM + 10

    custom_y = max(lib_y + 4, CONTENT_Y + 200)
    draw_text(surf, "New custom tag:", small_font, TEXT_MUTED, qx, custom_y)
    box = pygame.Rect(qx, custom_y + 16, left_w - 120, 32)
    active = state.get("input_active", True)
    tag_dirty = state.get("tag_input", "")
    box_col = BAD if tag_dirty and contains_profanity(tag_dirty) else (ACCENT if active else PANEL_BORDER)
    draw_rounded_rect(surf, box, (16, 22, 38), radius=6, border=2, border_color=box_col)
    draw_text(surf, tag_dirty or "e.g. Puzzle Pal, Pet Care...", body_font,
              TEXT if tag_dirty else TEXT_MUTED, qx + 8, custom_y + 32)

    if active and (pygame.time.get_ticks() // 450) % 2 == 0:
        tw = body_font.size(tag_dirty)[0]
        pygame.draw.line(surf, ACCENT, (qx + 8 + tw + 2, custom_y + 22), (qx + 8 + tw + 2, custom_y + 42), 2)

    can_add = bool(tag_dirty.strip()) and validate_tag(tag_dirty)[0] and can_afford_custom_tag()
    add_label = f"ADD -{CUSTOM_TAG_COST}" if can_afford_custom_tag() else "NO CR"
    add_btn = Button(left_x + left_w - 100, custom_y + 16, 88, 32, add_label, add_custom_tag_from_input, GOOD)
    add_btn.enabled = can_add
    tag_buttons.append(add_btn)

    sel_y = custom_y + 58
    draw_text(surf, f"Selected ({get_total_tag_count()}/{MAX_TAGS_TOTAL}):", small_font, ACCENT2, qx, sel_y)
    labels = get_display_tags()
    if labels:
        draw_text(surf, ", ".join(labels), body_font, TEXT, qx, sel_y + 18)
    else:
        draw_text(surf, "(none yet — pick at least one!)", small_font, TEXT_MUTED, qx, sel_y + 18)

    draw_text(
        surf,
        f"Custom tags cost {CUSTOM_TAG_COST} CR + friendly filter. Presets are free! :D",
        small_font, TEXT_MUTED, qx, sel_y + 42,
    )

    draw_mentor_avatar(surf, qx, CONTENT_Y + left_h - 118, 64, "happy",
                       state.get("credits", STARTING_CREDITS), t,
                       get_avatar_message(), show_bubble=True,
                       equipped=get_equipped())

    nav_y = MAIN_BOTTOM - BTN_H - 6
    back_btn = Button(qx, nav_y, 96, BTN_H, "BACK", go_back_from_tags, ACCENT3)
    finish_btn = Button(left_x + left_w - 128, nav_y, 116, BTN_H, "FINISH", submit_tags_and_finish, ACCENT2)
    finish_btn.enabled = get_total_tag_count() >= 1

    preview_answers = dict(state.get("answers", {}))
    preview_answers["preset_tags"] = list(state.get("selected_tags", []))
    preview_answers["custom_tags"] = list(state.get("custom_tags", []))

    right_x = left_x + left_w + MARGIN
    right_w = WIDTH - right_x - MARGIN
    draw_assistant_preview(surf, right_x, CONTENT_Y, right_w, left_h, preview_answers, t)

    for b in tag_buttons + [back_btn, finish_btn]:
        b.update(pygame.mouse.get_pos())
        b.draw(surf, button_font)
    buttons[:] = tag_buttons + [back_btn, finish_btn]
    draw_filter_warning(surf)


def draw_name_screen(surf, t):
    draw_background(surf, t)
    draw_header(surf, "Step 1 — Your name", t=t)

    panel = pygame.Rect(WIDTH // 2 - 260, CONTENT_Y + 10, 520, 280)
    draw_rounded_rect(surf, panel, PANEL_BG, radius=12, border=2, border_color=ACCENT)
    draw_text(surf, "What is your name?", question_font, TEXT, WIDTH // 2, CONTENT_Y + 42, center=True)
    draw_text(surf, "Grace Hopper started at 37 — it's never too late!", small_font, TEXT_MUTED, WIDTH // 2, CONTENT_Y + 64, center=True)

    box = pygame.Rect(WIDTH // 2 - 200, CONTENT_Y + 100, 400, 44)
    active = state["input_active"]
    draw_rounded_rect(surf, box, (18, 24, 40), radius=8, border=2, border_color=ACCENT if active else PANEL_BORDER)

    txt = state["current_input"] or "Type your name..."
    col = TEXT if state["current_input"] else TEXT_MUTED
    draw_text(surf, txt, name_font, col, WIDTH // 2, CONTENT_Y + 122, center=True)

    if active and (pygame.time.get_ticks() // 450) % 2 == 0:
        tw = name_font.size(state["current_input"])[0]
        pygame.draw.line(surf, ACCENT, (WIDTH // 2 + tw // 2 + 4, CONTENT_Y + 108),
                         (WIDTH // 2 + tw // 2 + 4, CONTENT_Y + 136), 2)

    draw_text(surf, "ENTER to continue", small_font, TEXT_MUTED, WIDTH // 2, CONTENT_Y + 162, center=True)

    typed = state["current_input"].strip()
    can_go = bool(typed) and not contains_profanity(typed)
    btn = Button(WIDTH // 2 - 80, CONTENT_Y + 200, 160, BTN_H, "CONTINUE", submit_name, ACCENT2)
    btn.enabled = can_go
    btn.update(pygame.mouse.get_pos())
    btn.draw(surf, button_font)
    buttons[:] = [btn]
    draw_filter_warning(surf)


def draw_avatar_name_screen(surf, t):
    """Step 2 — give the credit mentor avatar a custom name."""
    draw_background(surf, t)
    draw_header(surf, "Step 2 — Avatar name", t=t)

    panel = pygame.Rect(WIDTH // 2 - 280, CONTENT_Y + 6, 560, 300)
    draw_rounded_rect(surf, panel, PANEL_BG, radius=12, border=2, border_color=ACCENT2)
    draw_text(surf, "Name your mentor avatar", question_font, TEXT, WIDTH // 2, CONTENT_Y + 36, center=True)
    draw_text(surf, "Awards credits and wears your shop cosmetics.", small_font, TEXT_MUTED, WIDTH // 2, CONTENT_Y + 58, center=True)

    draw_mentor_avatar(surf, WIDTH // 2 - 42, CONTENT_Y + 72, 84, "happy", get_wallet(), t,
                       equipped=get_equipped(), show_bubble=False)

    box = pygame.Rect(WIDTH // 2 - 180, CONTENT_Y + 200, 360, 40)
    active = state["input_active"]
    draw_rounded_rect(surf, box, (18, 24, 40), radius=8, border=2, border_color=ACCENT2 if active else PANEL_BORDER)

    txt = state["current_input"] or "e.g. Professor Byte, Coach Nova..."
    col = TEXT if state["current_input"] else TEXT_MUTED
    draw_text(surf, txt, name_font, col, WIDTH // 2, CONTENT_Y + 220, center=True)

    if active and (pygame.time.get_ticks() // 450) % 2 == 0:
        tw = name_font.size(state["current_input"])[0]
        pygame.draw.line(surf, ACCENT2, (WIDTH // 2 + tw // 2 + 4, CONTENT_Y + 206),
                         (WIDTH // 2 + tw // 2 + 4, CONTENT_Y + 234), 2)

    draw_text(surf, "Rename anytime in the Avatar Shop", small_font, TEXT_MUTED, WIDTH // 2, CONTENT_Y + 256, center=True)

    typed = state["current_input"].strip()
    can_go = bool(typed) and not contains_profanity(typed)
    btn = Button(WIDTH // 2 - 84, CONTENT_Y + 278, 168, BTN_H, "SAVE & BUILD", submit_avatar_name, ACCENT2)
    btn.enabled = can_go
    btn.update(pygame.mouse.get_pos())
    btn.draw(surf, button_font)
    buttons[:] = [btn]
    draw_filter_warning(surf)


def draw_design_screen(surf, t):
    draw_background(surf, t)
    q_idx = state["current_q"]
    q = DESIGN_QUESTIONS[q_idx]
    total = len(DESIGN_QUESTIONS)

    draw_header(surf, f"Question {q_idx + 1}/{total}", t=t)

    left_w = 468
    left_h = MAIN_BOTTOM - CONTENT_Y
    left_x = MARGIN
    draw_rounded_rect(surf, pygame.Rect(left_x, CONTENT_Y, left_w, left_h), PANEL_BG, radius=10, border=2, border_color=PANEL_BORDER)

    # Fixed zones — hint length can't push other UI around
    qx = left_x + 12
    draw_text(surf, q["text"], question_font, ACCENT, qx, CONTENT_Y + 12)
    hint_lines = wrap_text(q["hint"], small_font, left_w - 28)[:2]
    hy = CONTENT_Y + 36
    for hl in hint_lines:
        draw_text(surf, f"Tip: {hl}", small_font, TEXT_MUTED, qx, hy)
        hy += 15

    input_y = CONTENT_Y + 78
    box = pygame.Rect(qx, input_y, left_w - 24, 44)
    active = state["input_active"]
    draw_rounded_rect(surf, box, (16, 22, 38), radius=6, border=2, border_color=ACCENT if active else PANEL_BORDER)

    display = state["current_input"] or "Type your answer..."
    col = TEXT if state["current_input"] else TEXT_MUTED
    draw_text(surf, display, body_font, col, qx + 10, input_y + 22)

    if active and (pygame.time.get_ticks() // 480) % 2 == 0:
        tw = body_font.size(state["current_input"])[0]
        pygame.draw.line(surf, ACCENT, (qx + 10 + tw + 2, input_y + 8), (qx + 10 + tw + 2, input_y + 36), 2)

    draw_text(surf, "ENTER to save", small_font, TEXT_MUTED, qx, input_y + 52)

    if state["current_input"].strip():
        preview_answers = dict(state["answers"])
        preview_answers[q["id"]] = state["current_input"].strip()
    else:
        preview_answers = state["answers"]

    meters_y = CONTENT_Y + 188
    draw_category_meters(surf, qx, meters_y, calculate_category_scores(preview_answers))

    mentor_y = CONTENT_Y + 262
    draw_mentor_avatar(surf, qx, mentor_y, 68, state.get("avatar_mood", "neutral"),
                       state.get("credits", STARTING_CREDITS), t,
                       get_avatar_message(), show_bubble=True,
                       equipped=get_equipped())

    nav_y = MAIN_BOTTOM - BTN_H - 6
    back_btn = Button(qx, nav_y, 96, BTN_H, "BACK", go_back_question, ACCENT3)
    back_btn.enabled = q_idx > 0

    if q_idx == total - 1:
        next_label = "TAGS"
        next_action = go_to_tags_screen
    else:
        next_label = "NEXT"
        next_action = advance_question

    next_btn = Button(left_x + left_w - 108, nav_y, 96, BTN_H, next_label, next_action, ACCENT2)
    typed = state["current_input"].strip()
    has_answer = bool(typed) or bool(get_answer(q["id"]))
    text_clean = not typed or not contains_profanity(typed)
    next_btn.enabled = has_answer and text_clean

    back_btn.update(pygame.mouse.get_pos())
    next_btn.update(pygame.mouse.get_pos())
    back_btn.draw(surf, button_font)
    next_btn.draw(surf, button_font)
    buttons[:] = [back_btn, next_btn]

    right_x = left_x + left_w + MARGIN
    right_w = WIDTH - right_x - MARGIN
    draw_assistant_preview(surf, right_x, CONTENT_Y, right_w, left_h, preview_answers, t)

    dot_y = CONTENT_Y + left_h - 14
    for i in range(total):
        dx = right_x + 20 + i * 22
        col = ACCENT2 if i <= q_idx else (70, 85, 110)
        pygame.draw.circle(surf, col, (dx, dot_y), 4)
        if i == q_idx:
            pygame.draw.circle(surf, WHITE, (dx, dot_y), 2)

    draw_text(surf, "Preview updates live →", small_font, TEXT_MUTED, WIDTH // 2, FOOTER_TEXT_Y, center=True)
    draw_filter_warning(surf)


def draw_summary_screen(surf, t):
    draw_background(surf, t)
    draw_header(surf, "Blueprint & Credits", t=t)

    score = state["score_data"]
    if not score:
        return

    total = score["total"]
    max_score = score["max"]
    rating = score["rating"]
    message = score["message"]
    answers_list = score["answers_list"]
    assistant_name = get_answer("name", "Your Assistant")

    strip_h = 48
    draw_rounded_rect(surf, pygame.Rect(MARGIN, CONTENT_Y, WIDTH - MARGIN * 2, strip_h),
                      PANEL_BG, radius=10, border=2, border_color=ACCENT)
    draw_text(surf, f"{total}/{max_score}  •  {rating}", header_font, ACCENT2, WIDTH // 2, CONTENT_Y + 16, center=True)
    bar_x, bar_w = MARGIN + 40, WIDTH - MARGIN * 2 - 80
    bar_y = CONTENT_Y + 32
    pygame.draw.rect(surf, (30, 38, 58), (bar_x, bar_y, bar_w, 8), border_radius=4)
    fill_w = int(bar_w * (total / max(max_score, 1)))
    bar_col = GOOD if total >= max_score * 0.65 else ACCENT3 if total >= max_score * 0.40 else BAD
    if fill_w > 0:
        pygame.draw.rect(surf, bar_col, (bar_x, bar_y, fill_w, 8), border_radius=4)

    panel_y = CONTENT_Y + strip_h + 8
    panel_h = MAIN_BOTTOM - panel_y
    col_w = (WIDTH - MARGIN * 4) // 3

    spec_rect = pygame.Rect(MARGIN, panel_y, col_w, panel_h)
    draw_rounded_rect(surf, spec_rect, PANEL_BG, radius=10, border=2, border_color=PANEL_BORDER)
    draw_text(surf, "SPECS", header_font, ACCENT, spec_rect.x + 12, panel_y + 12)

    clip = pygame.Rect(spec_rect.x + 8, panel_y + 32, col_w - 16, panel_h - 40)
    surf.set_clip(clip)
    y = panel_y + 38 - state["scroll_offset"]
    for entry in answers_list:
        label = LABELS.get(entry["key"], entry["key"].title())
        draw_text(surf, f"{label}:", small_font, ACCENT3, spec_rect.x + 10, y)
        y += 14
        for line in wrap_text(entry["answer"], body_font, col_w - 28):
            draw_text(surf, line, body_font, TEXT, spec_rect.x + 14, y)
            y += 16
        y += 6
    surf.set_clip(None)

    credit_data = {
        "final_credits": score.get("final_credits", state["credits"]),
        "net_change": score.get("net_change", 0),
        "category_scores": score.get("category_scores", {}),
        "log": score.get("log", []),
        "synergy_bonus": score.get("synergy_bonus", 0),
        "synergy_message": score.get("synergy_message", ""),
        "mentor_closing": score.get("mentor_closing", ""),
    }
    cred_x = MARGIN * 2 + col_w
    draw_credits_panel(surf, cred_x, panel_y, col_w, panel_h, credit_data)

    prev_x = MARGIN * 3 + col_w * 2
    state["boot_anim"] = min(1.0, state["boot_anim"] + 0.016)
    booted = state["boot_anim"] > 0.3
    prev_h = int(panel_h * 0.62)
    draw_assistant_preview(surf, prev_x, panel_y, col_w, prev_h, state["answers"], t, booted=booted)

    notes_y = panel_y + prev_h + 6
    notes_h = panel_h - prev_h - 6
    draw_rounded_rect(surf, pygame.Rect(prev_x, notes_y, col_w, notes_h), (20, 28, 48), radius=8, border=2, border_color=ACCENT2)
    draw_text(surf, "Notes:", small_font, ACCENT2, prev_x + 10, notes_y + 8)
    for i, line in enumerate(wrap_text(message, small_font, col_w - 20)[:2]):
        draw_text(surf, line, small_font, TEXT, prev_x + 10, notes_y + 24 + i * 14)

    draw_text(surf, f"{assistant_name} ready!", small_font, ACCENT2, prev_x + col_w // 2, notes_y + notes_h - 22, center=True)

    if booted and random.random() < 0.05:
        spawn_particles(prev_x + col_w // 2, panel_y + prev_h // 2, count=2, color=(120, 220, 255))

    new_btn = Button(MARGIN, ACTION_Y, 130, BTN_H, "BUILD AGAIN", lambda: (reset_game(), start_name()), ACCENT2)
    shop_btn = Button(MARGIN + 140, ACTION_Y, 130, BTN_H, "SHOP", open_shop, ACCENT3)
    boot_btn = Button(WIDTH // 2 - 65, ACTION_Y, 130, BTN_H, "BOOT UP!",
                      lambda: (play_sound("boot"), spawn_particles(prev_x + col_w // 2, panel_y + prev_h // 2, count=16)), ACCENT3)

    new_btn.update(pygame.mouse.get_pos())
    shop_btn.update(pygame.mouse.get_pos())
    boot_btn.update(pygame.mouse.get_pos())
    new_btn.draw(surf, button_font)
    shop_btn.draw(surf, button_font)
    boot_btn.draw(surf, button_font)
    buttons[:] = [new_btn, shop_btn, boot_btn]

    draw_particles(surf)
    draw_text(surf, "UP/DOWN scroll  •  ESC quit", small_font, TEXT_MUTED, WIDTH // 2, FOOTER_TEXT_Y, center=True)


# =============================================================================
# MAIN LOOP
# =============================================================================
def main():
    global buttons
    init_sounds()
    load_save()
    apply_display_mode(get_settings().get("fullscreen", False))
    chat_client.host = CHAT_HOST
    chat_client.port = CHAT_PORT
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        t = pygame.time.get_ticks() / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                persist_session()
                write_save()
                running = False

            if event.type == pygame.KEYDOWN:
                binds = get_settings().get("keybinds", DEFAULT_KEYBINDS)
                if event.key == pygame.K_ESCAPE:
                    if state.get("settings_open"):
                        if state.get("settings_rebind"):
                            state["settings_rebind"] = ""
                            state["settings_status"] = "Rebind cancelled."
                        else:
                            state["settings_open"] = False
                    elif state.get("screen") == "world":
                        leave_world()
                    elif state.get("chat_open"):
                        state["chat_open"] = False
                        state["chat_input_active"] = False
                    else:
                        persist_session()
                        write_save()
                        disconnect_chat()
                        running = False
                elif state.get("settings_open") and handle_settings_key(event):
                    pass
                elif state.get("chat_open") and handle_chat_key(event):
                    pass
                elif keybind_matches(event, "fullscreen", binds):
                    toggle_fullscreen()
                elif keybind_matches(event, "settings", binds):
                    toggle_settings()
                elif keybind_matches(event, "chat", binds):
                    toggle_chat()
                elif keybind_matches(event, "trade", binds):
                    toggle_trade()
                elif keybind_matches(event, "world", binds) and state["screen"] == "welcome":
                    enter_world()
                elif keybind_matches(event, "flex", binds) and state["screen"] == "world":
                    world_flex_emote()
                elif keybind_matches(event, "build", binds) and state["screen"] == "welcome":
                    continue_build() if has_saved_session() else start_name()
                elif event.key == pygame.K_UP and state["screen"] == "summary":
                    state["scroll_offset"] = max(0, state["scroll_offset"] - 24)
                elif event.key == pygame.K_DOWN and state["screen"] == "summary":
                    state["scroll_offset"] += 24
                elif event.key == pygame.K_UP and state["screen"] == "shop" and state.get("shop_tab") == "crates":
                    state["crate_drop_scroll"] = max(0, state.get("crate_drop_scroll", 0) - 20)
                elif event.key == pygame.K_DOWN and state["screen"] == "shop" and state.get("shop_tab") == "crates":
                    state["crate_drop_scroll"] = state.get("crate_drop_scroll", 0) + 20
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and state["screen"] == "crate_reveal":
                    if state.get("crate_reveal_anim", 0) > 0.7:
                        state["screen"] = "shop"
                elif state["screen"] in ("name", "avatar_name", "design", "tags"):
                    handle_text_input(event)
                elif state["screen"] == "shop" and state.get("shop_avatar_input_active"):
                    handle_text_input(event)

            for b in list(buttons):
                b.handle(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state["screen"] == "world":
                if not state.get("chat_open") and not state.get("trade_open"):
                    hit = _world_player_at_mouse(*event.pos)
                    if hit:
                        state["world_selected"] = hit
                        play_sound("click")

        sync_save_from_disk()
        process_chat_events()
        update_world_movement(dt)
        update_particles(dt)
        if state.get("credit_flash", 0) > 0:
            state["credit_flash"] = max(0.0, state["credit_flash"] - dt)
        if state.get("filter_flash", 0) > 0:
            state["filter_flash"] = max(0.0, state["filter_flash"] - dt)
            if state["filter_flash"] <= 0:
                state["filter_message"] = ""
        buttons = []

        if state["screen"] == "welcome":
            draw_welcome(screen, t)
        elif state["screen"] == "name":
            draw_name_screen(screen, t)
        elif state["screen"] == "avatar_name":
            draw_avatar_name_screen(screen, t)
        elif state["screen"] == "design":
            draw_design_screen(screen, t)
        elif state["screen"] == "tags":
            draw_tags_screen(screen, t)
        elif state["screen"] == "summary":
            draw_summary_screen(screen, t)
        elif state["screen"] == "shop":
            draw_shop_screen(screen, t)
        elif state["screen"] == "crate_reveal":
            draw_crate_reveal_screen(screen, t)
        elif state["screen"] == "world":
            draw_world_screen(screen, t)
        else:
            screen.fill(DARK_BG)

        if state["screen"] != "world":
            draw_integrity_banner(screen)
        draw_trade_panel(screen)
        draw_chat_panel(screen)
        draw_settings_panel(screen)
        if state.get("chat_open"):
            draw_filter_warning(screen)

        set_btn = Button(WIDTH - MARGIN - 118, HDR_TOP + 6, 56, 30, "SET", toggle_settings,
                         ACCENT2 if state.get("settings_open") else PANEL_BORDER)
        set_btn.update(mouse_pos)
        set_btn.draw(screen, button_font)
        buttons.append(set_btn)

        chat_col = ACCENT2 if state.get("chat_open") else ACCENT3
        chat_lbl = "CHAT*" if state.get("chat_open") else "CHAT"
        chat_hdr_btn = Button(WIDTH - MARGIN - 56, HDR_TOP + 6, 52, 30, chat_lbl, toggle_chat, chat_col)
        chat_hdr_btn.update(mouse_pos)
        chat_hdr_btn.draw(screen, button_font)
        buttons.append(chat_hdr_btn)

        if state.get("settings_open"):
            spanel = pygame.Rect((WIDTH - 520) // 2, (HEIGHT - 500) // 2, 520, 500)
            buttons = [b for b in buttons if spanel.colliderect(b.rect) or b.rect.colliderect(
                pygame.Rect(WIDTH - MARGIN - 118, HDR_TOP + 6, 56, 30))]

        pygame.display.flip()

    disconnect_chat()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()