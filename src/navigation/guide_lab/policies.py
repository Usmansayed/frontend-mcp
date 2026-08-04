"""Arm policies for Guide Lab quizzes (deterministic offline agents)."""
from __future__ import annotations

from typing import Any

# Capability → family (singular tunnel target for Arm A)
_CAP_FAMILY = {
    "inspiration_workflow": "inspiration",
    "design_snapshot": "snapshot",
    "component_search_plan": "component",
    "component_select": "component",
    "browser_observe": "observe",
    "browser_verify": "verify",
    "design_review": "design_review",
    "figma_integration": "figma",
    "codebase_context": "resolve",
    "design_graph_manage": "component",
    "form_probe": "forms",
    "guard_probe": "guards",
}

# Clean-guide: class → preferred family order (intersect unpaid)
_CLASS_OWE: dict[str, list[str]] = {
    "greenfield": ["inspiration", "snapshot", "component", "observe", "verify"],
    "redesign": ["snapshot", "observe", "verify", "inspiration", "component", "design_review"],
    "mockup": ["snapshot", "observe", "verify", "component", "design_review"],
    "feature": ["observe", "resolve", "verify"],
    "hotfix": ["observe", "verify"],
    "polish": ["observe", "verify"],
    "forms": ["observe", "forms", "verify", "guards"],
}

# When portfolio unpaid is empty (outside design initiative)
_CLASS_DEFAULTS: dict[str, list[str]] = {
    "greenfield": ["inspiration", "component", "observe"],
    "redesign": ["snapshot", "observe", "verify"],
    "mockup": ["snapshot", "observe", "verify"],
    "feature": ["observe", "verify"],
    "hotfix": ["observe", "verify"],
    "polish": ["observe", "verify"],
    "forms": ["observe", "forms", "verify"],
}

_DEFERRED = frozenset({"seo", "figma"})
_REF_FAMILIES = frozenset({"inspiration", "snapshot"})


def _unpaid_set(case: dict[str, Any]) -> list[str]:
    raw = case.get("unpaid") or []
    out: list[str] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(str(item.get("family") or item.get("id") or ""))
        else:
            out.append(str(item))
    return [u for u in out if u]


def _top_family(case: dict[str, Any]) -> str:
    top = case.get("backlog_top") or (case.get("backlog") or {}).get("top")
    if isinstance(top, dict):
        top_fam = _CAP_FAMILY.get(str(top.get("suggested_capability") or ""), "")
        return top_fam or str(top.get("family") or "")
    top_fam = str(top or "")
    return _CAP_FAMILY.get(top_fam, top_fam)


def decide_arm_a(case: dict[str, Any]) -> dict[str, Any]:
    """Large-doc failure mode: latch onto ONE singular hint (top or gate.next)."""
    unpaid = _unpaid_set(case)
    unpaid_set = set(unpaid)
    gate = case.get("gate") or {}
    next_cap = (
        gate.get("next_required_capability")
        or case.get("recommended_evidence")
        or case.get("next_capability")
    )
    gate_fam = _CAP_FAMILY.get(str(next_cap or ""), "observe")
    top_fam = _top_family(case)

    if top_fam and top_fam in unpaid_set:
        family = top_fam
        why = f"tunnel_backlog_top:{top_fam}"
    elif gate_fam:
        family = gate_fam
        why = f"tunnel_gate_next:{next_cap}"
    else:
        family = unpaid[0] if unpaid else "observe"
        why = "tunnel_first_unpaid"

    return {
        "arm": "A",
        "owed": [family],
        "first_family": family,
        "rationale": why,
    }


def decide_arm_b(case: dict[str, Any]) -> dict[str, Any]:
    """Clean-guide algorithm: unpaid ∩ class owe ≤3; class tables beat singular next."""
    task_class = str(case.get("class") or case.get("task_class") or "feature").lower()
    sticky = bool(case.get("sticky_design"))
    prefer = list(
        _CLASS_OWE["mockup"]
        if task_class == "mockup"
        else _CLASS_OWE.get(task_class, _CLASS_OWE["feature"])
    )
    if sticky and task_class in ("polish", "hotfix"):
        prefer = ["observe", "verify", "sections", "design_review", "residue"]

    unpaid = _unpaid_set(case)
    unpaid_set = set(unpaid)

    # Gate ladder families bind ahead of class tables when unpaid
    ladder = [f for f in ("sections", "residue") if f in unpaid_set]
    prefer = ladder + prefer

    owed: list[str] = []
    for fam in prefer:
        if fam not in unpaid_set:
            continue
        if fam in _REF_FAMILIES and task_class == "greenfield":
            if owed and any(x in owed for x in _REF_FAMILIES):
                continue
        if fam == "inspiration" and task_class in ("redesign", "mockup"):
            if "snapshot" in unpaid_set:
                continue
        owed.append(fam)
        if len(owed) >= 3:
            break

    if not owed:
        structural = [u for u in unpaid if u not in _DEFERRED]
        if structural:
            owed = structural[:3]
        else:
            owed = list(_CLASS_DEFAULTS.get(task_class, ["observe", "verify"]))[:3]

    top_fam = _top_family(case)

    if task_class in ("redesign", "mockup") and "snapshot" in owed:
        first = "snapshot"
    elif "residue" in owed:
        first = "residue"
    elif "sections" in owed:
        first = "sections"
    elif (
        task_class == "redesign"
        and "inspiration" in owed
        and "snapshot" not in unpaid_set
    ):
        first = "inspiration"
    elif task_class == "greenfield" and any(f in owed for f in _REF_FAMILIES):
        first = next(f for f in ("inspiration", "snapshot") if f in owed)
    elif (
        task_class == "greenfield"
        and "component" in owed
        and not any(f in owed for f in _REF_FAMILIES)
    ):
        first = "component"
    elif task_class in ("hotfix", "polish") and "observe" in owed:
        first = "observe"
    elif task_class == "forms" and "observe" in owed:
        first = "observe"
    elif task_class == "forms" and "forms" in owed:
        first = "forms"
    elif task_class == "feature" and "resolve" in owed and top_fam == "resolve":
        first = "resolve"
    elif task_class == "feature" and "observe" in owed:
        first = "observe"
    elif not owed:
        first = "observe"
    elif top_fam in owed:
        first = top_fam
    else:
        first = owed[0] if owed else "observe"

    return {
        "arm": "B",
        "owed": owed[:3],
        "first_family": first,
        "rationale": f"clean_guide:{task_class}",
    }
