"""Reference Spec binding + post-draft SpecDiff revision gate.

Closed loop (no new decision catalog entries):

  Reference Spec (bound on episode)
       ↓
  Host draft implementation
       ↓
  Remeasure → Current Spec
       ↓
  SpecDiff → revision_gate
       ↓
  Host revises until gate.passed

Stores reference Spec on PSM artifacts.persistent when an episode exists,
and in a process-local session fallback so the host can also re-pass the Spec.
"""
from __future__ import annotations

from typing import Any

from navigation.engineering_knowledge.models import FrontendEngineeringSpec
from navigation.engineering_knowledge.spec_diff import diff_specs

REF_PERSISTENT_KEY = "reference_engineering_spec"
REF_META_KEY = "reference_engineering_spec_meta"

# session_id → {spec, meta} — fallback when coordinator episode missing
_SESSION_REF: dict[str, dict[str, Any]] = {}


def bind_reference_spec(
    spec: FrontendEngineeringSpec | dict[str, Any],
    *,
    session_id: str | None = None,
    psm: Any | None = None,
    source: str = "manual",
    note: str = "",
) -> dict[str, Any]:
    """Bind Spec as the episode/session reference for later SpecDiff."""
    if isinstance(spec, FrontendEngineeringSpec):
        spec_dict = spec.to_dict()
    else:
        spec_dict = dict(spec)
    meta = {
        "source": source,
        "note": note,
        "catalog_version": spec_dict.get("catalog_version"),
        "source_kind": spec_dict.get("source_kind"),
        "coverage": spec_dict.get("coverage"),
    }
    if psm is not None:
        psm.artifacts.persistent = dict(psm.artifacts.persistent or {})
        psm.artifacts.persistent[REF_PERSISTENT_KEY] = spec_dict
        psm.artifacts.persistent[REF_META_KEY] = meta
    if session_id:
        _SESSION_REF[str(session_id)] = {"spec": spec_dict, "meta": meta}
    return {"bound": True, "meta": meta}


def clear_reference_spec(*, session_id: str | None = None, psm: Any | None = None) -> None:
    if psm is not None and isinstance(psm.artifacts.persistent, dict):
        psm.artifacts.persistent.pop(REF_PERSISTENT_KEY, None)
        psm.artifacts.persistent.pop(REF_META_KEY, None)
    if session_id and session_id in _SESSION_REF:
        del _SESSION_REF[session_id]


def get_reference_spec(
    *,
    session_id: str | None = None,
    psm: Any | None = None,
    reference_spec: dict[str, Any] | None = None,
) -> tuple[FrontendEngineeringSpec | None, dict[str, Any]]:
    """Resolve reference Spec: explicit arg > PSM > session fallback."""
    if isinstance(reference_spec, dict) and reference_spec.get("decisions"):
        try:
            return FrontendEngineeringSpec.from_dict(reference_spec), {
                "source": "argument",
                "source_kind": reference_spec.get("source_kind"),
            }
        except Exception:
            pass

    if psm is not None:
        persistent = psm.artifacts.persistent or {}
        raw = persistent.get(REF_PERSISTENT_KEY)
        meta = dict(persistent.get(REF_META_KEY) or {})
        if isinstance(raw, dict) and raw.get("decisions"):
            try:
                return FrontendEngineeringSpec.from_dict(raw), meta or {"source": "episode"}
            except Exception:
                pass

    if session_id and session_id in _SESSION_REF:
        blob = _SESSION_REF[session_id]
        raw = blob.get("spec")
        meta = dict(blob.get("meta") or {})
        if isinstance(raw, dict) and raw.get("decisions"):
            try:
                return FrontendEngineeringSpec.from_dict(raw), meta or {"source": "session"}
            except Exception:
                pass

    return None, {}


def evaluate_revision_gate(
    current: FrontendEngineeringSpec | dict[str, Any],
    reference: FrontendEngineeringSpec | dict[str, Any] | None,
    *,
    phase: str = "current",
) -> dict[str, Any]:
    """SpecDiff gate: did the draft drift from the bound reference Spec?"""
    if reference is None:
        return {
            "reference_bound": False,
            "phase": phase,
            "revision_required": False,
            "passed": True,
            "engineering_delta": None,
            "host_action": (
                "No reference Spec bound. Capture one first: "
                "perception_build_design_snapshot({ bind_as_reference: true }) "
                "or bind from inspiration seed Spec."
            ),
            "blocking_drifts": [],
            "major_drifts": [],
        }

    if isinstance(current, dict):
        current_spec = FrontendEngineeringSpec.from_dict(current)
    else:
        current_spec = current
    if isinstance(reference, dict):
        ref_spec = FrontendEngineeringSpec.from_dict(reference)
    else:
        ref_spec = reference

    if phase == "reference_captured":
        return {
            "reference_bound": True,
            "phase": phase,
            "revision_required": False,
            "passed": True,
            "engineering_delta": None,
            "host_action": (
                "Reference Spec bound. Implement from Spec decisions, then remeasure "
                "with perception_build_design_snapshot (default) to run SpecDiff gate."
            ),
            "blocking_drifts": [],
            "major_drifts": [],
            "reference_coverage": ref_spec.to_dict().get("coverage"),
        }

    delta = diff_specs(ref_spec, current_spec)
    delta_dict = delta.to_dict()
    blocking = [
        i for i in delta.items if i.severity == "blocking" and i.kind in (
            "value_drift", "enum_mismatch", "missing", "status_change"
        )
    ]
    major = [
        i for i in delta.items if i.severity == "major" and i.kind in (
            "value_drift", "enum_mismatch", "missing", "status_change"
        )
    ]
    # Soft-seed references (inspiration) — only gate when both sides have concrete values
    actionable_blocking = [
        i for i in blocking
        if i.from_value is not None and i.to_value is not None
    ]
    actionable_major = [
        i for i in major
        if i.from_value is not None and i.to_value is not None
    ]

    revision_required = bool(actionable_blocking or actionable_major)
    top = actionable_blocking[:3] or actionable_major[:3]
    if revision_required and top:
        host_action = (
            "REVISION REQUIRED — draft drifted from reference Spec. "
            + "; ".join(f"{t.decision_id}: {t.detail}" for t in top)
        )
    elif revision_required:
        host_action = "REVISION REQUIRED — SpecDiff found major/blocking drifts vs reference."
    else:
        host_action = (
            "SpecDiff gate passed — no major/blocking drifts vs bound reference Spec."
        )

    return {
        "reference_bound": True,
        "phase": phase,
        "revision_required": revision_required,
        "passed": not revision_required,
        "engineering_delta": delta_dict,
        "host_action": host_action,
        "blocking_drifts": [i.to_dict() for i in actionable_blocking[:12]],
        "major_drifts": [i.to_dict() for i in actionable_major[:12]],
        "reference_coverage": ref_spec.to_dict().get("coverage"),
        "current_coverage": current_spec.to_dict().get("coverage"),
    }


def resolve_psm_for_session(session_id: str | None) -> Any | None:
    """Best-effort episode PSM for a browser session_id."""
    if not session_id:
        return None
    try:
        from navigation.coordination_intelligence.integration.bridge import (
            coordinator_enabled,
            get_coordinator_bridge,
        )

        if not coordinator_enabled():
            return None
        bridge = get_coordinator_bridge()
        episode_id = bridge._bindings.resolve(session_id=session_id)
        if not episode_id:
            return None
        return bridge.service.runtime.get(episode_id)
    except Exception:
        return None
