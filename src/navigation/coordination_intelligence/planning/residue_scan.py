"""Residue scan bookkeeping — one forced remeasure pass per design episode."""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel, _utc_now

RESIDUE_KEY = "residue_scan"


def get_residue_state(psm: ProjectSituationModel) -> dict[str, Any]:
    raw = psm.episode.retry_counters.get(RESIDUE_KEY)
    if isinstance(raw, dict):
        return dict(raw)
    return {"required": False, "completed": False, "at": None}


def mark_residue_required(psm: ProjectSituationModel) -> dict[str, Any]:
    state = get_residue_state(psm)
    if state.get("completed"):
        return state
    state = {
        "required": True,
        "completed": False,
        "at": _utc_now(),
    }
    psm.episode.retry_counters[RESIDUE_KEY] = state
    return state


def mark_residue_completed(psm: ProjectSituationModel) -> dict[str, Any]:
    state = {
        "required": False,
        "completed": True,
        "at": _utc_now(),
    }
    psm.episode.retry_counters[RESIDUE_KEY] = state
    return state


def residue_required(psm: ProjectSituationModel) -> bool:
    state = get_residue_state(psm)
    return bool(state.get("required")) and not bool(state.get("completed"))


def maybe_require_residue_for_ship(
    psm: ProjectSituationModel,
    *,
    coverage: str | None,
    challenge_count: int,
    dense_ui: bool,
    design_scope: bool,
) -> bool:
    """Return True if residue was newly required (or already pending)."""
    if not design_scope:
        return False
    state = get_residue_state(psm)
    if state.get("completed"):
        return False
    if state.get("required"):
        return True
    thin = coverage == "thin"
    empty_but_dense = challenge_count == 0 and dense_ui
    if thin or empty_but_dense:
        mark_residue_required(psm)
        return True
    return False
