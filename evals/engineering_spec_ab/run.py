"""A/B harness — does FrontendEngineeringSpec change host planning?

Simulates two planners (without Spec vs with Spec) against the same engineering task
and scores whether high-impact Spec decisions appear in the implementation plan.

This is NOT a live Cursor agent loop. It measures Spec influence on planning artifacts
deterministically so we can iterate the Knowledge Compiler before spending week-long
human A/B sessions.

Usage:
  python -m evals.engineering_spec_ab.run
  python -m evals.engineering_spec_ab.run --scenario saas_dashboard
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from navigation.design_snapshot_engine import DesignSnapshotEngine
from navigation.engineering_knowledge import (
    compile_inspiration_seed_spec,
    compile_live_spec,
    diff_specs,
)
from navigation.engineering_knowledge.catalog import catalog_by_id

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "output"


@dataclass
class PlanArtifact:
    mode: str  # without_spec | with_spec
    task: str
    bullets: list[str] = field(default_factory=list)
    decisions_cited: list[str] = field(default_factory=list)
    adjectives_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioResult:
    scenario_id: str
    task: str
    without_spec: dict[str, Any]
    with_spec: dict[str, Any]
    score_without: float
    score_with: float
    influence_gain: float
    critical_decisions: list[str]
    covered_without: list[str]
    covered_with: list[str]
    spec_summary: dict[str, Any]
    engineering_delta: dict[str, Any] | None
    passed: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_GENERIC_ADJECTIVES = (
    "clean",
    "modern",
    "minimal",
    "sleek",
    "beautiful",
    "nice",
    "linear-like",
    "polished",
)


def plan_without_spec(task: str) -> PlanArtifact:
    """Simulate typical host plan when only screenshots/tags are available."""
    bullets = [
        f"Build a clean, modern UI for: {task}",
        "Use a minimal, polished aesthetic (Linear-like)",
        "Pick a nice color palette and good typography",
        "Add a sidebar or top nav depending on feel",
        "Use comfortable spacing and card layouts",
        "Ship a beautiful first version then iterate",
    ]
    adjectives = [a for a in _GENERIC_ADJECTIVES if any(a in b.lower() for b in bullets)]
    return PlanArtifact(
        mode="without_spec",
        task=task,
        bullets=bullets,
        decisions_cited=[],
        adjectives_used=adjectives,
    )


def plan_with_spec(task: str, spec: dict[str, Any]) -> PlanArtifact:
    """Simulate host plan constrained by FrontendEngineeringSpec decisions."""
    decisions = spec.get("decisions") or {}
    bullets: list[str] = [f"Implement '{task}' from FrontendEngineeringSpec (V1 Pareto)."]
    cited: list[str] = []

    def cite(did: str, text: str) -> None:
        dec = decisions.get(did) or {}
        if dec.get("status") in ("resolved", "partial") and dec.get("value") is not None:
            bullets.append(text.format(value=dec.get("value"), conf=dec.get("confidence")))
            cited.append(did)
        elif (dec.get("importance") in ("critical", "high")) and dec.get("status") == "unresolved":
            bullets.append(
                f"BLOCKED on {did} (impact={dec.get('impact_weight')}): {dec.get('why')}"
            )
            cited.append(did)

    cite("layout.archetype", "Layout archetype={value} (conf={conf})")
    cite("layout.sidebar_width_px", "Sidebar width={value}px")
    cite("layout.header_height_px", "Header height={value}px")
    cite("nav.pattern", "Navigation pattern={value}")
    cite("hierarchy.primary_focus", "Primary focus copy/target='{value}'")
    cite("spacing.base_unit_px", "Spacing base unit={value}px")
    cite("type.font_families", "Font stack={value}")
    cite("type.heading_scale_px", "Heading scale(px)={value}")
    cite("type.body_size_px", "Body size={value}px")
    cite("color.accent", "Accent color={value}")
    cite("color.background", "Background={value}")
    cite("density.band", "Visual density band={value}")
    cite("component.foundation_status", "Component foundation={value}")

    bullets.append("Do not invent alternate layout/spacing/type once Spec decisions are resolved.")
    return PlanArtifact(
        mode="with_spec",
        task=task,
        bullets=bullets,
        decisions_cited=cited,
        adjectives_used=[],
    )


def score_plan_against_spec(plan: PlanArtifact, spec: dict[str, Any]) -> tuple[float, list[str]]:
    """Fraction of critical/high impact decisions reflected in the plan."""
    catalog = catalog_by_id()
    decisions = spec.get("decisions") or {}
    targets: list[str] = []
    for did, dec in decisions.items():
        meta = catalog.get(did)
        importance = (meta.importance if meta else dec.get("importance")) or "medium"
        if importance in ("critical", "high"):
            if dec.get("status") in ("resolved", "partial", "unresolved"):
                targets.append(did)

    if not targets:
        return 0.0, []

    text = " ".join(plan.bullets).lower()
    covered: list[str] = []
    for did in targets:
        token = did.split(".")[-1].replace("_", " ")
        if did in plan.decisions_cited or did in text or token in text:
            covered.append(did)
            continue
        # value mention
        val = (decisions.get(did) or {}).get("value")
        if val is not None and str(val).lower() in text:
            covered.append(did)

    # Penalize adjective-only plans
    adj_penalty = min(0.35, 0.07 * len(plan.adjectives_used))
    raw = len(covered) / max(len(targets), 1)
    return round(max(0.0, raw - adj_penalty), 4), covered


def dashboard_fixture() -> dict[str, Any]:
    return {
        "url": "http://localhost:5173/dashboard",
        "viewport": {"width": 1440, "height": 900},
        "document": {"scrollWidth": 1440, "scrollHeight": 1200},
        "css_variables": {"--primary": "#4f46e5", "--spacing-4": "16px"},
        "elements": [
            {
                "tag": "nav",
                "selector": "nav",
                "text": "App",
                "classes": [],
                "rect": {"x": 0, "y": 0, "width": 280, "height": 900},
                "style": {
                    "fontSize": "14px",
                    "fontFamily": "Inter, sans-serif",
                    "color": "rgb(17,24,39)",
                    "backgroundColor": "rgb(249,250,251)",
                    "padding": "16px",
                },
            },
            {
                "tag": "header",
                "selector": "header",
                "text": "Overview",
                "classes": [],
                "rect": {"x": 280, "y": 0, "width": 1160, "height": 72},
                "style": {
                    "fontSize": "18px",
                    "fontFamily": "Inter, sans-serif",
                    "color": "rgb(17,24,39)",
                    "backgroundColor": "rgb(255,255,255)",
                    "padding": "16px",
                },
            },
            {
                "tag": "main",
                "selector": "main",
                "text": "",
                "classes": [],
                "rect": {"x": 280, "y": 72, "width": 1160, "height": 828},
                "style": {
                    "fontSize": "16px",
                    "fontFamily": "Inter, sans-serif",
                    "color": "rgb(55,65,81)",
                    "backgroundColor": "rgb(255,255,255)",
                    "padding": "24px",
                    "gap": "24px",
                },
            },
            {
                "tag": "h1",
                "selector": "h1",
                "text": "Revenue overview",
                "classes": [],
                "rect": {"x": 304, "y": 96, "width": 400, "height": 40},
                "style": {
                    "fontSize": "28px",
                    "fontFamily": "Inter, sans-serif",
                    "lineHeight": "36px",
                    "color": "rgb(17,24,39)",
                    "backgroundColor": "rgba(0,0,0,0)",
                },
            },
            {
                "tag": "button",
                "selector": "button",
                "text": "Export",
                "classes": ["primary"],
                "rect": {"x": 1200, "y": 20, "width": 90, "height": 36},
                "style": {
                    "fontSize": "14px",
                    "color": "#fff",
                    "backgroundColor": "#4f46e5",
                    "padding": "8px",
                },
            },
        ],
    }


SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "saas_dashboard",
        "task": "Build a SaaS dashboard",
        "fixture": "dashboard",
        "min_influence_gain": 0.35,
    },
    {
        "id": "landing_seed",
        "task": "Build a marketing landing page",
        "mode": "inspiration_seed",
        "query": "saas marketing landing page hero",
        "profiles": [{"page_type": "landing", "style": "marketing", "components": ["hero", "cta"]}],
        "min_influence_gain": 0.15,
    },
    {
        "id": "dashboard_drift",
        "task": "Review dashboard vs reference",
        "fixture": "dashboard",
        "mutate_sidebar": 200,
        "min_influence_gain": 0.35,
    },
]


def _ensure_regions(snapshot) -> None:
    roles = {r.get("role") for r in snapshot.layout.regions}
    needed = []
    if "nav" not in roles:
        needed.append({"role": "nav", "rect": {"width": 280, "height": 900}})
    if "header" not in roles:
        needed.append({"role": "header", "rect": {"width": 1160, "height": 72}})
    if "main" not in roles:
        needed.append({"role": "main", "rect": {"width": 1160, "height": 828}})
    if needed:
        snapshot.layout.regions = list(snapshot.layout.regions) + needed


def run_scenario(scenario: dict[str, Any]) -> ScenarioResult:
    task = scenario["task"]
    notes: list[str] = []
    engineering_delta = None

    if scenario.get("mode") == "inspiration_seed":
        spec_obj = compile_inspiration_seed_spec(
            query=str(scenario.get("query") or task),
            profiles=list(scenario.get("profiles") or []),
        )
        spec = spec_obj.to_dict()
        notes.append("Used inspiration seed Spec (soft priors only).")
    else:
        fixture = dashboard_fixture()
        snapshot = DesignSnapshotEngine().capture_from_fixture(fixture)
        _ensure_regions(snapshot)
        live = compile_live_spec(snapshot)
        if scenario.get("mutate_sidebar"):
            ref = compile_live_spec(snapshot)
            live.decisions["layout.sidebar_width_px"].value = int(scenario["mutate_sidebar"])
            engineering_delta = diff_specs(ref, live).to_dict()
            notes.append(
                f"Injected sidebar drift -> {scenario['mutate_sidebar']}px for SpecDiff check."
            )
        spec = live.to_dict()

    without = plan_without_spec(task)
    with_p = plan_with_spec(task, spec)
    score_wo, cov_wo = score_plan_against_spec(without, spec)
    score_w, cov_w = score_plan_against_spec(with_p, spec)
    gain = round(score_w - score_wo, 4)
    critical = [
        did
        for did, dec in (spec.get("decisions") or {}).items()
        if dec.get("importance") in ("critical", "high")
    ]
    min_gain = float(scenario.get("min_influence_gain") or 0.25)
    passed = gain >= min_gain and score_w > score_wo

    if engineering_delta and not engineering_delta.get("items"):
        notes.append("WARNING: expected SpecDiff items for drift scenario.")
        passed = False
    if engineering_delta and engineering_delta.get("items"):
        notes.append(
            f"SpecDiff items={engineering_delta['summary'].get('delta_count')} "
            f"major={engineering_delta['summary'].get('major_or_blocking')}"
        )

    return ScenarioResult(
        scenario_id=str(scenario["id"]),
        task=task,
        without_spec=without.to_dict(),
        with_spec=with_p.to_dict(),
        score_without=score_wo,
        score_with=score_w,
        influence_gain=gain,
        critical_decisions=critical,
        covered_without=cov_wo,
        covered_with=cov_w,
        spec_summary={
            "source_kind": spec.get("source_kind"),
            "coverage": spec.get("coverage"),
            "unresolved_by_impact": (spec.get("unresolved_by_impact") or [])[:5],
        },
        engineering_delta=engineering_delta,
        passed=passed,
        notes=notes,
    )


def run_all(scenario_id: str | None = None) -> dict[str, Any]:
    scenarios = SCENARIOS
    if scenario_id:
        scenarios = [s for s in SCENARIOS if s["id"] == scenario_id]
        if not scenarios:
            raise SystemExit(f"Unknown scenario: {scenario_id}")

    results = [run_scenario(s) for s in scenarios]
    passed = sum(1 for r in results if r.passed)
    report = {
        "passed": passed,
        "total": len(results),
        "pass_rate": round(passed / max(len(results), 1), 4),
        "results": [r.to_dict() for r in results],
        "verdict": (
            "Spec materially changes planning for measured scenarios."
            if passed == len(results)
            else "Some scenarios show weak Spec influence — improve compiler priors/values before expanding catalog."
        ),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Engineering Spec A/B planning harness")
    parser.add_argument("--scenario", default=None, help="Run a single scenario id")
    parser.add_argument("--out", default=None, help="Output JSON path")
    args = parser.parse_args()

    report = run_all(args.scenario)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else OUT_DIR / "ab_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("=" * 72)
    print(f"A/B Spec influence: {report['passed']}/{report['total']} passed ({report['pass_rate']})")
    print(report["verdict"])
    print("=" * 72)
    for r in report["results"]:
        flag = "PASS" if r["passed"] else "FAIL"
        print(
            f"[{flag}] {r['scenario_id']}: without={r['score_without']} "
            f"with={r['score_with']} gain={r['influence_gain']}"
        )
        for n in r.get("notes") or []:
            print(f"       note: {n}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
