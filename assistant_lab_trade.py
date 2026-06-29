"""
Assistant Lab — safe player trading (anti-scam).

Server holds a frozen trade snapshot; BOTH players must confirm the exact same
offer before either client applies changes locally.

Anti-scam rules:
  - Mirror trade: B gives exactly what A wants; A gives exactly what A offered
  - 5-second review timer before CONFIRM unlocks
  - Max credits/items per trade
  - Duplicate trade_id blocked on client
  - Decline cooldown after cancel
  - Kid-safe item IDs only (catalog)
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from assistant_lab_chat_log import chat_log_manager
from assistant_lab_data import COSMETIC_CATALOG

MAX_TRADE_CREDITS = 500
MAX_TRADE_ITEMS = 3
REVIEW_SECONDS = 5
DECLINE_COOLDOWN_SEC = 20
TRADE_TIMEOUT_SEC = 180


def _valid_item_ids(items) -> list[str]:
    if not isinstance(items, list):
        return []
    out = []
    for raw in items:
        iid = str(raw).strip()
        if iid in COSMETIC_CATALOG and iid not in out:
            out.append(iid)
        if len(out) >= MAX_TRADE_ITEMS:
            break
    return out


def normalize_bundle(raw: dict | None) -> dict[str, Any]:
    raw = raw or {}
    try:
        credits = int(raw.get("credits", 0))
    except (TypeError, ValueError):
        credits = 0
    credits = max(0, min(MAX_TRADE_CREDITS, credits))
    return {"credits": credits, "items": _valid_item_ids(raw.get("items", []))}


def bundle_empty(bundle: dict) -> bool:
    return bundle.get("credits", 0) == 0 and not bundle.get("items")


def bundle_label(bundle: dict) -> str:
    parts = []
    if bundle.get("credits", 0):
        parts.append(f"{bundle['credits']} CR")
    for iid in bundle.get("items", []):
        parts.append(COSMETIC_CATALOG.get(iid, {}).get("name", iid))
    return ", ".join(parts) if parts else "(nothing)"


def can_afford_side(bundle: dict, wallet: int, owned: set[str]) -> tuple[bool, str]:
    if bundle.get("credits", 0) > wallet:
        return False, "Not enough credits for this trade."
    for iid in bundle.get("items", []):
        if iid not in owned:
            name = COSMETIC_CATALOG.get(iid, {}).get("name", iid)
            return False, f"You don't own {name}."
    return True, ""


def apply_trade_to_save(
    save_data: dict,
    *,
    my_name: str,
    trade_id: str,
    from_player: str,
    to_player: str,
    a_gives: dict,
    a_wants: dict,
) -> tuple[bool, str]:
    """
    Apply a server-authorized trade to local save.

    from_player proposed: gives a_gives, wants a_wants.
    to_player gives a_wants and receives a_gives.
    """
    if save_data.get("integrity_violation"):
        return False, "Anti-cheat: trading disabled on tampered saves."

    done = save_data.setdefault("completed_trades", [])
    if trade_id in done:
        return False, "Trade already completed."

    if my_name == from_player:
        give, receive = a_gives, a_wants
    elif my_name == to_player:
        give, receive = a_wants, a_gives
    else:
        return False, "You are not part of this trade."

    give = normalize_bundle(give)
    receive = normalize_bundle(receive)
    if bundle_empty(give) and bundle_empty(receive):
        return False, "Empty trade."

    owned = set(save_data.get("owned_cosmetics", []))
    wallet = int(save_data.get("wallet_credits", 0))
    ok, err = can_afford_side(give, wallet, owned)
    if not ok:
        return False, err

    # Deduct give
    save_data["wallet_credits"] = wallet - give["credits"]
    owned_list = list(save_data.get("owned_cosmetics", []))
    equipped = dict(save_data.get("equipped", {}))
    for iid in give["items"]:
        if iid in owned_list:
            owned_list.remove(iid)
        slot = COSMETIC_CATALOG.get(iid, {}).get("slot")
        if slot and equipped.get(slot) == iid:
            del equipped[slot]

    # Add receive
    save_data["wallet_credits"] = int(save_data.get("wallet_credits", 0)) + receive["credits"]
    for iid in receive["items"]:
        if iid not in owned_list:
            owned_list.append(iid)

    save_data["owned_cosmetics"] = owned_list
    save_data["equipped"] = equipped
    done.append(trade_id)
    if len(done) > 50:
        save_data["completed_trades"] = done[-50:]
    history = save_data.setdefault("trade_history", [])
    history.append({
        "id": trade_id,
        "with": to_player if my_name == from_player else from_player,
        "gave": give,
        "got": receive,
        "ts": time.strftime("%Y-%m-%d %H:%M"),
    })
    save_data["trade_history"] = history[-30:]
    return True, f"Trade complete! You gave {bundle_label(give)} and got {bundle_label(receive)}."


class TradeManager:
    """Server-side trade sessions — both players must confirm frozen snapshot."""

    def __init__(self):
        self._trades: dict[str, dict[str, Any]] = {}
        self._by_player: dict[str, str] = {}
        self._cooldown: dict[str, float] = {}

    def _find_client(self, name: str, clients: list):
        for c in clients:
            if getattr(c, "name", "") == name:
                return c
        return None

    def _cooldown_active(self, name: str) -> bool:
        return time.time() < self._cooldown.get(name, 0)

    def _set_cooldown(self, name: str) -> None:
        self._cooldown[name] = time.time() + DECLINE_COOLDOWN_SEC

    def _cancel_trade(self, trade_id: str, reason: str, clients: list) -> None:
        trade = self._trades.pop(trade_id, None)
        if not trade:
            return
        self._by_player.pop(trade.get("from"), None)
        self._by_player.pop(trade.get("to"), None)
        payload = {"type": "trade_cancelled", "trade_id": trade_id, "reason": reason}
        for pname in (trade.get("from"), trade.get("to")):
            client = self._find_client(pname, clients)
            if client:
                client._send(payload)

    def _expire_old(self, clients: list) -> None:
        now = time.time()
        expired = [tid for tid, t in self._trades.items() if now - t.get("created", now) > TRADE_TIMEOUT_SEC]
        for tid in expired:
            self._cancel_trade(tid, "Trade timed out.", clients)

    def handle_packet(self, handler, data: dict, clients: list) -> None:
        self._expire_old(clients)
        mtype = data.get("type")
        if mtype == "trade_offer":
            self._handle_offer(handler, data, clients)
        elif mtype == "trade_confirm":
            self._handle_confirm(handler, data, clients)
        elif mtype == "trade_cancel":
            self._handle_cancel(handler, data, clients)

    def _handle_offer(self, handler, data: dict, clients: list) -> None:
        sender = handler.name
        if not sender:
            handler._send({"type": "error", "text": "Join before trading."})
            return
        if self._cooldown_active(sender):
            handler._send({"type": "error", "text": "Wait a moment before trading again."})
            return
        if sender in self._by_player:
            handler._send({"type": "error", "text": "You already have an active trade."})
            return

        partner = str(data.get("to", "")).strip()[:20]
        if not partner or partner == sender:
            handler._send({"type": "error", "text": "Pick a trade partner."})
            return
        if not self._find_client(partner, clients):
            handler._send({"type": "error", "text": f"{partner} is not online."})
            return
        if partner in self._by_player:
            handler._send({"type": "error", "text": f"{partner} is already in a trade."})
            return

        give = normalize_bundle(data.get("give"))
        want = normalize_bundle(data.get("want"))
        if bundle_empty(give) and bundle_empty(want):
            handler._send({"type": "error", "text": "Offer something or ask for something."})
            return

        trade_id = uuid.uuid4().hex[:12]
        now = time.time()
        trade = {
            "trade_id": trade_id,
            "from": sender,
            "to": partner,
            "a_gives": give,
            "a_wants": want,
            "a_confirmed": False,
            "b_confirmed": False,
            "created": now,
            "review_until": now + REVIEW_SECONDS,
        }
        self._trades[trade_id] = trade
        self._by_player[sender] = trade_id
        self._by_player[partner] = trade_id

        review_msg = (
            f"SAFE TRADE #{trade_id}: {sender} offers you [{bundle_label(give)}] "
            f"for your [{bundle_label(want)}]. Review {REVIEW_SECONDS}s, then confirm BOTH sides."
        )
        notify = {
            "type": "trade_offer",
            "trade_id": trade_id,
            "from": sender,
            "to": partner,
            "a_gives": give,
            "a_wants": want,
            "review_until": trade["review_until"],
            "anti_scam": (
                "ANTI-SCAM: Only confirm if YOU GIVE / YOU GET looks correct. "
                "Both players must confirm the same trade."
            ),
        }
        handler._send({**notify, "role": "sender", "text": f"Trade sent to {partner}. Confirm when ready."})
        partner_client = self._find_client(partner, clients)
        if partner_client:
            partner_client._send({**notify, "role": "receiver"})
        handler._send({"type": "system", "text": review_msg})

    def _handle_confirm(self, handler, data: dict, clients: list) -> None:
        sender = handler.name
        trade_id = str(data.get("trade_id", ""))
        trade = self._trades.get(trade_id)
        if not trade or sender not in (trade.get("from"), trade.get("to")):
            handler._send({"type": "error", "text": "Unknown or expired trade."})
            return
        if time.time() < trade.get("review_until", 0):
            left = int(trade["review_until"] - time.time()) + 1
            handler._send({"type": "error", "text": f"Review the trade {left}s more before confirming."})
            return

        if sender == trade["from"]:
            trade["a_confirmed"] = True
        else:
            trade["b_confirmed"] = True

        status = {
            "type": "trade_status",
            "trade_id": trade_id,
            "from": trade["from"],
            "to": trade["to"],
            "a_gives": trade["a_gives"],
            "a_wants": trade["a_wants"],
            "a_confirmed": trade["a_confirmed"],
            "b_confirmed": trade["b_confirmed"],
        }
        for pname in (trade["from"], trade["to"]):
            client = self._find_client(pname, clients)
            if client:
                client._send(status)

        if trade["a_confirmed"] and trade["b_confirmed"]:
            execute = {
                "type": "trade_execute",
                "trade_id": trade_id,
                "from": trade["from"],
                "to": trade["to"],
                "a_gives": trade["a_gives"],
                "a_wants": trade["a_wants"],
            }
            for pname in (trade["from"], trade["to"]):
                client = self._find_client(pname, clients)
                if client:
                    client._send(execute)
            self._trades.pop(trade_id, None)
            self._by_player.pop(trade["from"], None)
            self._by_player.pop(trade["to"], None)
            trade_done = {
                "type": "system",
                "text": f"Trade #{trade_id} completed between {trade['from']} and {trade['to']}!",
            }
            chat_log_manager.record_payload(trade_done)
            for client in clients:
                if getattr(client, "name", None) in (trade["from"], trade["to"]):
                    client._send(trade_done)

    def _handle_cancel(self, handler, data: dict, clients: list) -> None:
        sender = handler.name
        trade_id = str(data.get("trade_id", ""))
        trade = self._trades.get(trade_id)
        if not trade or sender not in (trade.get("from"), trade.get("to")):
            handler._send({"type": "error", "text": "No trade to cancel."})
            return
        self._set_cooldown(sender)
        self._cancel_trade(trade_id, f"{sender} cancelled the trade.", clients)

    def on_disconnect(self, name: str, clients: list) -> None:
        trade_id = self._by_player.pop(name, None)
        if trade_id:
            self._cancel_trade(trade_id, f"{name} disconnected.", clients)