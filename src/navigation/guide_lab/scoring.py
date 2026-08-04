"""Score Guide Lab decisions against gold."""
from __future__ import annotations

from typing import Any


def score_decision(gold: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Return per-check results and case_pass."""
    owed_gold = list(gold.get("owed") or [])
    owed_or = list(gold.get("owed_or") or [])
    first_gold = gold.get("first_family")
    first_or = list(gold.get("first_family_or") or [])
    must_not = list(gold.get("must_not") or [])

    owed_pred = list(decision.get("owed") or [])
    first_pred = decision.get("first_family")

    checks: dict[str, bool] = {}

    pred_set = set(owed_pred)
    gold_set = set(owed_gold)

    # Empty gold owed = intentionally owe nothing structural
    if gold.get("owed_mode") == "covers" and not gold_set and not owed_or:
        owed_ok = len(pred_set) == 0 or pred_set.isdisjoint(set(must_not) | {"seo"})
        if not gold_set and not owed_or:
            owed_ok = len(pred_set) == 0
    else:
        owed_ok = pred_set == gold_set
        if not owed_ok and owed_or:
            owed_ok = any(pred_set == set(alt) for alt in owed_or)
        if not owed_ok and gold.get("owed_mode") == "covers":
            owed_ok = gold_set.issubset(pred_set)
        if not owed_ok and gold.get("owed_mode") == "intersects_reference":
            need = set(owed_gold)
            for alt in owed_or:
                need |= set(alt)
            if "inspiration" in need or "snapshot" in need:
                owed_ok = bool(pred_set & {"inspiration", "snapshot"})
            else:
                owed_ok = bool(pred_set & gold_set)
    checks["owed"] = owed_ok

    first_ok = first_pred == first_gold or first_pred in first_or
    if gold.get("first_mode") == "reference_family":
        first_ok = first_pred in {"inspiration", "snapshot", "figma"} or first_pred == first_gold
        if first_pred in first_or:
            first_ok = True
    # When nothing owed, first may be a sentinel skip family
    if not gold_set and not owed_or:
        first_ok = first_pred in (first_or or ["observe", "verify"]) or first_pred == first_gold
    checks["first_family"] = bool(first_ok)

    tunnel_bad = any(f in owed_pred or first_pred == f for f in must_not)
    checks["must_not"] = not tunnel_bad

    if gold.get("require_multi_owed") and len(owed_pred) < 2:
        checks["multi_owed"] = False
    else:
        checks["multi_owed"] = True

    case_pass = all(checks.values())
    return {
        "checks": checks,
        "pass": case_pass,
        "owed_pred": owed_pred,
        "first_pred": first_pred,
    }
