"""
Shared data + save helpers for Build Your Own Smart Assistant.

Used by the main game and the admin panel so both read/write the same save file.
"""

from __future__ import annotations

import json
import os
import random

SAVE_VERSION = 5
SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assistant_lab_save.json")
PENDING_GRANTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assistant_lab_pending_grants.json",
)
CHAT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "assistant_lab_chat_log.json",
)
def get_admin_server_pin() -> str:
    """Owner-only. Set ASSISTANT_LAB_ADMIN_PIN when hosting; empty = admin disabled."""
    return os.environ.get("ASSISTANT_LAB_ADMIN_PIN", "").strip()
DAILY_SHOP_SIZE = 5
STARTING_CREDITS = 50

# Lab owner — custom join announcements in chat + Social Lab world
LAB_OWNER_DISPLAY_NAME = "Owen"
LAB_OWNER_NAME_KEYS = frozenset({"owen", "(owner)owen"})

RARITIES = {
    "common":    {"label": "Common",    "color": (170, 180, 200), "refund": 5},
    "uncommon":  {"label": "Uncommon",  "color": (100, 210, 130), "refund": 8},
    "rare":      {"label": "Rare",      "color": (90, 170, 255),  "refund": 12},
    "epic":      {"label": "Epic",      "color": (190, 110, 255), "refund": 20},
    "legendary": {"label": "Legendary", "color": (255, 190, 70),  "refund": 35},
    "ultra":     {"label": "Ultra",     "color": (60, 240, 255),  "refund": 45},
    "mythic":    {"label": "Mythic",    "color": (255, 90, 140),  "refund": 60},
    "god":       {"label": "God",       "color": (255, 245, 120), "refund": 90},
}

CRATE_TYPES = {
    "code_crate": {
        "name": "Code Crate",
        "price": 20,
        "color": (100, 200, 255),
        "desc": "Starter crate — Common heavy. Ultra, Mythic & God are insanely rare!",
        "odds": [
            ("god", 1), ("mythic", 1), ("ultra", 2), ("legendary", 2), ("epic", 5),
            ("rare", 16), ("uncommon", 31), ("common", 42),
        ],
    },
    "circuit_crate": {
        "name": "Circuit Crate",
        "price": 45,
        "color": (190, 110, 255),
        "desc": "Better Rare & Epic odds — Ultra, Mythic & God still brutal to pull.",
        "odds": [
            ("god", 1), ("mythic", 2), ("ultra", 3), ("legendary", 3), ("epic", 10),
            ("rare", 24), ("uncommon", 27), ("common", 30),
        ],
    },
    "hopper_crate": {
        "name": "Hopper Crate",
        "price": 150,
        "color": (255, 190, 70),
        "desc": "Premium crate — 150 CR! Best Ultra, Mythic & God odds, but still rare.",
        "odds": [
            ("god", 4), ("mythic", 6), ("ultra", 8), ("legendary", 10), ("epic", 17),
            ("rare", 28), ("uncommon", 18), ("common", 9),
        ],
    },
}

COSMETIC_CATALOG = {
    "hat_gray":      {"name": "Gray Cap",         "slot": "hat",      "price": 12, "rarity": "common",    "hat_color": (120, 125, 135)},
    "tie_plain":     {"name": "Plain Tie",        "slot": "tie",      "price": 10, "rarity": "common",    "tie_color": (100, 105, 115)},
    "badge_starter": {"name": "Starter Pin",      "slot": "badge",    "price": 14, "rarity": "common",    "badge_color": (130, 135, 145)},
    "hat_cyan":      {"name": "Cyan Cap",         "slot": "hat",      "price": 25, "rarity": "common",    "hat_color": (80, 220, 255)},
    "hat_pink":      {"name": "Pink Bow",         "slot": "hat",      "price": 28, "rarity": "common",    "hat_color": (255, 120, 180)},
    "tie_ruby":      {"name": "Ruby Tie",         "slot": "tie",      "price": 18, "rarity": "common",    "tie_color": (200, 50, 70)},
    "tie_emerald":   {"name": "Emerald Tie",      "slot": "tie",      "price": 18, "rarity": "common",    "tie_color": (40, 170, 100)},
    "glasses_clear": {"name": "Clear Frames",     "slot": "glasses",  "price": 16, "rarity": "common",    "frame_color": (200, 210, 220)},
    "badge_lab":     {"name": "Lab Pin",          "slot": "badge",    "price": 15, "rarity": "common",    "badge_color": (90, 160, 220)},
    "glasses_neon":  {"name": "Neon Frames",      "slot": "glasses",  "price": 24, "rarity": "uncommon",  "frame_color": (120, 255, 200)},
    "coat_mint":     {"name": "Mint Lab Coat",    "slot": "coat",     "price": 32, "rarity": "uncommon",  "coat_color": (170, 245, 210)},
    "hair_auburn":   {"name": "Auburn Hair",      "slot": "hair",     "price": 28, "rarity": "uncommon",  "hair_color": (150, 75, 45)},
    "badge_code":    {"name": "Code Pin",         "slot": "badge",    "price": 26, "rarity": "uncommon",  "badge_color": (255, 170, 90)},
    "tie_cobalt":    {"name": "Cobalt Tie",       "slot": "tie",      "price": 22, "rarity": "uncommon",  "tie_color": (50, 100, 200)},
    "hat_striped":   {"name": "Striped Cap",      "slot": "hat",      "price": 24, "rarity": "uncommon",  "hat_color": (220, 80, 100)},
    "hat_gold":      {"name": "Gold Beret",       "slot": "hat",      "price": 30, "rarity": "rare",      "hat_color": (255, 200, 60)},
    "coat_rose":     {"name": "Rose Lab Coat",    "slot": "coat",     "price": 35, "rarity": "rare",      "coat_color": (255, 190, 210)},
    "coat_midnight": {"name": "Midnight Coat",    "slot": "coat",     "price": 35, "rarity": "rare",      "coat_color": (45, 55, 95)},
    "hair_silver":   {"name": "Silver Hair",      "slot": "hair",     "price": 30, "rarity": "rare",      "hair_color": (190, 195, 210)},
    "glasses_aviator":{"name": "Aviator Frames",  "slot": "glasses",  "price": 26, "rarity": "rare",      "frame_color": (180, 150, 90)},
    "tie_striped":   {"name": "Striped Tie",      "slot": "tie",      "price": 24, "rarity": "rare",      "tie_color": (70, 90, 160)},
    "glasses_star":  {"name": "Star Frames",      "slot": "glasses",  "price": 22, "rarity": "epic",      "frame_color": (255, 230, 80)},
    "badge_hopper":  {"name": "Hopper Badge",     "slot": "badge",    "price": 40, "rarity": "epic",      "badge_color": (100, 200, 255)},
    "aura_glow":     {"name": "Glow Aura",        "slot": "aura",     "price": 45, "rarity": "epic",      "aura_color": (120, 200, 255)},
    "coat_golden":   {"name": "Golden Coat",      "slot": "coat",     "price": 55, "rarity": "epic",      "crate_only": True, "coat_color": (255, 215, 100)},
    "glasses_holo":  {"name": "Holo Frames",      "slot": "glasses",  "price": 50, "rarity": "epic",      "crate_only": True, "frame_color": (180, 100, 255)},
    "hair_crimson":  {"name": "Crimson Hair",     "slot": "hair",     "price": 48, "rarity": "epic",      "crate_only": True, "hair_color": (180, 40, 60)},
    "badge_quantum": {"name": "Quantum Pin",      "slot": "badge",    "price": 52, "rarity": "epic",      "crate_only": True, "badge_color": (140, 80, 255)},
    "hat_crown":     {"name": "Compiler Crown",   "slot": "hat",      "price": 70, "rarity": "legendary", "crate_only": True, "hat_color": (255, 220, 80)},
    "aura_rainbow":  {"name": "Rainbow Aura",     "slot": "aura",     "price": 75, "rarity": "legendary", "crate_only": True, "aura_color": (255, 120, 200)},
    "badge_compiler":{"name": "Compiler Medal",  "slot": "badge",    "price": 65, "rarity": "legendary", "crate_only": True, "badge_color": (255, 200, 60)},
    "tie_galaxy":    {"name": "Galaxy Tie",       "slot": "tie",      "price": 60, "rarity": "legendary", "crate_only": True, "tie_color": (80, 60, 180)},
    "glasses_solar": {"name": "Solar Frames",     "slot": "glasses",  "price": 68, "rarity": "legendary", "crate_only": True, "frame_color": (255, 180, 50)},
    "hair_golden":   {"name": "Golden Hair",      "slot": "hair",     "price": 72, "rarity": "legendary", "crate_only": True, "hair_color": (230, 190, 70)},
    "aura_ultra":    {"name": "Ultra Pulse Aura", "slot": "aura",     "price": 80, "rarity": "ultra",     "crate_only": True, "aura_color": (50, 230, 255)},
    "hat_ultra":     {"name": "Ultra Visor",      "slot": "hat",      "price": 82, "rarity": "ultra",     "crate_only": True, "hat_color": (40, 200, 240)},
    "coat_ultra":    {"name": "Ultra Lab Coat",   "slot": "coat",     "price": 84, "rarity": "ultra",     "crate_only": True, "coat_color": (30, 180, 220)},
    "tie_ultra":     {"name": "Ultra Neon Tie",   "slot": "tie",      "price": 78, "rarity": "ultra",     "crate_only": True, "tie_color": (20, 220, 200)},
    "badge_ultra":   {"name": "Ultra Core Pin",   "slot": "badge",    "price": 86, "rarity": "ultra",     "crate_only": True, "badge_color": (80, 240, 255)},
    "aura_flame":    {"name": "Flame Aura",       "slot": "aura",     "price": 88, "rarity": "mythic",    "crate_only": True, "aura_color": (255, 100, 50)},
    "hat_phoenix":   {"name": "Phoenix Crown",    "slot": "hat",      "price": 90, "rarity": "mythic",    "crate_only": True, "hat_color": (255, 80, 60)},
    "coat_void":     {"name": "Void Lab Coat",    "slot": "coat",     "price": 88, "rarity": "mythic",    "crate_only": True, "coat_color": (30, 20, 50)},
    "glasses_mythic":{"name": "Mythic Prism",     "slot": "glasses",  "price": 92, "rarity": "mythic",    "crate_only": True, "frame_color": (255, 60, 120)},
    "tie_mythic":    {"name": "Serpent Tie",      "slot": "tie",      "price": 90, "rarity": "mythic",    "crate_only": True, "tie_color": (200, 40, 80)},
    "hair_mythic":   {"name": "Ember Hair",       "slot": "hair",     "price": 91, "rarity": "mythic",    "crate_only": True, "hair_color": (255, 70, 40)},
    "aura_divine":   {"name": "Divine Aura",      "slot": "aura",     "price": 100, "rarity": "god",     "crate_only": True, "aura_color": (255, 240, 140)},
    "hat_god":       {"name": "God Crown",        "slot": "hat",      "price": 105, "rarity": "god",     "crate_only": True, "hat_color": (255, 250, 180)},
    "coat_god":      {"name": "God Mantle",       "slot": "coat",     "price": 102, "rarity": "god",     "crate_only": True, "coat_color": (240, 220, 100)},
    "badge_god":     {"name": "God Protocol",     "slot": "badge",    "price": 98, "rarity": "god",      "crate_only": True, "badge_color": (255, 230, 90)},
    "hair_godstream":{"name": "Godstream Hair",   "slot": "hair",     "price": 96, "rarity": "god",       "crate_only": True, "hair_color": (255, 220, 120)},
    "glasses_god":   {"name": "God Sight",        "slot": "glasses",  "price": 99, "rarity": "god",      "crate_only": True, "frame_color": (255, 245, 160)},
    "tie_god":       {"name": "God Thread Tie",   "slot": "tie",      "price": 97, "rarity": "god",      "crate_only": True, "tie_color": (255, 210, 80)},
}


def default_save() -> dict:
    return {
        "version": SAVE_VERSION,
        "wallet_credits": 0,
        "owned_cosmetics": [],
        "equipped": {},
        "shop_date": "",
        "shop_items": [],
        "shop_bought_today": [],
        "runs_completed": 0,
        "crate_seed": str(random.randint(100000, 999999)),
        "crates_opened": 0,
        "last_crate_open": None,
        "avatar_name": "Mentor",
        "player_name": "",
        "in_progress": None,
        "last_build": None,
        "custom_tag_library": [],
        "save_hmac": "",
        "admin_signed": False,
        "integrity_ok": True,
        "completed_trades": [],
        "trade_history": [],
        "settings": {
            "muted": False,
            "fullscreen": False,
            "message_duration": 10,
            "keybinds": {
                "chat": "c",
                "trade": "t",
                "world": "l",
                "flex": "f",
                "build": "space",
                "settings": ",",
                "fullscreen": "f11",
            },
        },
    }


def load_save_data() -> dict:
    """Load save from disk; returns a fresh default if missing or corrupt."""
    if os.path.isfile(SAVE_PATH):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**default_save(), **data}
            if merged.get("version") in (1, 2, 3, 4, SAVE_VERSION):
                merged["version"] = SAVE_VERSION
                if not merged.get("crate_seed"):
                    merged["crate_seed"] = str(random.randint(100000, 999999))
                from assistant_lab_integrity import apply_integrity_on_load
                merged, _warning = apply_integrity_on_load(merged)
                return merged
        except (json.JSONDecodeError, OSError):
            pass
    return default_save()


def write_save_data(data: dict, *, admin: bool = False) -> bool:
    """Write save to disk. Returns True on success."""
    try:
        from assistant_lab_integrity import prepare_save_for_write
        data["version"] = SAVE_VERSION
        prepare_save_for_write(data, admin=admin)
        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except OSError:
        return False


def normalize_player_key(name: str) -> str:
    """Lowercase name with spaces removed — used for owner matching."""
    return "".join((name or "").lower().split())


def is_lab_owner(name: str) -> bool:
    key = normalize_player_key(name)
    if key in LAB_OWNER_NAME_KEYS:
        return True
    low = (name or "").lower()
    return "owner" in low and "owen" in low


def format_lab_join_message(name: str) -> str:
    """System message when a player connects to lab chat."""
    if is_lab_owner(name):
        return (
            f"★ LAB OWNER {LAB_OWNER_DISPLAY_NAME} has joined the chat — "
            "welcome the creator of the Assistant Lab!"
        )
    return f"{name} joined the lab."


def format_world_join_message(name: str) -> str:
    """System message when a player enters the Social Lab world."""
    if is_lab_owner(name):
        return (
            f"★ LAB OWNER {LAB_OWNER_DISPLAY_NAME} entered the Social Lab — "
            "the creator is here to flex!"
        )
    return f"{name} entered the Social Lab to flex their build!"


def cosmetics_by_rarity(rarity: str) -> list[str]:
    return [cid for cid, c in COSMETIC_CATALOG.items() if c.get("rarity") == rarity]


def format_crate_drop_line(
    player: str,
    crate_id: str,
    item_id: str,
    rarity: str,
    *,
    duplicate: bool = False,
    refund: int = 0,
) -> str:
    """Human-readable crate pull for lab chat Drops tab."""
    crate = CRATE_TYPES.get(crate_id, {})
    item = COSMETIC_CATALOG.get(item_id, {})
    crate_name = crate.get("name", "Crate")
    item_name = item.get("name", "???")
    rlabel = RARITIES.get(rarity, RARITIES["common"])["label"]
    who = (player or "Builder").strip()[:20] or "Builder"
    if duplicate:
        return f"{who} opened {crate_name} — dup {rlabel} {item_name} (+{refund} CR)"
    return f"{who} opened {crate_name} — {rlabel} {item_name}!"


def grant_cosmetic(data: dict, item_id: str) -> bool:
    if item_id not in COSMETIC_CATALOG:
        return False
    owned = data.setdefault("owned_cosmetics", [])
    if item_id not in owned:
        owned.append(item_id)
    return True


def revoke_cosmetic(data: dict, item_id: str) -> bool:
    owned = data.setdefault("owned_cosmetics", [])
    if item_id in owned:
        owned.remove(item_id)
    equipped = data.setdefault("equipped", {})
    slot = COSMETIC_CATALOG.get(item_id, {}).get("slot")
    if slot and equipped.get(slot) == item_id:
        del equipped[slot]
    return True


def apply_admin_gift(
    data: dict,
    *,
    credits: int = 0,
    items: list[str] | None = None,
) -> tuple[bool, str]:
    """Apply a remote admin grant to local save data."""
    try:
        credits = max(0, min(9999, int(credits)))
    except (TypeError, ValueError):
        credits = 0
    granted_items = []
    owned = set(data.get("owned_cosmetics", []))
    for raw in items or []:
        iid = str(raw).strip()
        if iid in COSMETIC_CATALOG and iid not in owned:
            grant_cosmetic(data, iid)
            granted_items.append(iid)
            owned.add(iid)
    if credits:
        data["wallet_credits"] = min(9999, data.get("wallet_credits", 0) + credits)
    if credits == 0 and not granted_items:
        return False, "Nothing to grant."
    parts = []
    if credits:
        parts.append(f"+{credits} CR")
    for iid in granted_items:
        parts.append(COSMETIC_CATALOG[iid]["name"])
    return True, f"Admin gift received: {', '.join(parts)}"