"""Offline validation of deterministic runtime retrieval + graph traversal."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import GRAPHS, KB_ROOT, REPORTS, RUNTIME


@dataclass
class Scenario:
	name: str
	filters: dict[str, list[str]]
	expect_pack: str | None = None
	min_claims: int = 4
	min_decisions: int = 1
	adversarial: bool = False
	notes: str = ""


SCENARIOS: list[Scenario] = [
	# Core surface types
	Scenario("Build SaaS analytics dashboard", {"surface_type": ["dashboard"], "product_type": ["saas"]}, "pack_dashboard"),
	Scenario("Improve onboarding flow", {"user_flow": ["onboarding"], "surface_type": ["onboarding"]}, "pack_onboarding"),
	Scenario("Design pricing page", {"surface_type": ["landing"], "user_flow": ["conversion"]}, "pack_landing"),
	Scenario("Enterprise settings IA", {"surface_type": ["settings"], "product_type": ["enterprise"]}, "pack_information_architecture"),
	Scenario("Checkout form errors", {"surface_type": ["checkout"], "user_flow": ["checkout"]}, "pack_forms"),
	Scenario("Navigation hierarchy app shell", {"surface_type": ["app_shell"], "user_flow": ["navigation"]}, "pack_navigation"),
	Scenario("Accessibility audit hotfix", {"surface_type": ["all"], "user_flow": ["forms"]}, "pack_accessibility"),
	Scenario("Admin data table clarity", {"surface_type": ["admin"], "product_type": ["enterprise"]}, "pack_dashboard"),
	Scenario("Marketing landing readability", {"surface_type": ["marketing"], "user_flow": ["browse"], "problem": ["reading flow"]}, "pack_landing"),
	Scenario("Signup flow friction", {"surface_type": ["forms"], "user_flow": ["signup"]}, "pack_forms"),
	Scenario("Modal error recovery", {"ui_component": ["modal"], "surface_type": ["forms"]}, "pack_forms"),
	Scenario("Sidebar hierarchy dashboard", {"surface_type": ["dashboard"], "ui_component": ["sidebar"]}, "pack_dashboard"),
	# Psychology / cognitive
	Scenario("Reduce cognitive load in feature UI", {"psychology_category": ["cognitive_load"]}, "pack_psychology"),
	Scenario("Motor ergonomics for touch UI", {"psychology_category": ["motor_ergonomics"]}, "pack_accessibility"),
	Scenario("Feedback systems for async actions", {"surface_type": ["dashboard"], "problem": ["feedback"]}, "pack_dashboard"),
	# Forms depth
	Scenario("Multi-step wizard onboarding", {"surface_type": ["onboarding"], "ui_component": ["wizard"]}, "pack_onboarding"),
	Scenario("Inline validation signup form", {"surface_type": ["forms"], "user_flow": ["signup"], "ui_component": ["textfield"]}, "pack_forms"),
	Scenario("Password field visibility toggle", {"surface_type": ["forms"], "ui_component": ["textfield"]}, "pack_forms"),
	Scenario("Guest checkout minimal fields", {"surface_type": ["checkout"], "user_flow": ["checkout"], "product_type": ["ecommerce"]}, "pack_forms"),
	# Navigation / IA
	Scenario("Mega menu for large catalog", {"surface_type": ["marketing"], "user_flow": ["browse"]}, "pack_navigation"),
	Scenario("Sticky nav on marketing site", {"surface_type": ["marketing"], "ui_component": ["nav"]}, "pack_navigation"),
	Scenario("Settings page grouped sections", {"surface_type": ["settings"], "user_flow": ["configuration"]}, "pack_information_architecture"),
	Scenario("Dashboard KPI hierarchy", {"surface_type": ["dashboard"], "problem": ["information hierarchy"]}, "pack_dashboard"),
	# Landing / conversion
	Scenario("Hero CTA placement landing", {"surface_type": ["landing"], "user_flow": ["conversion"]}, "pack_landing"),
	Scenario("F-pattern text-heavy landing", {"surface_type": ["landing"], "problem": ["reading flow"]}, "pack_landing"),
	Scenario("Mobile landing touch targets", {"surface_type": ["landing"], "platform": ["mobile"]}, "pack_landing"),
	# Onboarding
	Scenario("First-run empty state onboarding", {"surface_type": ["onboarding"], "user_flow": ["onboarding"]}, "pack_onboarding"),
	Scenario("Peak-end onboarding finish", {"user_flow": ["onboarding"], "psychology_category": ["cognitive_load"]}, "pack_onboarding"),
	# Accessibility
	Scenario("WCAG contrast fix polish", {"surface_type": ["all"], "phase": ["polish"]}, "pack_accessibility"),
	Scenario("Focus visible keyboard nav", {"surface_type": ["app_shell"], "problem": ["accessibility"]}, "pack_accessibility"),
	Scenario("44px touch target hotfix", {"surface_type": ["all"], "phase": ["hotfix"]}, "pack_accessibility"),
	# Adversarial / edge routing
	Scenario(
		"Generic web app greenfield",
		{"surface_type": ["app_shell"], "phase": ["greenfield"]},
		adversarial=True,
		notes="No single obvious pack — should still return useful pack",
	),
	Scenario(
		"Ecommerce product browse",
		{"surface_type": ["marketing"], "product_type": ["ecommerce"], "user_flow": ["browse"]},
		"pack_navigation",
	),
	Scenario(
		"Enterprise admin analytics",
		{"surface_type": ["admin", "analytics"], "product_type": ["enterprise"]},
		"pack_dashboard",
		adversarial=True,
		notes="Multi surface_type — tests filter scoring",
	),
	Scenario(
		"Conflicting density vs a11y",
		{"surface_type": ["dashboard"], "problem": ["density", "accessibility"]},
		adversarial=True,
		min_claims=4,
		notes="Should surface conflict_pairs in pack",
	),
	Scenario(
		"Settings mistaken for dashboard",
		{"surface_type": ["settings"], "product_type": ["saas"]},
		"pack_information_architecture",
		adversarial=True,
		notes="Regression: settings must not route to pack_dashboard",
	),
]


def load_packs() -> list[dict[str, Any]]:
	packs: list[dict[str, Any]] = []
	for path in sorted(RUNTIME.glob("pack_*.json")):
		try:
			p = json.loads(path.read_text(encoding="utf-8"))
			p["_path"] = str(path)
			packs.append(p)
		except Exception:
			continue
	return packs


def load_graph() -> tuple[dict[str, dict], list[dict]]:
	nodes_path = GRAPHS / "nodes.json"
	edges_path = GRAPHS / "edges.json"
	if not nodes_path.exists() or not edges_path.exists():
		return {}, []
	nodes = {n["id"]: n for n in json.loads(nodes_path.read_text(encoding="utf-8"))}
	edges = json.loads(edges_path.read_text(encoding="utf-8"))
	return nodes, edges


def score_pack(pack: dict[str, Any], filters: dict[str, list[str]]) -> int:
	keys = pack.get("retrieval_keys") or {}
	score = 0
	for k, vals in filters.items():
		pv = keys.get(k) or []
		if k == "surface_type" and "all" in pv and vals:
			# Wildcard surface — weaker than explicit surface_type on specialized packs
			score += 1
			continue
		if any(v in pv for v in vals):
			score += 2
		elif k == "surface_type" and any(v in (pack.get("target_surfaces") or []) for v in vals):
			score += 1
		elif k == "phase" and any(v in (pack.get("target_surfaces") or []) for v in vals):
			score += 1
		elif k == "phase" and any(v in pv for v in vals):
			score += 2
	score += 1 if pack.get("playbook_id") else 0
	score += 1 if pack.get("pattern_refs") else 0
	score += 1 if pack.get("claim_stubs") else 0
	return score


def traverse_playbook(
	pb_id: str | None,
	nodes: dict[str, dict],
	edges: list[dict],
) -> dict[str, Any]:
	if not pb_id:
		return {"decisions": 0, "patterns": 0, "principles": 0, "path_ok": False}

	decisions = [
		e["target"]
		for e in edges
		if e.get("source") == pb_id and e.get("relation") == "decision_in"
	]
	patterns: set[str] = set()
	principles: set[str] = set()

	for dec_id in decisions:
		for e in edges:
			if e.get("source") == dec_id and e.get("relation") == "selects_pattern":
				patterns.add(e["target"])
		for e in edges:
			if e.get("source") in patterns and e.get("relation") == "pattern_of":
				principles.add(e["target"])

	path_ok = len(decisions) > 0 and (len(patterns) > 0 or len(principles) > 0)
	return {
		"decisions": len(decisions),
		"patterns": len(patterns),
		"principles": len(principles),
		"decision_ids": decisions[:5],
		"path_ok": path_ok,
	}


def evaluate_retrieval() -> dict[str, Any]:
	"""Run full retrieve() pipeline for each scenario."""
	from .retrieve import RetrievalRequest, retrieve

	results: list[dict[str, Any]] = []
	ok = 0
	for s in SCENARIOS:
		req = RetrievalRequest(intent=s.name, **{k: (v[0] if len(v) == 1 else v) for k, v in s.filters.items()})
		out = retrieve(req)
		has_pb = bool(out.get("matched_playbook", {}).get("id"))
		has_principles = len(out.get("principles") or []) >= s.min_claims
		has_decisions = len(out.get("decisions") or []) >= s.min_decisions
		pack_id = out.get("meta", {}).get("pack_id")
		pack_match = s.expect_pack is None or pack_id == s.expect_pack
		passing = has_pb and has_principles and has_decisions and pack_match
		if passing:
			ok += 1
		results.append(
			{
				"scenario": s.name,
				"pass": passing,
				"pack_id": pack_id,
				"expect_pack": s.expect_pack,
				"decisions": len(out.get("decisions") or []),
				"patterns": len(out.get("patterns") or []),
				"principles": len(out.get("principles") or []),
				"conflicts": len(out.get("conflicts") or []),
				"evidence": len(out.get("evidence") or []),
				"traversal": out.get("meta", {}).get("traversal_path"),
			}
		)
	return {
		"scenarios": len(SCENARIOS),
		"retrieval_pass": ok,
		"retrieval_coverage": round(ok / max(1, len(SCENARIOS)), 3),
		"results": results,
	}


def evaluate() -> dict[str, Any]:
	packs = load_packs()
	nodes, edges = load_graph()
	results: list[dict[str, Any]] = []
	useful = 0
	pack_hits = 0
	traversal_ok = 0
	failures: list[str] = []

	for s in SCENARIOS:
		scored = sorted(((score_pack(p, s.filters), p) for p in packs), key=lambda x: x[0], reverse=True)
		best_score, best = scored[0] if scored else (0, None)
		top3 = [(sc, p.get("pack_id")) for sc, p in scored[:3]]

		claims = len(best.get("claim_stubs") or []) if best else 0
		conflicts = len(best.get("conflict_pairs") or []) if best else 0
		pb_id = best.get("playbook_id") if best else None
		trav = traverse_playbook(pb_id, nodes, edges)

		is_useful = bool(best and best_score >= 4 and claims >= s.min_claims)
		pack_match = bool(s.expect_pack and best and best.get("pack_id") == s.expect_pack)
		trav_pass = trav["decisions"] >= s.min_decisions and trav["path_ok"]

		if is_useful:
			useful += 1
		if pack_match:
			pack_hits += 1
		elif s.expect_pack:
			failures.append(f"{s.name}: expected {s.expect_pack}, got {best.get('pack_id') if best else None}")
		if trav_pass:
			traversal_ok += 1
		elif pb_id:
			failures.append(
				f"{s.name}: weak traversal ({trav['decisions']} decisions, {trav['patterns']} patterns)"
			)
		if s.adversarial and s.name.startswith("Conflicting") and conflicts < 1:
			failures.append(f"{s.name}: expected conflict_pairs, got {conflicts}")

		results.append(
			{
				"scenario": s.name,
				"filters": s.filters,
				"expect_pack": s.expect_pack,
				"top_pack": best.get("pack_id") if best else None,
				"score": best_score,
				"top3": top3,
				"useful": is_useful,
				"pack_match": pack_match,
				"playbook_id": pb_id,
				"claims": claims,
				"patterns_in_pack": len(best.get("pattern_refs") or []) if best else 0,
				"conflicts": conflicts,
				"traversal": trav,
				"traversal_ok": trav_pass,
				"adversarial": s.adversarial,
				"notes": s.notes,
			}
		)

	n = len(SCENARIOS)
	expected = sum(1 for s in SCENARIOS if s.expect_pack)
	return {
		"scenarios": n,
		"useful_hits": useful,
		"useful_coverage": round(useful / max(1, n), 3),
		"pack_match_hits": pack_hits,
		"pack_match_coverage": round(pack_hits / max(1, expected), 3) if expected else None,
		"traversal_ok": traversal_ok,
		"traversal_coverage": round(traversal_ok / max(1, n), 3),
		"failures": failures,
		"results": results,
		"retrieval_engine": evaluate_retrieval(),
	}


def evaluate_and_write() -> Path:
	REPORTS.mkdir(parents=True, exist_ok=True)
	report = evaluate()
	path = REPORTS / "runtime_eval.json"
	path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
	# Human-readable summary
	md_lines = [
		"# Runtime Eval — offline retrieval",
		"",
		f"- Scenarios: {report['scenarios']}",
		f"- Useful coverage: {report['useful_coverage']:.0%} ({report['useful_hits']}/{report['scenarios']})",
		f"- Pack match: {report['pack_match_coverage']:.0%} ({report['pack_match_hits']}/{sum(1 for s in SCENARIOS if s.expect_pack)})" if report.get("pack_match_coverage") is not None else "",
		f"- Traversal ok: {report['traversal_coverage']:.0%} ({report['traversal_ok']}/{report['scenarios']})",
	]
	re = report.get("retrieval_engine") or {}
	md_lines.append(
		f"- **Retrieval engine pass:** {re.get('retrieval_coverage', 0):.0%} ({re.get('retrieval_pass', 0)}/{report['scenarios']})"
	)
	md_lines += ["", "## Pack filter failures", ""]
	for f in report.get("failures") or []:
		md_lines.append(f"- {f}")
	if not report.get("failures"):
		md_lines.append("- None")
	re_fail = [r for r in re.get("results", []) if not r.get("pass")]
	if re_fail:
		md_lines += ["", "## Retrieval engine failures", ""]
		for r in re_fail:
			md_lines.append(f"- {r['scenario']}: pack={r.get('pack_id')} expected={r.get('expect_pack')}")
	md_path = REPORTS / "RUNTIME_EVAL.md"
	md_path.write_text("\n".join(md_lines), encoding="utf-8")
	return path


def main() -> None:
	path = evaluate_and_write()
	print(json.dumps({"report_path": str(path)}, indent=2))


if __name__ == "__main__":
	main()
