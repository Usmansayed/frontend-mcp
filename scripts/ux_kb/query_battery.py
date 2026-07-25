"""Dev query battery — ~30 retrieval scenarios from micro forms to macro IA/sitemap flows."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import KB_ROOT, REPORTS


@dataclass
class QueryCase:
	id: str
	tier: str  # micro | meso | macro
	intent: str
	params: dict[str, Any]
	expect_pack: str | None = None
	expect_playbook: str | None = None
	min_principles: int = 3
	min_patterns: int = 2
	notes: str = ""


# 30 queries: micro (forms/a11y atoms) → meso (flows/components) → macro (layout/IA/sitemap)
QUERY_BATTERY: list[QueryCase] = [
	# ── MICRO (10) — field-level, validation, a11y atoms ──────────────────
	QueryCase(
		"q01_label_above_input",
		"micro",
		"Should form labels sit above or beside text inputs?",
		{"surface_type": "forms", "ui_component": "textfield", "phase": "greenfield"},
		expect_pack="pack_forms",
		expect_playbook="pb_forms",
	),
	QueryCase(
		"q02_inline_validation_blur",
		"micro",
		"When should inline validation fire on a signup field?",
		{"surface_type": "forms", "ui_component": "textfield", "user_flow": "signup"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q03_password_visibility_toggle",
		"micro",
		"Password field show/hide toggle UX",
		{"surface_type": "forms", "ui_component": "textfield", "problem": "form usability"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q04_radio_group_fieldset",
		"micro",
		"How to group radio buttons semantically for screen readers?",
		{"surface_type": "forms", "ui_component": "radio", "problem": "accessibility"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q05_aria_describedby_hint",
		"micro",
		"Associate helper text with an input using aria-describedby",
		{"surface_type": "forms", "ui_component": "form", "problem": "accessibility"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q06_error_message_placement",
		"micro",
		"Where should inline error messages appear relative to the field?",
		{"surface_type": "forms", "ui_component": "textfield", "user_flow": "signup"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q07_touch_target_44px",
		"micro",
		"Minimum touch target size for mobile form submit button",
		{"surface_type": "forms", "platform": "mobile", "phase": "hotfix"},
		expect_pack="pack_accessibility",
	),
	QueryCase(
		"q08_required_field_indicator",
		"micro",
		"How to mark required fields without relying on color alone",
		{"surface_type": "forms", "problem": "accessibility"},
		expect_pack="pack_accessibility",
	),
	QueryCase(
		"q09_checkbox_single_terms",
		"micro",
		"Single checkbox for terms acceptance — fieldset needed?",
		{"surface_type": "forms", "ui_component": "checkbox"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q10_select_autocomplete",
		"micro",
		"Country select dropdown accessibility and keyboard support",
		{"surface_type": "forms", "ui_component": "select"},
		expect_pack="pack_forms",
	),
	# ── MESO (10) — form flows, nav chunks, dashboard sections ────────────
	QueryCase(
		"q11_multi_step_wizard",
		"meso",
		"Multi-step checkout wizard with progress indicator",
		{"surface_type": "checkout", "ui_component": "wizard", "user_flow": "checkout"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q12_guest_checkout_minimal",
		"meso",
		"Guest checkout — minimize fields to reduce cognitive load",
		{"surface_type": "checkout", "user_flow": "checkout", "psychology_category": "cognitive_load"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q13_signup_form_friction",
		"meso",
		"Reduce signup form friction and abandonment",
		{"surface_type": "forms", "user_flow": "signup", "psychology_category": "cognitive_load"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q14_modal_confirm_destructive",
		"meso",
		"Confirmation modal before destructive delete action",
		{"surface_type": "dashboard", "ui_component": "modal", "problem": "feedback"},
		expect_pack="pack_dashboard",
	),
	QueryCase(
		"q15_sidebar_nav_dashboard",
		"meso",
		"Persistent sidebar navigation for analytics dashboard",
		{"surface_type": "dashboard", "ui_component": "sidebar", "user_flow": "navigation"},
		expect_pack="pack_dashboard",
	),
	QueryCase(
		"q16_kpi_card_hierarchy",
		"meso",
		"KPI cards with unequal visual weight — which metric is primary?",
		{"surface_type": "dashboard", "problem": "information hierarchy"},
		expect_pack="pack_dashboard",
	),
	QueryCase(
		"q17_sticky_marketing_nav",
		"meso",
		"Sticky top navigation on marketing site",
		{"surface_type": "marketing", "ui_component": "nav", "user_flow": "browse"},
		expect_pack="pack_navigation",
	),
	QueryCase(
		"q18_mega_menu_catalog",
		"meso",
		"Mega menu for large ecommerce product catalog",
		{"surface_type": "marketing", "user_flow": "browse", "product_type": "ecommerce"},
		expect_pack="pack_navigation",
	),
	QueryCase(
		"q19_onboarding_empty_state",
		"meso",
		"First-run empty state with guided first action",
		{"surface_type": "onboarding", "user_flow": "onboarding"},
		expect_pack="pack_onboarding",
	),
	QueryCase(
		"q20_async_action_feedback",
		"meso",
		"Loading and success feedback for async form submit",
		{"surface_type": "forms", "problem": "feedback", "user_flow": "signup"},
		expect_pack="pack_forms",
	),
	# ── MACRO (10) — layouts, IA, sitemap-level flows ─────────────────────
	QueryCase(
		"q21_single_column_form_layout",
		"macro",
		"Overall form page layout — single column vs multi-column grid",
		{"surface_type": "forms", "phase": "greenfield", "problem": "form usability"},
		expect_pack="pack_forms",
		expect_playbook="pb_forms",
	),
	QueryCase(
		"q22_landing_hero_conversion",
		"macro",
		"Marketing landing page hero section with primary CTA conversion flow",
		{"surface_type": "landing", "user_flow": "conversion", "phase": "greenfield"},
		expect_pack="pack_landing",
		expect_playbook="pb_landing",
	),
	QueryCase(
		"q23_dashboard_shell_layout",
		"macro",
		"Full SaaS dashboard shell — sidebar, header, KPI grid, data table",
		{"surface_type": "dashboard", "product_type": "saas", "phase": "greenfield"},
		expect_pack="pack_dashboard",
		expect_playbook="pb_dashboard",
	),
	QueryCase(
		"q24_settings_ia_grouping",
		"macro",
		"Enterprise settings area information architecture and section grouping",
		{"surface_type": "settings", "product_type": "enterprise", "user_flow": "configuration"},
		expect_pack="pack_information_architecture",
		expect_playbook="pb_information_architecture",
	),
	QueryCase(
		"q25_sitemap_marketing_flow",
		"macro",
		"Sitemap flow for marketing site: home → pricing → signup",
		{"surface_type": "marketing", "user_flow": "conversion", "task": "sitemap flow"},
		expect_pack="pack_navigation",
	),
	QueryCase(
		"q26_onboarding_journey_peak_end",
		"macro",
		"End-to-end onboarding journey with peak-end rule for first session",
		{"surface_type": "onboarding", "user_flow": "onboarding", "psychology_category": "cognitive_load"},
		expect_pack="pack_onboarding",
	),
	QueryCase(
		"q27_checkout_flow_ecommerce",
		"macro",
		"Full ecommerce checkout flow cart to confirmation",
		{"surface_type": "checkout", "user_flow": "checkout", "product_type": "ecommerce"},
		expect_pack="pack_forms",
	),
	QueryCase(
		"q28_app_shell_navigation_ia",
		"macro",
		"App shell navigation hierarchy for multi-module SaaS product",
		{"surface_type": "app_shell", "user_flow": "navigation", "product_type": "saas"},
		expect_pack="pack_navigation",
	),
	QueryCase(
		"q29_reading_flow_landing_f_pattern",
		"macro",
		"Text-heavy landing page reading flow and F-pattern layout",
		{"surface_type": "landing", "problem": "reading flow", "user_flow": "browse"},
		expect_pack="pack_landing",
	),
	QueryCase(
		"q30_cognitive_load_feature_ui",
		"macro",
		"Reduce cognitive load across a complex feature UI with Hick's law",
		{"psychology_category": "cognitive_load", "phase": "redesign", "problem": "information hierarchy"},
		expect_pack="pack_psychology",
		expect_playbook="pb_psychology",
	),
]


def run_query_battery(*, repo_root: Path | None = None) -> dict[str, Any]:
	from navigation.ux_knowledge.retrieval_engine import retrieve_ux_knowledge

	root = repo_root or Path(__file__).resolve().parents[2]
	results: list[dict[str, Any]] = []
	passed = 0

	for case in QUERY_BATTERY:
		req = {"intent": case.intent, **case.params}
		ret = retrieve_ux_knowledge(req, repo_root=str(root))
		pb = ret.get("matched_playbook") or {}
		meta = ret.get("meta") or {}
		pack_id = meta.get("pack_id")
		pb_id = pb.get("id")
		principles = len(ret.get("principles") or [])
		patterns = len(ret.get("patterns") or [])
		decisions = len(ret.get("decisions") or [])
		conflicts = len(ret.get("conflicts") or [])
		evidence = len(ret.get("evidence") or [])

		checks: list[str] = []
		ok = True
		if case.expect_pack and pack_id != case.expect_pack:
			checks.append(f"pack: expected {case.expect_pack}, got {pack_id}")
			ok = False
		if case.expect_playbook and pb_id != case.expect_playbook:
			checks.append(f"playbook: expected {case.expect_playbook}, got {pb_id}")
			ok = False
		if principles < case.min_principles:
			checks.append(f"principles<{case.min_principles}")
			ok = False
		if patterns < case.min_patterns:
			checks.append(f"patterns<{case.min_patterns}")
			ok = False
		if not pb_id:
			checks.append("no_playbook")
			ok = False

		if ok:
			passed += 1

		top_principles = [
			(p.get("id"), p.get("title", "")[:60])
			for p in (ret.get("principles") or [])[:3]
		]
		top_patterns = [p.get("label", "")[:50] for p in (ret.get("patterns") or [])[:3]]

		results.append(
			{
				"id": case.id,
				"tier": case.tier,
				"intent": case.intent,
				"pass": ok,
				"checks_failed": checks,
				"playbook_id": pb_id,
				"playbook_title": pb.get("title"),
				"pack_id": pack_id,
				"match_score": pb.get("match_score"),
				"decisions": decisions,
				"patterns": patterns,
				"principles": principles,
				"conflicts": conflicts,
				"evidence": evidence,
				"top_principles": top_principles,
				"top_patterns": top_patterns,
				"traversal": meta.get("traversal_path"),
				"notes": case.notes,
			}
		)

	by_tier: dict[str, dict[str, int]] = {}
	for r in results:
		t = r["tier"]
		by_tier.setdefault(t, {"total": 0, "passed": 0})
		by_tier[t]["total"] += 1
		if r["pass"]:
			by_tier[t]["passed"] += 1

	report = {
		"queries": len(QUERY_BATTERY),
		"passed": passed,
		"failed": len(QUERY_BATTERY) - passed,
		"coverage": round(passed / max(1, len(QUERY_BATTERY)), 3),
		"by_tier": by_tier,
		"results": results,
	}

	REPORTS.mkdir(parents=True, exist_ok=True)
	json_path = REPORTS / "query_battery.json"
	json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

	md_lines = [
		"# UX KB Query Battery Report",
		"",
		f"**{passed}/{len(QUERY_BATTERY)} passed** ({report['coverage']*100:.0f}%)",
		"",
		"## By tier",
		"",
		"| Tier | Passed | Total |",
		"|------|--------|-------|",
	]
	for tier in ("micro", "meso", "macro"):
		t = by_tier.get(tier, {"passed": 0, "total": 0})
		md_lines.append(f"| {tier} | {t['passed']} | {t['total']} |")

	md_lines.extend(["", "## Results", ""])
	for r in results:
		status = "PASS" if r["pass"] else "FAIL"
		md_lines.append(f"### {r['id']} [{r['tier']}] — {status}")
		md_lines.append(f"**Intent:** {r['intent']}")
		md_lines.append(
			f"**Playbook:** `{r['playbook_id']}` ({r['playbook_title']}) · "
			f"pack `{r['pack_id']}` · "
			f"{r['decisions']}d / {r['patterns']}p / {r['principles']}pr / {r['conflicts']}c"
		)
		if r["top_patterns"]:
			md_lines.append(f"- Patterns: {', '.join(r['top_patterns'])}")
		if r["top_principles"]:
			pr = "; ".join(f"`{p[0]}`" for p in r["top_principles"])
			md_lines.append(f"- Principles: {pr}")
		if r["checks_failed"]:
			md_lines.append(f"- **Failed:** {', '.join(r['checks_failed'])}")
		md_lines.append("")

	md_path = REPORTS / "QUERY_BATTERY.md"
	md_path.write_text("\n".join(md_lines), encoding="utf-8")
	report["report_json"] = str(json_path)
	report["report_md"] = str(md_path)
	return report


def main() -> None:
	import sys

	sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
	report = run_query_battery()
	print(json.dumps(
		{
			"passed": report["passed"],
			"queries": report["queries"],
			"coverage": report["coverage"],
			"by_tier": report["by_tier"],
			"report_md": report["report_md"],
			"report_json": report["report_json"],
		},
		indent=2,
	))
	raise SystemExit(0 if report["failed"] == 0 else 1)


if __name__ == "__main__":
	main()
