"""Human-readable + JSON reporting for sandbox simulations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from coordination_sandbox.simulator.engine import ScenarioResult


def format_text_report(result: ScenarioResult) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append(f"PROMPT: {result.prompt}")
    lines.append("=" * 72)
    lines.append(result.tech_lead_summary)
    lines.append("")
    lines.append(f"Project state:          {result.project_state}")
    lines.append(f"Lifecycle stage:        {result.lifecycle_stage}")
    lines.append(f"Situation policy (start): {result.initial_situation_policy_id}")
    lines.append(f"Situation policy (end):   {result.situation_policy_id}")
    lines.append(f"Investment band:        {result.investment_band}")
    lines.append(f"Engineering Investment: B_base={result.engineering_investment_b_base}")
    lines.append(f"Visual impact ceiling:  {result.visual_impact_ceiling}")
    lines.append(
        f"Budget:                 spent={result.budget_spent} remaining={result.budget_remaining} / total={result.budget_total}"
    )
    lines.append(f"Initial discriminators: {result.initial_discriminators}")
    lines.append(f"Final discriminators:   {result.discriminators}")
    lines.append(f"Playbook:               {result.recommended_playbook}")
    lines.append(f"  reason:               {result.playbook_reason}")
    lines.append(f"Design-oriented:        {result.design_oriented}")
    lines.append(f"Recommended caps:       {result.recommended_capabilities}")
    lines.append(f"Semantic actions:       {result.recommended_semantic_actions}")
    lines.append(f"EQG (value):            {result.estimated_engineering_value}")
    lines.append(f"Est. latency (ms):      {result.estimated_latency_ms_total}")
    lines.append(f"STOP:                   {result.stop_recommendations}")
    lines.append(f"Diminishing returns:    {result.diminishing_returns}")
    lines.append("")
    lines.append("SKIPPED CAPABILITIES")
    lines.append("-" * 72)
    if not result.skipped:
        lines.append("  (none)")
    for s in result.skipped:
        lines.append(
            f"  - {s['capability_id']}: {s['reason']} | roi={s['roi']} eqg={s['eqg']} cost={s['cost']}"
        )
        lines.append(f"    why: {s['routing_rationale']}")
    lines.append("")
    lines.append("DECISION TRACE")
    lines.append("-" * 72)
    for step in result.decision_trace:
        lines.append(
            f"[{step['step_index']:02d}] {step['action'].upper():6} {step['capability_id']}"
            f"  eqg={step['eqg']} cost={step['cost']} roi={step['roi']} "
            f"budget_rem={step['budget_remaining']} latency_ms={step['estimated_latency_ms']}"
        )
        lines.append(f"     semantic: {step['semantic_action']}")
        lines.append(f"     plan: {step['plan_rationale']}")
        lines.append(f"     why:  {step['routing_rationale']}")
        if step.get("effects"):
            lines.append(f"     effects: {step['effects']}")
        if step.get("stop_reason"):
            lines.append(f"     stop: {step['stop_reason']}")
    lines.append("")
    return "\n".join(lines)


def write_json(result: ScenarioResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def append_jsonl(result: ScenarioResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")


def load_scenarios_yaml(path: Path) -> list[dict[str, Any]]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(data.get("scenarios") or [])
