"""Step Compiler — semantic actions + PSM Runtime → MCP tool invocations."""

from __future__ import annotations

import re
from typing import Any

from navigation.coordination_intelligence.artifacts.loader import RuntimeArtifactBundle
from navigation.coordination_intelligence.models import CompiledStep, ProjectSituationModel

_TEMPLATE = re.compile(r"^\$([a-zA-Z0-9_.]+)$")


class StepCompiler:
    def __init__(self, bundle: RuntimeArtifactBundle) -> None:
        self._bundle = bundle

    def compile_step(
        self,
        psm: ProjectSituationModel,
        *,
        semantic_action: str,
        capability_id: str,
        step_id: str | None = None,
        step_context: dict[str, Any] | None = None,
        playbook_id: str | None = None,
    ) -> CompiledStep | None:
        binding = self._bundle.bindings_by_semantic_action.get(semantic_action)
        if not binding:
            bindings = self._bundle.bindings_by_capability.get(capability_id) or []
            binding = bindings[0] if bindings else None
        if not binding:
            return None

        ctx = dict(step_context or {})
        ctx.setdefault("url_present", bool(ctx.get("url")))
        ctx.setdefault("url_absent", not bool(ctx.get("url")))
        ctx.setdefault("actions_present", bool(ctx.get("actions")))
        ctx.setdefault("script_present", bool(ctx.get("script")))
        ctx.setdefault("actions_before_verify", bool(ctx.get("actions")))

        tools_out: list[dict[str, Any]] = []
        for tool_spec in binding.get("tools") or []:
            when = tool_spec.get("when")
            if when and not self._when_matches(when, ctx):
                continue
            resolved = {
                "tool": tool_spec["tool"],
                "arguments": self._resolve_args(
                    tool_spec.get("arg_template") or {},
                    psm,
                    ctx,
                ),
            }
            tools_out.append(resolved)

        return CompiledStep(
            capability_id=capability_id,
            semantic_action=semantic_action,
            step_id=step_id,
            tools=tools_out,
            playbook_id=playbook_id,
        )

    def _when_matches(self, when: str, ctx: dict[str, Any]) -> bool:
        return bool(ctx.get(when))

    def _resolve_args(
        self,
        template: dict[str, Any],
        psm: ProjectSituationModel,
        step_context: dict[str, Any],
    ) -> dict[str, Any]:
        psm_dict = psm.to_dict()
        out: dict[str, Any] = {}
        for key, value in template.items():
            out[key] = self._resolve_value(value, psm_dict, step_context)
        return out

    def _resolve_value(
        self,
        value: Any,
        psm_dict: dict[str, Any],
        step_context: dict[str, Any],
    ) -> Any:
        if isinstance(value, str):
            m = _TEMPLATE.match(value)
            if m:
                return self._lookup_path(m.group(1), psm_dict, step_context)
        if isinstance(value, dict):
            return {k: self._resolve_value(v, psm_dict, step_context) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_value(v, psm_dict, step_context) for v in value]
        return value

    @staticmethod
    def _lookup_path(path: str, psm_dict: dict[str, Any], step_context: dict[str, Any]) -> Any:
        if path.startswith("step."):
            return step_context.get(path[5:])
        parts = path.split(".")
        cur: Any = psm_dict
        for part in parts:
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur
