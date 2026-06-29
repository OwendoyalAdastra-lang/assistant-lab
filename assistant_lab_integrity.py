"""
Save integrity + runtime anti-cheat for Assistant Lab.

- HMAC signature on wallet / cosmetics / crate stats (blocks hand-edited JSON)
- Config fingerprint (detects tampered crate prices or catalog in code)
- Admin panel writes saves with admin_signed=True (legitimate overrides)
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

# Pepper for HMAC — deters casual save-file editing (not unbreakable on local Python).
_INTEGRITY_PEPPER = b"grace-hopper-assistant-lab-integrity-v5"

# SHA-256 of crate catalog config — update if CRATE_TYPES / COSMETIC_CATALOG change.
_EXPECTED_CONFIG_HASH = "5fdc514e3c2819b2351225a919c6efd408d081c02f8310104fbc2060c33fd173"

PROTECTED_SAVE_KEYS = (
    "wallet_credits",
    "owned_cosmetics",
    "equipped",
    "crates_opened",
    "runs_completed",
)


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _signing_payload(data: dict) -> bytes:
    owned = data.get("owned_cosmetics") or []
    if not isinstance(owned, list):
        owned = []
    equipped = data.get("equipped") or {}
    if not isinstance(equipped, dict):
        equipped = {}
    payload = {
        "wallet_credits": int(data.get("wallet_credits") or 0),
        "owned_cosmetics": sorted(str(x) for x in owned),
        "equipped": {str(k): str(v) for k, v in sorted(equipped.items())},
        "crates_opened": int(data.get("crates_opened") or 0),
        "runs_completed": int(data.get("runs_completed") or 0),
    }
    return _stable_json(payload).encode("utf-8")


def sign_save(data: dict, *, admin: bool = False) -> None:
    """Attach HMAC to save before writing."""
    data["admin_signed"] = bool(admin)
    digest = hmac.new(_INTEGRITY_PEPPER, _signing_payload(data), hashlib.sha256).hexdigest()
    data["save_hmac"] = digest
    data["integrity_ok"] = True


def verify_save(data: dict) -> tuple[bool, str]:
    """Return (ok, reason)."""
    stored = data.get("save_hmac")
    if not stored:
        return False, "missing_signature"
    expected = hmac.new(_INTEGRITY_PEPPER, _signing_payload(data), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(stored), expected):
        return False, "tampered"
    return True, "ok"


def sanitize_cheated_save(data: dict) -> dict:
    """Reset rewards when someone hand-edited the save file."""
    data["wallet_credits"] = 0
    data["owned_cosmetics"] = []
    data["equipped"] = {}
    data["integrity_violation"] = True
    data["integrity_message"] = (
        "Anti-cheat: save file was edited outside the game. Wallet and items were reset."
    )
    data["admin_signed"] = False
    sign_save(data, admin=False)
    return data


def verify_runtime_config() -> bool:
    """True when crate/shop data in code matches the expected fingerprint."""
    try:
        from assistant_lab_data import COSMETIC_CATALOG, CRATE_TYPES
    except ImportError:
        return False
    blob = _stable_json({"crates": CRATE_TYPES, "n": len(COSMETIC_CATALOG)})
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return hmac.compare_digest(digest, _EXPECTED_CONFIG_HASH)


def apply_integrity_on_load(data: dict) -> tuple[dict, str | None]:
    """
    Validate loaded save. Returns (data, warning_message_or_none).

    - Missing HMAC on old saves: grandfather sign (first run after upgrade)
    - Invalid HMAC: sanitize (unless admin_signed — admin edits are trusted)
    - Bad runtime config: strip wallet/items
    """
    warning = None

    if not verify_runtime_config():
        data["wallet_credits"] = 0
        data["owned_cosmetics"] = []
        data["equipped"] = {}
        data["integrity_violation"] = True
        data["integrity_message"] = (
            "Anti-cheat: game files were modified. Earn credits the fair way!"
        )
        sign_save(data, admin=False)
        return data, data["integrity_message"]

    ok, reason = verify_save(data)
    if ok:
        data["integrity_ok"] = True
        data.pop("integrity_violation", None)
        return data, None

    if reason == "missing_signature":
        sign_save(data, admin=bool(data.get("admin_signed")))
        return data, None

    if data.get("admin_signed"):
        sign_save(data, admin=True)
        return data, None

    data = sanitize_cheated_save(data)
    return data, data.get("integrity_message")


def prepare_save_for_write(data: dict, *, admin: bool = False) -> dict:
    """Sign save before flushing to disk."""
    sign_save(data, admin=admin)
    return data