"""Timeout policies — per-tool deterministic limits."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TimeoutPolicy:
    default_seconds: float = 60.0
    per_tool_seconds: dict[str, float] = field(default_factory=dict)

    def timeout_for(self, tool: str) -> float:
        if tool in self.per_tool_seconds:
            return self.per_tool_seconds[tool]
        if tool.startswith("perception_audit_") or tool == "perception_full_diagnosis":
            return 120.0
        if tool == "perception_health":
            return 10.0
        if tool in ("perception_seo_audit", "perception_seo_verify"):
            return 90.0
        return self.default_seconds


DEFAULT_TIMEOUT_POLICY = TimeoutPolicy(
    per_tool_seconds={
        "perception_health": 10.0,
        "perception_flow_describe": 15.0,
        "perception_code_context": 30.0,
    },
)
