"""Minimal PSM-like structures for the Coordination Sandbox.

Copied / adapted from production coordination_intelligence.models for isolation.
Do not import production navigation packages from the sandbox.
"""
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def posture_meets_min(posture: str, minimum: str) -> bool:
    order = ("unknown", "partial", "known", "verified")
    if posture == "regressed":
        return False
    try:
        return order.index(posture) >= order.index(minimum)
    except ValueError:
        return False


@dataclass
class EvidenceDomainState:
    posture: str = "unknown"
    source_capability: str | None = None


@dataclass
class IntentFrame:
    intent: str
    pushed_at: str = field(default_factory=_utc_now)


@dataclass
class SituationState:
    situation_class: str = "new_feature"
    lifecycle_stage: str = "S05_implementation"
    project_maturity: str = "M3"
    cluster_id: str = "cluster.feature.generic"


@dataclass
class EvidenceState:
    domains: dict[str, EvidenceDomainState] = field(default_factory=dict)
    blocking: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.domains:
            self.domains = {d: EvidenceDomainState() for d in EVIDENCE_DOMAINS}


@dataclass
class ArtifactState:
    scan_id: str | None = None
    persistent: dict[str, Any] = field(default_factory=dict)


@dataclass
class BriefingState:
    routing_rationale: str | None = None
    benefit_claim: str | None = None
    skip_condition: str | None = None
    investment: dict[str, Any] | None = None
    suggested_next_capability: str | None = None
    suggested_semantic_action: str | None = None
    stop_reason: str | None = None


@dataclass
class EpisodeState:
    episode_id: str = field(default_factory=lambda: f"sim_{uuid4().hex[:12]}")
    intent_stack: list[IntentFrame] = field(default_factory=list)
    verification_status: str = "unknown"
    completed_step_ids: list[str] = field(default_factory=list)
    retry_counters: dict[str, Any] = field(default_factory=dict)
    active_playbook_id: str | None = None
    active_step_id: str | None = None


@dataclass
class ConstraintsState:
    human_gates: list[str] = field(default_factory=list)


@dataclass
class ProjectSituationModel:
    """Sandbox PSM — advisory only, never drives MCP."""

    situation: SituationState = field(default_factory=SituationState)
    evidence: EvidenceState = field(default_factory=EvidenceState)
    artifacts: ArtifactState = field(default_factory=ArtifactState)
    episode: EpisodeState = field(default_factory=EpisodeState)
    briefing: BriefingState = field(default_factory=BriefingState)
    constraints: ConstraintsState = field(default_factory=ConstraintsState)

    def push_intent(self, intent: str) -> None:
        self.episode.intent_stack.append(IntentFrame(intent=intent))
