"""Deterministic cluster_signature hashing for PSM Runtime."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel


def _evidence_posture_vector(psm: ProjectSituationModel) -> dict[str, str]:
    return {domain: state.posture for domain, state in psm.evidence.domains.items()}


def cluster_signature_payload(psm: ProjectSituationModel) -> dict[str, Any]:
    return {
        "situation_class": psm.situation.situation_class,
        "lifecycle_stage": psm.situation.lifecycle_stage,
        "evidence_posture_vector": _evidence_posture_vector(psm),
        "active_constraints": {
            "mcp_ready_blocks": sorted(psm.constraints.mcp_ready_blocks),
            "modules_forbidden": sorted(psm.constraints.modules_forbidden),
            "human_gates": sorted(psm.constraints.human_gates),
            "invariants_active": sorted(psm.constraints.invariants_active),
        },
        "available_capabilities": sorted(psm.situation.capability_posture.eligible),
    }


def compute_cluster_signature(psm: ProjectSituationModel) -> str:
    payload = cluster_signature_payload(psm)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def refresh_cluster_signature(psm: ProjectSituationModel) -> None:
    psm.situation.cluster_signature = compute_cluster_signature(psm)
