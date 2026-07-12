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
            out[domain] = "verified" if envelope.get("ok") else POSTURE_REGRESSED
        else:
            out[domain] = "known" if envelope.get("ok") else "partial"
    if not out and envelope.get("ok"):
        producers = _domain_producers(bundle)
        for domain, caps in producers.items():
            if capability_id in caps:
                out[domain] = "known"
    return out


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

    if envelope.get("session_id"):
        psm.artifacts.session_id = envelope["session_id"]
    if envelope.get("scan_id"):
        psm.artifacts.scan_id = envelope["scan_id"]
    if envelope.get("url"):
        psm.artifacts.website_url = envelope["url"]

    data = envelope.get("data") or {}
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

    if cap in VERIFY_CAPABILITIES:
        psm.episode.verification_status = "passed" if envelope.get("ok") else "failed"
        if not envelope.get("ok"):
            psm.episode.retry_counters["verify_loop"] = int(
                psm.episode.retry_counters.get("verify_loop", 0)
            ) + 1

    if cap == "form_probe" and envelope.get("ok"):
        psm.evidence.unknown_gaps = [
            g for g in psm.evidence.unknown_gaps if g != "form_rules"
        ]

    postures = _posture_for_capability(bundle, cap, envelope)
    now = _utc_now()
    for domain, posture in postures.items():
        if domain not in psm.evidence.domains:
            continue
        state = psm.evidence.domains[domain]
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
