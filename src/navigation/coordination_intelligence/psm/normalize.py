"""Envelope normalization into PSM Runtime — no raw MCP responses leave this layer."""

from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import (
    POSTURE_REGRESSED,
    ProjectSituationModel,
    _utc_now,
)
from navigation.coordination_intelligence.psm.signature import refresh_cluster_signature

VERIFY_CAPABILITIES = frozenset({"browser_verify", "seo_recommendation_verify", "design_consistency_audit"})


def _merge_unique(target: list[str], items: list[str]) -> None:
    for item in items:
        if item and item not in target:
            target.append(item)


def _domain_producers(bundle: RuntimeArtifactBundle) -> dict[str, list[str]]:
    matrix = bundle.capability_graph.get("evidence_capability_matrix") or {}
    out: dict[str, list[str]] = {}
    for domain, spec in matrix.items():
        out[domain] = list(spec.get("primary_producers") or [])
    return out


def infer_capability_from_envelope(
    bundle: RuntimeArtifactBundle,
    envelope: dict[str, Any],
    *,
    capability_hint: str | None = None,
) -> str | None:
    if capability_hint:
        return capability_hint
    tool = envelope.get("tool")
    if isinstance(tool, str):
        return bundle.tool_to_capability.get(tool)
    return None


def _posture_for_capability(
    bundle: RuntimeArtifactBundle,
    capability_id: str,
    envelope: dict[str, Any],
) -> dict[str, str]:
    contract = bundle.capability_by_id.get(capability_id) or {}
    produces = contract.get("produces") or {}
    evidence_spec = produces.get("evidence") or {}
    out: dict[str, str] = {}
    for domain, spec in evidence_spec.items():
        if isinstance(spec, dict) and "posture" in spec:
            posture = spec["posture"]
            if isinstance(posture, str) and "|" in posture:
                left, right = [p.strip() for p in posture.split("|", 1)]
                posture = left if envelope.get("ok") else right
            out[domain] = posture
        elif capability_id in VERIFY_CAPABILITIES:
            data = envelope.get("data") or {}
            if "verified" in data:
                passed = bool(data.get("verified"))
            else:
                passed = bool(envelope.get("ok"))
            out[domain] = "verified" if passed else POSTURE_REGRESSED
        else:
            out[domain] = "known" if envelope.get("ok") else "partial"
    if not out and envelope.get("ok"):
        producers = _domain_producers(bundle)
        for domain, caps in producers.items():
            if capability_id in caps:
                out[domain] = "known"
    return out


def _capability_outcome(
    capability_id: str,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    """Separate evidence quality from envelope transport success."""
    data = envelope.get("data") or {}
    explicit = data.get("coordination_evidence")
    if isinstance(explicit, dict):
        outcome = dict(explicit)
        status = str(outcome.get("outcome") or "noop")
        outcome["status"] = {
            "success": "succeeded",
            "degraded": "provisional",
            "failure": "failed",
            "noop": "noop",
        }.get(status, status)
    else:
        summary = data.get("agent_summary") or {}
        degraded = list(envelope.get("degraded") or []) + list(summary.get("degraded") or [])
        blocking = list(summary.get("blocking") or [])
        tool = str(envelope.get("tool") or "")
        quality: dict[str, Any] = {}
        noop_tools = {
            "perception_inspiration_session_end",
            "perception_resource_session_end",
            "perception_figma_status",
            "perception_figma_connect",
        }
        if tool in noop_tools and envelope.get("ok"):
            status = "noop"
        elif not envelope.get("ok"):
            status = "failed"
        elif tool == "perception_inspiration_collect":
            collection = data.get("inspiration_collection") or {}
            hits = list(collection.get("hits") or [])
            usable_refs = sum(
                1 for hit in hits
                if isinstance(hit, dict) and bool(hit.get("inspiration_blob"))
            )
            quality = {
                "usable_image_refs": usable_refs,
                "total_hits": len(hits),
                "minimum_required": 3,
            }
            status = "succeeded" if usable_refs >= 3 and not blocking else "provisional"
        elif tool == "perception_design_review" and (data.get("mode") or "") == "ship":
            ship_gate = data.get("ship_gate") or {}
            council_clear = bool(ship_gate.get("council_clear"))
            quality = {
                "mode": "ship",
                "challenges_emitted": len(data.get("challenges") or []),
                "open_high_roi": int(ship_gate.get("open_high_roi") or 0),
                "council_clear": council_clear,
            }
            status = "succeeded" if council_clear else "provisional"
        elif tool == "perception_design_review" and data.get("passed") is False:
            status = "provisional"
        elif tool == "perception_select_component_foundation":
            chosen = (data.get("foundation_selection") or {}).get("chosen")
            quality = {"chosen": bool(chosen)}
            status = "succeeded" if chosen and not blocking else "provisional"
        elif degraded or blocking:
            status = "provisional"
        else:
            status = "succeeded"
        outcome = {
            "status": status,
            "advancement_eligible": status == "succeeded",
            "quality": quality,
            "artifact_refs": {},
        }

    outcome.setdefault("capability_id", capability_id)
    outcome.setdefault("advancement_eligible", outcome.get("status") == "succeeded")
    outcome.setdefault("quality", {})
    outcome.setdefault("artifact_refs", {})
    outcome.setdefault("degraded_reasons", list(envelope.get("degraded") or []))
    outcome.setdefault("failure_reason", str(envelope.get("error") or "") or None)
    outcome["updated_at"] = _utc_now()
    return outcome


def apply_envelope(
    psm: ProjectSituationModel,
    envelope: dict[str, Any],
    bundle: RuntimeArtifactBundle,
    *,
    capability_id: str | None = None,
) -> str | None:
    """Mutate PSM from a normalized MCP envelope. Returns resolved capability_id."""
    cap = infer_capability_from_envelope(bundle, envelope, capability_hint=capability_id)
    if not cap:
        return None

    attempts = psm.episode.retry_counters.setdefault("capability_attempts", {})
    attempts[cap] = int(attempts.get(cap, 0)) + 1
    capability_outcome = _capability_outcome(cap, envelope)
    psm.evidence.capability_ledger[cap] = capability_outcome

    data = envelope.get("data") or {}
    ship_gate = data.get("ship_gate") if isinstance(data.get("ship_gate"), dict) else {}
    if (data.get("mode") == "ship") or ("council_clear" in ship_gate):
        clear = bool(ship_gate.get("council_clear"))
        if not ship_gate and isinstance(capability_outcome.get("quality"), dict):
            clear = bool((capability_outcome.get("quality") or {}).get("council_clear"))
        psm.episode.retry_counters["ship_council_run"] = True
        psm.episode.retry_counters["ship_council_clear"] = clear

    if envelope.get("session_id"):
        psm.artifacts.session_id = envelope["session_id"]
    if envelope.get("scan_id"):
        psm.artifacts.scan_id = envelope["scan_id"]
    if envelope.get("url"):
        psm.artifacts.website_url = envelope["url"]

    if data.get("snapshot_id"):
        psm.artifacts.snapshot_id = data["snapshot_id"]
    if data.get("audit_id"):
        psm.artifacts.audit_id = data["audit_id"]

    summary = data.get("agent_summary") or {}
    _merge_unique(psm.evidence.blocking, list(summary.get("blocking") or []))
    _merge_unique(psm.evidence.degraded, list(envelope.get("degraded") or []))
    _merge_unique(psm.evidence.degraded, list(summary.get("degraded") or []))

    if envelope.get("error"):
        psm.evidence.blocking.append(str(envelope["error"]))

    if cap == "auth_gate":
        auth = data.get("auth_gate") or data
        if auth.get("requires_human"):
            psm.episode.auth_status = "requires_human"
            psm.constraints.human_gates.append("auth_gate_requires_human")
        else:
            psm.episode.auth_status = "clear"

    if cap == "browser_observe" and envelope.get("ok"):
        from navigation.coordination_intelligence.planning.section_checklist import (
            mark_section_observed,
        )

        section_id = data.get("section_id")
        mark_section_observed(
            psm,
            section_id=str(section_id) if section_id else None,
        )

    if cap in VERIFY_CAPABILITIES:
        data = envelope.get("data") or {}
        # Strict: transport ok does not mean criteria passed.
        if "verified" in data:
            passed = bool(data.get("verified"))
        else:
            passed = bool(envelope.get("ok"))
        psm.episode.verification_status = "passed" if passed else "failed"
        if not passed:
            psm.episode.retry_counters["verify_loop"] = int(
                psm.episode.retry_counters.get("verify_loop", 0)
            ) + 1
        # Section progress only when section_id is explicit (page-level verify does not close blocks).
        section_id = data.get("section_id") or (data.get("criteria") or {}).get("section_id")
        if passed and section_id:
            from navigation.coordination_intelligence.planning.section_checklist import (
                mark_section_verified,
            )

            mark_section_verified(
                psm,
                section_id=str(section_id),
                verified=True,
            )

    if cap == "form_probe" and envelope.get("ok"):
        psm.evidence.unknown_gaps = [
            g for g in psm.evidence.unknown_gaps if g != "form_rules"
        ]

    postures = (
        {}
        if capability_outcome.get("status") in ("failed", "noop")
        else _posture_for_capability(bundle, cap, envelope)
    )
    if cap == "component_select" and capability_outcome.get("status") == "succeeded":
        postures["design_system"] = "known"
    now = _utc_now()
    for domain, posture in postures.items():
        if domain not in psm.evidence.domains:
            continue
        state = psm.evidence.domains[domain]
        if capability_outcome.get("status") == "provisional" and posture in ("known", "verified"):
            posture = "partial"
        if psm.evidence.degraded and cap in VERIFY_CAPABILITIES and posture == "verified":
            posture = "partial"
        state.posture = posture
        state.updated_at = now
        state.source_capability = cap
        if psm.artifacts.scan_id:
            state.artifact_refs["scan_id"] = psm.artifacts.scan_id

    psm.touch()
    refresh_cluster_signature(psm)
    return cap
