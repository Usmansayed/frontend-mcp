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
MEASURED_PERSISTENT_KEY = "measured_engineering_spec"
MEASURED_META_KEY = "measured_engineering_spec_meta"
FOUNDATION_PERSISTENT_KEY = "component_foundation"

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
    coverage = dict(spec_dict.get("coverage") or {})
    coverage_ratio = float(coverage.get("coverage_ratio") or 0.0)
    seed_source = "seed" in source or source == "inspiration"
    implementation_ready = not seed_source and coverage_ratio >= 0.5
    quality = "implementation_ready" if implementation_ready else "provisional"
    meta = {
        "source": source,
        "note": note,
        "catalog_version": spec_dict.get("catalog_version"),
        "source_kind": spec_dict.get("source_kind"),
        "coverage": coverage,
        "quality": quality,
        "implementation_ready": implementation_ready,
    }
    if psm is not None:
        psm.artifacts.persistent = dict(psm.artifacts.persistent or {})
        psm.artifacts.persistent[REF_PERSISTENT_KEY] = spec_dict
        psm.artifacts.persistent[REF_META_KEY] = meta
    if session_id:
        _SESSION_REF[str(session_id)] = {"spec": spec_dict, "meta": meta}
    return {
        "bound": True,
        "quality": quality,
        "implementation_ready": implementation_ready,
        "meta": meta,
    }


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


def store_measured_spec(
    spec: FrontendEngineeringSpec | dict[str, Any],
    *,
    session_id: str | None = None,
    psm: Any | None = None,
    source: str = "live_dom",
    scan_id: str | None = None,
    snapshot_id: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    """Persist latest live-measured Spec (does not overwrite a deliberate reference Spec)."""
    if isinstance(spec, FrontendEngineeringSpec):
        spec_dict = spec.to_dict()
    else:
        spec_dict = dict(spec)
    meta = {
        "source": source,
        "note": note,
        "catalog_version": spec_dict.get("catalog_version"),
        "source_kind": spec_dict.get("source_kind") or "live_dom",
        "coverage": dict(spec_dict.get("coverage") or {}),
        "scan_id": scan_id,
        "snapshot_id": snapshot_id,
        "quality": "measured",
    }
    if psm is not None:
        psm.artifacts.persistent = dict(psm.artifacts.persistent or {})
        psm.artifacts.persistent[MEASURED_PERSISTENT_KEY] = spec_dict
        psm.artifacts.persistent[MEASURED_META_KEY] = meta
        if snapshot_id:
            psm.artifacts.snapshot_id = snapshot_id
    if session_id:
        blob = _SESSION_REF.setdefault(str(session_id), {})
        blob["measured_spec"] = spec_dict
        blob["measured_meta"] = meta
    return {"stored": True, "meta": meta}


def get_measured_spec(
    *,
    session_id: str | None = None,
    psm: Any | None = None,
) -> tuple[FrontendEngineeringSpec | None, dict[str, Any]]:
    """Latest live-measured Spec from observe/snapshot auto-compile."""
    if psm is not None:
        persistent = psm.artifacts.persistent or {}
        raw = persistent.get(MEASURED_PERSISTENT_KEY)
        meta = dict(persistent.get(MEASURED_META_KEY) or {})
        if isinstance(raw, dict) and raw.get("decisions"):
            try:
                return FrontendEngineeringSpec.from_dict(raw), meta or {"source": "episode_measured"}
            except Exception:
                pass
    if session_id and session_id in _SESSION_REF:
        blob = _SESSION_REF[session_id]
        raw = blob.get("measured_spec")
        meta = dict(blob.get("measured_meta") or {})
        if isinstance(raw, dict) and raw.get("decisions"):
            try:
                return FrontendEngineeringSpec.from_dict(raw), meta or {"source": "session_measured"}
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
            "evaluated": False,
            "phase": phase,
            "revision_required": False,
            "passed": False,
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
            "evaluated": True,
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
        "evaluated": True,
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


def store_foundation_selection(
    selection: dict[str, Any],
    *,
    psm: Any | None = None,
) -> None:
    """Persist usable foundation select onto PSM so live Spec can resolve catalog status.

    Durable rule: catalog library is always a LIBRARY id (@shadcn, …), never a block name.
    """
    if psm is None or not isinstance(selection, dict):
        return

    from navigation.component_intelligence.selection.library_lock import (
        is_valid_foundation_library,
        normalize_library_id,
    )

    library = normalize_library_id(
        selection.get("library")
        or selection.get("library_id")
        or selection.get("registry")
    )
    # Reject storing specialty/block names as the foundation library.
    if not is_valid_foundation_library(
        library,
        allow_specialty=bool(selection.get("allow_specialty")),
    ):
        # Last resort: if category is library lock, trust registry.
        if str(selection.get("category") or "") == "library":
            library = normalize_library_id(selection.get("registry") or selection.get("name"))
        else:
            return
    if not library:
        return

    try:
        confidence = float(selection.get("relevance_score") or selection.get("confidence") or 0.9)
    except (TypeError, ValueError):
        confidence = 0.9

    starter_name = None
    if str(selection.get("category") or "") not in ("library",):
        # legacy path where chosen was a component — keep as starter only
        starter_name = selection.get("name") or selection.get("title")
    if selection.get("starter_name"):
        starter_name = selection.get("starter_name")

    hint = {
        "foundation": library,
        "library": library,
        "id": selection.get("id") or library,
        "confidence": confidence,
        "name": library,
        "starter": starter_name,
        "lock_evidence": list(selection.get("lock_evidence") or []),
    }
    psm.artifacts.persistent = dict(psm.artifacts.persistent or {})
    psm.artifacts.persistent[FOUNDATION_PERSISTENT_KEY] = hint
    _patch_measured_foundation_status(psm, hint)


def _patch_measured_foundation_status(psm: Any, hint: dict[str, Any]) -> None:
    """Update stored measured catalog so component.foundation_status resolves after select."""
    persistent = getattr(psm.artifacts, "persistent", None) or {}
    raw = persistent.get(MEASURED_PERSISTENT_KEY)
    if not isinstance(raw, dict):
        return
    decisions = raw.get("decisions")
    if not isinstance(decisions, dict):
        return
    library = hint.get("library") or hint.get("foundation") or hint.get("name")
    decisions["component.foundation_status"] = {
        "decision_id": "component.foundation_status",
        "group": "component_foundation",
        "status": "resolved",
        "value": {"status": "selected", "library": library},
        "unit": None,
        "confidence": round(float(hint.get("confidence") or 0.85), 4),
        "importance": "high",
        "impact_weight": 0.7,
        "evidence": ["component_foundation_hint"],
        "constraints": {},
        "why": "Foundation provided by component selection context.",
        "why_code": "hint.foundation_selected",
        "provenance": {"patched_after_select": True},
        "raw_refs": [],
    }
    unresolved = raw.get("unresolved_by_impact")
    if isinstance(unresolved, list):
        raw["unresolved_by_impact"] = [
            u
            for u in unresolved
            if not (isinstance(u, dict) and u.get("decision_id") == "component.foundation_status")
        ]
    coverage = raw.get("coverage")
    if isinstance(coverage, dict):
        try:
            total = int(coverage.get("total") or len(decisions) or 1)
            settled = sum(
                1
                for d in decisions.values()
                if isinstance(d, dict) and d.get("status") in ("resolved", "partial", "not_applicable")
            )
            coverage["settled"] = settled
            coverage["settled_ratio"] = round(settled / max(total, 1), 4)
        except (TypeError, ValueError):
            pass
    persistent[MEASURED_PERSISTENT_KEY] = raw
    session_id = getattr(psm.artifacts, "session_id", None)
    if session_id and str(session_id) in _SESSION_REF:
        _SESSION_REF[str(session_id)]["measured_spec"] = raw


def foundation_hint_from_psm(psm: Any | None) -> dict[str, Any] | None:
    """Hint for compile_live_spec from a prior usable select."""
    if psm is None:
        return None
    raw = (getattr(psm.artifacts, "persistent", None) or {}).get(FOUNDATION_PERSISTENT_KEY)
    if not isinstance(raw, dict):
        # Fall back to ledger quality.selection when persistent missing.
        try:
            selected = (psm.evidence.capability_ledger.get("component_select") or {})
            if selected.get("status") != "succeeded" and not selected.get("advancement_eligible"):
                return None
            quality = selected.get("quality") if isinstance(selected.get("quality"), dict) else {}
            sel = quality.get("selection")
            if isinstance(sel, dict) and quality.get("usable") is not False:
                return {
                    "foundation": sel.get("name") or sel.get("title") or sel.get("id"),
                    "library": sel.get("registry") or sel.get("provider"),
                    "confidence": float(sel.get("relevance_score") or 0.85),
                }
        except Exception:
            return None
        return None
    if not (raw.get("foundation") or raw.get("library") or raw.get("name")):
        return None
    return {
        "foundation": raw.get("foundation") or raw.get("name") or raw.get("id"),
        "library": raw.get("library"),
        "confidence": float(raw.get("confidence") or 0.85),
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
