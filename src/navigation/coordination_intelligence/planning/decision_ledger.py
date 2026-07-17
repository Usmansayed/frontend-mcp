"""Decision Ledger — unified lifecycle for engineering decisions through ship."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel, _utc_now

LEDGER_PERSISTENT_KEY = "decision_ledger"

HOLLOW_ACCEPT_PHRASES = frozenset({
    "looks fine",
    "looks good",
    "looks ok",
    "look fine",
    "look good",
    "fine",
    "ok",
    "okay",
    "good",
    "good enough",
    "n/a",
    "na",
    "none",
    "intentional",
    "by design",
    "no change",
    "no changes",
    "as is",
    "as-is",
    "wont fix",
    "won't fix",
})


def load_ledger(psm: ProjectSituationModel) -> dict[str, Any]:
    raw = psm.artifacts.persistent.get(LEDGER_PERSISTENT_KEY)
    if isinstance(raw, dict) and isinstance(raw.get("entries"), dict):
        return {
            "entries": dict(raw["entries"]),
            "session_stats": dict(raw.get("session_stats") or {}),
        }
    return {"entries": {}, "session_stats": {}}


def save_ledger(psm: ProjectSituationModel, ledger: dict[str, Any]) -> None:
    psm.artifacts.persistent[LEDGER_PERSISTENT_KEY] = {
        "entries": dict(ledger.get("entries") or {}),
        "session_stats": dict(ledger.get("session_stats") or {}),
        "updated_at": _utc_now(),
    }


def validate_accept_reason(reason: str | None) -> tuple[bool, str | None]:
    text = str(reason or "").strip()
    if len(text) < 25:
        return False, "accept_reason_too_short"
    normalized = " ".join(text.lower().split())
    if normalized in HOLLOW_ACCEPT_PHRASES:
        return False, "hollow_accept_phrase"
    for phrase in HOLLOW_ACCEPT_PHRASES:
        if normalized == phrase or normalized.startswith(f"{phrase}.") or normalized.startswith(f"{phrase},"):
            return False, "hollow_accept_phrase"
    return True, None


def apply_dispositions(
    ledger: dict[str, Any],
    dispositions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply agent dispositions. Returns (applied, rejected)."""
    entries = ledger.setdefault("entries", {})
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for item in dispositions:
        if not isinstance(item, dict):
            continue
        signal = str(item.get("signal") or item.get("decision_id") or "").strip()
        disposition = str(item.get("disposition") or "").strip().lower()
        if not signal or disposition not in {"revised", "accepted", "ask_user"}:
            rejected.append({"signal": signal, "reason": "invalid_disposition"})
            continue

        reason = str(item.get("reason") or item.get("accept_reason") or "").strip() or None
        if disposition == "accepted":
            ok, err = validate_accept_reason(reason)
            if not ok:
                rejected.append({"signal": signal, "reason": err})
                continue

        entry = dict(entries.get(signal) or {})
        entry.update({
            "signal": signal,
            "decision_id": signal,
            "phase": "closed" if disposition in {"revised", "accepted"} else "awaiting_user",
            "disposition": disposition,
            "accept_reason": reason if disposition == "accepted" else None,
            "closed_at": _utc_now() if disposition in {"revised", "accepted"} else None,
        })
        entries[signal] = entry
        applied.append({"signal": signal, "disposition": disposition})

    stats = ledger.setdefault("session_stats", {})
    stats["revised"] = sum(
        1 for e in entries.values() if e.get("disposition") == "revised"
    )
    stats["accepted"] = sum(
        1 for e in entries.values() if e.get("disposition") == "accepted"
    )
    stats["asked_user"] = sum(
        1 for e in entries.values() if e.get("disposition") == "ask_user"
    )
    return applied, rejected


def is_signal_suppressed(ledger: dict[str, Any], signal: str) -> bool:
    entry = (ledger.get("entries") or {}).get(signal) or {}
    if entry.get("phase") != "closed":
        return False
    return entry.get("disposition") == "accepted"


def upsert_challenge_entry(ledger: dict[str, Any], challenge: dict[str, Any]) -> None:
    signal = str(challenge.get("signal") or challenge.get("decision_id") or "")
    if not signal:
        return
    entries = ledger.setdefault("entries", {})
    existing = entries.get(signal) or {}
    if existing.get("phase") == "closed" and existing.get("disposition") in {"revised", "accepted"}:
        return
    entries[signal] = {
        **existing,
        **challenge,
        "phase": "challenge",
        "disposition": existing.get("disposition"),
        "accept_reason": existing.get("accept_reason"),
        "updated_at": _utc_now(),
    }
