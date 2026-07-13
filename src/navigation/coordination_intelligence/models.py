"""Project Situation Model datatypes for PSM Runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

EVIDENCE_DOMAINS = (
    "ui_runtime",
    "codebase",
    "design_source",
    "design_system",
    "seo",
    "quality",
    "assets",
)

POSTURE_ORDER = ("unknown", "partial", "known", "verified")
POSTURE_REGRESSED = "regressed"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_episode_id() -> str:
    return f"ep_{uuid4().hex}"


@dataclass
class EvidenceDomainState:
    posture: str = "unknown"
    updated_at: str | None = None
    source_capability: str | None = None
    artifact_refs: dict[str, str] = field(default_factory=dict)
    staleness_ttl_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "posture": self.posture,
            "updated_at": self.updated_at,
            "source_capability": self.source_capability,
            "artifact_refs": dict(self.artifact_refs),
            "staleness_ttl_seconds": self.staleness_ttl_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EvidenceDomainState:
        data = data or {}
        return cls(
            posture=data.get("posture", "unknown"),
            updated_at=data.get("updated_at"),
            source_capability=data.get("source_capability"),
            artifact_refs=dict(data.get("artifact_refs") or {}),
            staleness_ttl_seconds=data.get("staleness_ttl_seconds"),
        )


@dataclass
class CapabilityPosture:
    eligible: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    deferred: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": list(self.eligible),
            "blocked": list(self.blocked),
            "deferred": list(self.deferred),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> CapabilityPosture:
        data = data or {}
        return cls(
            eligible=list(data.get("eligible") or []),
            blocked=list(data.get("blocked") or []),
            deferred=list(data.get("deferred") or []),
        )


@dataclass
class IntentFrame:
    intent: str
    pushed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {"intent": self.intent, "pushed_at": self.pushed_at}


@dataclass
class SituationState:
    situation_class: str = "new_feature"
    lifecycle_stage: str = "S05_implementation"
    project_maturity: str = "M3"
    cluster_id: str = "cluster.feature.form_pipeline"
    cluster_signature: str = "0" * 64
    leaf_hint: str | None = None
    capability_posture: CapabilityPosture = field(default_factory=CapabilityPosture)

    def to_dict(self) -> dict[str, Any]:
        return {
            "situation_class": self.situation_class,
            "lifecycle_stage": self.lifecycle_stage,
            "project_maturity": self.project_maturity,
            "cluster_id": self.cluster_id,
            "cluster_signature": self.cluster_signature,
            "leaf_hint": self.leaf_hint,
            "capability_posture": self.capability_posture.to_dict(),
        }


@dataclass
class EvidenceState:
    domains: dict[str, EvidenceDomainState] = field(default_factory=dict)
    blocking: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)
    unknown_gaps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for domain in EVIDENCE_DOMAINS:
            self.domains.setdefault(domain, EvidenceDomainState())

    def to_dict(self) -> dict[str, Any]:
        return {
            "domains": {k: v.to_dict() for k, v in self.domains.items()},
            "blocking": list(self.blocking),
            "degraded": list(self.degraded),
            "unknown_gaps": list(self.unknown_gaps),
        }


@dataclass
class ConstraintsState:
    mcp_ready_blocks: list[str] = field(default_factory=list)
    modules_forbidden: list[str] = field(default_factory=list)
    invariants_active: list[str] = field(default_factory=list)
    human_gates: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mcp_ready_blocks": list(self.mcp_ready_blocks),
            "modules_forbidden": list(self.modules_forbidden),
            "invariants_active": list(self.invariants_active),
            "human_gates": list(self.human_gates),
        }


@dataclass
class EpisodeState:
    active_playbook_id: str | None = None
    active_step_id: str | None = None
    intent_stack: list[IntentFrame] = field(default_factory=list)
    retry_counters: dict[str, Any] = field(default_factory=lambda: {"verify_loop": 0, "capability_attempts": {}})
    confidence: str = "medium"
    completed_step_ids: list[str] = field(default_factory=list)
    verification_status: str = "pending"
    auth_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_playbook_id": self.active_playbook_id,
            "active_step_id": self.active_step_id,
            "intent_stack": [f.to_dict() for f in self.intent_stack],
            "retry_counters": {
                "verify_loop": int(self.retry_counters.get("verify_loop", 0)),
                "capability_attempts": dict(self.retry_counters.get("capability_attempts") or {}),
            },
            "confidence": self.confidence,
            "completed_step_ids": list(self.completed_step_ids),
            "verification_status": self.verification_status,
            "auth_status": self.auth_status,
        }


@dataclass
class ArtifactsState:
    session_id: str | None = None
    scan_id: str | None = None
    snapshot_id: str | None = None
    audit_id: str | None = None
    repo_root: str | None = None
    website_url: str | None = None
    persistent: dict[str, Any] = field(default_factory=lambda: {
        "seo_graph_path": None,
        "pdg_path": None,
        "figma_connected": False,
    })

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "scan_id": self.scan_id,
            "snapshot_id": self.snapshot_id,
            "audit_id": self.audit_id,
            "repo_root": self.repo_root,
            "website_url": self.website_url,
            "persistent": dict(self.persistent),
        }


@dataclass
class BriefingState:
    suggested_next_capability: str | None = None
    suggested_semantic_action: str | None = None
    compiled_step_preview: dict[str, Any] | None = None
    stop_reason: str | None = None
    routing_rationale: str | None = None
    benefit_claim: str | None = None
    skip_condition: str | None = None
    investment: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "suggested_next_capability": self.suggested_next_capability,
            "suggested_semantic_action": self.suggested_semantic_action,
            "compiled_step_preview": self.compiled_step_preview,
            "stop_reason": self.stop_reason,
            "routing_rationale": self.routing_rationale,
            "benefit_claim": self.benefit_claim,
            "skip_condition": self.skip_condition,
            "investment": dict(self.investment) if self.investment else None,
        }


@dataclass
class ProjectSituationModel:
    """Live project situation — single source of truth for the coordinator."""

    schema_version: str = "1.0"
    episode_id: str = field(default_factory=_new_episode_id)
    project_id: str = "default"
    updated_at: str = field(default_factory=_utc_now)
    situation: SituationState = field(default_factory=SituationState)
    evidence: EvidenceState = field(default_factory=EvidenceState)
    constraints: ConstraintsState = field(default_factory=ConstraintsState)
    episode: EpisodeState = field(default_factory=EpisodeState)
    artifacts: ArtifactsState = field(default_factory=ArtifactsState)
    briefing: BriefingState = field(default_factory=BriefingState)

    def to_dict(self) -> dict[str, Any]:
        base = {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "project_id": self.project_id,
            "updated_at": self.updated_at,
            "situation": self.situation.to_dict(),
            "evidence": self.evidence.to_dict(),
            "constraints": self.constraints.to_dict(),
            "episode": self.episode.to_dict(),
            "artifacts": self.artifacts.to_dict(),
            "briefing": self.briefing.to_dict(),
        }
        return base

    def touch(self) -> None:
        self.updated_at = _utc_now()


@dataclass
class GateResult:
    allowed: bool
    capability_id: str
    reason: str | None = None
    gather_first: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "capability_id": self.capability_id,
            "reason": self.reason,
            "gather_first": self.gather_first,
        }


@dataclass
class CompiledStep:
    capability_id: str
    semantic_action: str
    step_id: str | None
    tools: list[dict[str, Any]]
    playbook_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "semantic_action": self.semantic_action,
            "step_id": self.step_id,
            "tools": self.tools,
            "playbook_id": self.playbook_id,
        }


@dataclass
class CoordinatorBriefing:
    episode_id: str
    stop_reason: str | None
    suggested_capability: str | None
    suggested_semantic_action: str | None
    compiled_step: CompiledStep | None
    psm_summary: dict[str, Any]
    routing_rationale: str | None = None
    benefit_claim: str | None = None
    skip_condition: str | None = None
    investment: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "stop_reason": self.stop_reason,
            "suggested_capability": self.suggested_capability,
            "suggested_semantic_action": self.suggested_semantic_action,
            "compiled_step": self.compiled_step.to_dict() if self.compiled_step else None,
            "psm_summary": self.psm_summary,
            "routing_rationale": self.routing_rationale,
            "benefit_claim": self.benefit_claim,
            "skip_condition": self.skip_condition,
            "investment": dict(self.investment) if self.investment else None,
        }


def posture_rank(posture: str) -> int:
    if posture == POSTURE_REGRESSED:
        return 2
    try:
        return POSTURE_ORDER.index(posture)
    except ValueError:
        return 0


def posture_meets_min(current: str, minimum: str) -> bool:
    if current == POSTURE_REGRESSED:
        return minimum in (POSTURE_REGRESSED, "partial")
    return posture_rank(current) >= posture_rank(minimum)
