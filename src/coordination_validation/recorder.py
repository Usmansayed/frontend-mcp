"""Record coordinator decisions during validation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionRecord:
    step_index: int
    tool: str
    ok: bool
    capability_id: str | None
    expected_capability: str | None
    cluster_id: str | None
    playbook_id: str | None
    active_step_id: str | None
    suggested_capability: str | None
    suggested_semantic_action: str | None
    stop_reason: str | None
    compiled_tools: list[str]
    governor_advanced: bool
    psm_snapshot: dict[str, Any]
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "tool": self.tool,
            "ok": self.ok,
            "capability_id": self.capability_id,
            "expected_capability": self.expected_capability,
            "cluster_id": self.cluster_id,
            "playbook_id": self.playbook_id,
            "active_step_id": self.active_step_id,
            "suggested_capability": self.suggested_capability,
            "suggested_semantic_action": self.suggested_semantic_action,
            "stop_reason": self.stop_reason,
            "compiled_tools": self.compiled_tools,
            "governor_advanced": self.governor_advanced,
            "psm_snapshot": self.psm_snapshot,
            "timestamp": self.timestamp,
        }


class DecisionRecorder:
    def __init__(self) -> None:
        self.decisions: list[DecisionRecord] = []
        self._completed_before: list[str] = []

    def record(
        self,
        *,
        step_index: int,
        tool: str,
        envelope: dict[str, Any],
        psm: dict[str, Any],
        expected_capability: str | None,
        capability_id: str | None,
        governor_advanced: bool,
    ) -> None:
        coord = (envelope.get("data") or {}).get("coordinator") or {}
        briefing = coord.get("briefing") or {}
        compiled = briefing.get("compiled_step") or coord.get("compiled_step") or {}
        tools = [t.get("tool") for t in (compiled.get("tools") or []) if t.get("tool")]
        episode = psm.get("episode") or {}
        situation = psm.get("situation") or {}
        self.decisions.append(
            DecisionRecord(
                step_index=step_index,
                tool=tool,
                ok=bool(envelope.get("ok")),
                capability_id=capability_id
                or (psm.get("episode") or {}).get("retry_counters", {}).get("last_capability"),
                expected_capability=expected_capability,
                cluster_id=situation.get("cluster_id"),
                playbook_id=episode.get("active_playbook_id"),
                active_step_id=episode.get("active_step_id"),
                suggested_capability=briefing.get("suggested_capability")
                or coord.get("suggested_capability"),
                suggested_semantic_action=briefing.get("suggested_semantic_action")
                or coord.get("suggested_semantic_action"),
                stop_reason=briefing.get("stop_reason") or coord.get("stop_reason"),
                compiled_tools=tools,
                governor_advanced=governor_advanced,
                psm_snapshot={
                    "cluster_id": situation.get("cluster_id"),
                    "lifecycle_stage": situation.get("lifecycle_stage"),
                    "completed_step_ids": list(episode.get("completed_step_ids") or []),
                    "verification_status": episode.get("verification_status"),
                    "blocking_count": len((psm.get("evidence") or {}).get("blocking") or []),
                    "capability_posture": situation.get("capability_posture"),
                },
            )
        )

    def psm_timeline(self) -> list[dict[str, Any]]:
        return [d.psm_snapshot for d in self.decisions]

    def cluster_transitions(self) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        prev: str | None = None
        for d in self.decisions:
            cid = d.cluster_id
            if cid and cid != prev:
                if prev is not None:
                    out.append((prev, cid))
                prev = cid
        return out
