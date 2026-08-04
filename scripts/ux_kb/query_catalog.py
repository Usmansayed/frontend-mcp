"""Generate probe query catalog from taxonomy, CQs, and frontend surface matrix."""
from __future__ import annotations

import itertools
import json
import re
from pathlib import Path
from typing import Any

import yaml

from .paths import KB_ROOT, QUERY_CATALOG, REPO_ROOT, REPORTS, TAXONOMY

# Frontend MCP surface matrix — deterministic, no embeddings
SURFACE_TYPES = [
	"forms",
	"checkout",
	"onboarding",
	"landing",
	"dashboard",
	"settings",
	"marketing",
	"app_shell",
	"admin",
	"analytics",
]
PHASES = ["greenfield", "redesign", "feature", "hotfix", "polish"]
UI_COMPONENTS = [
	"textfield",
	"checkbox",
	"radio",
	"select",
	"modal",
	"sidebar",
	"nav",
	"data_table",
	"chart",
	"wizard",
	"breadcrumb",
	"tabs",
	"toast",
	"dropdown",
	"search_input",
	"password_field",
]
USER_FLOWS = [
	"signup",
	"checkout",
	"onboarding",
	"navigation",
	"browse",
	"conversion",
	"configuration",
	"data_entry",
	"login",
	"search",
]
PROBLEMS = [
	"accessibility",
	"information hierarchy",
	"density",
	"feedback",
	"navigation",
	"form usability",
	"reading flow",
	"conversion",
	"typography",
	"motion",
	"authentication",
	"table usability",
	"search UX",
	"notifications",
]
PRODUCT_TYPES = ["saas", "enterprise", "ecommerce"]
PLATFORMS = ["mobile", "desktop", "responsive"]
PSYCHOLOGY = ["cognitive_load", "motor_ergonomics", "aesthetic_usability", "human_factors"]

# Gap topics needing new playbooks / principles
GAP_TOPICS = [
	"typography",
	"motion",
	"auth",
	"data_tables",
	"search",
	"notifications",
	"responsive",
	"agentic_ux",
]

TOPIC_PACK_HINT: dict[str, str | None] = {
	"forms": "pack_forms",
	"checkout": "pack_forms",
	"onboarding": "pack_onboarding",
	"landing": "pack_landing",
	"dashboard": "pack_dashboard",
	"settings": "pack_information_architecture",
	"hierarchy_density": "pack_navigation",
	"reading_flow": "pack_landing",
	"a11y_absolute": "pack_accessibility",
	"motor_ergonomics": "pack_accessibility",
	"cognitive_load": "pack_psychology",
	"aesthetic_usability": "pack_psychology",
	"human_factors": "pack_psychology",
	"feedback_systems": "pack_dashboard",
	"design_tokens": "pack_dashboard",
	"general": "pack_information_architecture",
	"typography": None,
	"motion": None,
	"auth": None,
	"data_tables": None,
	"search": None,
	"notifications": None,
	"responsive": None,
	"agentic_ux": None,
}

CQ_SEEDS: list[dict[str, Any]] = [
	{"id": "CQ-SIT-01", "intent": "Cognitive-load gates before large greenfield UI first draft", "params": {"phase": "greenfield", "psychology_category": "cognitive_load"}, "topic_hint": "cognitive_load", "expect_pack": "pack_psychology"},
	{"id": "CQ-SIT-02", "intent": "Hierarchy and measurement claims for redesign SpecDiff", "params": {"phase": "redesign", "problem": "information hierarchy"}, "topic_hint": "hierarchy_density", "expect_pack": "pack_navigation"},
	{"id": "CQ-SIT-03", "intent": "Hotfix scope — no redesign exploration", "params": {"phase": "hotfix", "surface_type": "app_shell"}, "topic_hint": "general"},
	{"id": "CQ-SIT-04", "intent": "Progressive disclosure for expert dashboard vs harmful overload", "params": {"surface_type": "dashboard", "phase": "feature"}, "topic_hint": "feedback_systems", "expect_pack": "pack_dashboard"},
	{"id": "CQ-INX-01", "intent": "Minimum pointer target size and violation detection", "params": {"problem": "accessibility", "platform": "mobile"}, "topic_hint": "motor_ergonomics", "expect_pack": "pack_accessibility"},
	{"id": "CQ-INX-02", "intent": "Inline validation vs submit-time validation", "params": {"surface_type": "forms", "user_flow": "signup"}, "topic_hint": "forms", "expect_pack": "pack_forms"},
	{"id": "CQ-INX-03", "intent": "Single-column form layout mandatory vs exceptions", "params": {"surface_type": "forms", "user_flow": "data_entry"}, "topic_hint": "forms", "expect_pack": "pack_forms"},
	{"id": "CQ-INX-04", "intent": "Fitts and Steering laws for menu and CTA placement", "params": {"ui_component": "nav", "surface_type": "app_shell"}, "topic_hint": "motor_ergonomics", "expect_pack": "pack_accessibility"},
	{"id": "CQ-INX-05", "intent": "KLM cost estimate for high-frequency enterprise flow", "params": {"product_type": "enterprise", "user_flow": "data_entry"}, "topic_hint": "cognitive_load"},
	{"id": "CQ-COG-01", "intent": "How many choices before Hick cost is material", "params": {"psychology_category": "cognitive_load", "ui_component": "dropdown"}, "topic_hint": "cognitive_load", "expect_pack": "pack_psychology"},
	{"id": "CQ-COG-02", "intent": "Tesler's Law — allocate complexity system vs user", "params": {"psychology_category": "cognitive_load", "phase": "feature"}, "topic_hint": "cognitive_load"},
	{"id": "CQ-COG-03", "intent": "Fogg B=MAP diagnose failing CTA", "params": {"surface_type": "landing", "user_flow": "conversion"}, "topic_hint": "onboarding", "expect_pack": "pack_landing"},
	{"id": "CQ-COG-04", "intent": "When aesthetic-usability masks structural failure", "params": {"psychology_category": "aesthetic_usability", "phase": "polish"}, "topic_hint": "aesthetic_usability", "expect_pack": "pack_psychology"},
	{"id": "CQ-VIS-01", "intent": "Proximity encodes semantic grouping", "params": {"problem": "information hierarchy", "surface_type": "dashboard"}, "topic_hint": "hierarchy_density"},
	{"id": "CQ-VIS-02", "intent": "Primary CTA placement under F vs Z scanning", "params": {"surface_type": "landing", "problem": "reading flow"}, "topic_hint": "reading_flow", "expect_pack": "pack_landing"},
	{"id": "CQ-VIS-03", "intent": "Avoid equal-weight KPI false hierarchy on dashboards", "params": {"surface_type": "dashboard", "ui_component": "chart"}, "topic_hint": "feedback_systems", "expect_pack": "pack_dashboard"},
	{"id": "CQ-A11Y-01", "intent": "Mandatory contrast ratios text and large text", "params": {"problem": "accessibility", "phase": "polish"}, "topic_hint": "a11y_absolute", "expect_pack": "pack_accessibility"},
	{"id": "CQ-A11Y-02", "intent": "WCAG 2.2 target size and spacing rules", "params": {"problem": "accessibility", "platform": "mobile"}, "topic_hint": "a11y_absolute", "expect_pack": "pack_accessibility"},
	{"id": "CQ-PRD-01", "intent": "Checkout conversion empirics for ecommerce forms", "params": {"surface_type": "checkout", "product_type": "ecommerce"}, "topic_hint": "checkout", "expect_pack": "pack_forms"},
	{"id": "CQ-PRD-02", "intent": "Onboarding disclosure sequence minimizes overload", "params": {"surface_type": "onboarding", "user_flow": "onboarding"}, "topic_hint": "onboarding", "expect_pack": "pack_onboarding"},
	{"id": "CQ-PRD-03", "intent": "Settings IA patterns reduce search cost", "params": {"surface_type": "settings", "product_type": "saas"}, "topic_hint": "settings", "expect_pack": "pack_information_architecture"},
	{"id": "CQ-DS-01", "intent": "Semantic tokens vs raw CSS for a11y-bound color", "params": {"problem": "accessibility", "surface_type": "dashboard"}, "topic_hint": "design_tokens"},
	{"id": "CQ-DS-02", "intent": "Enterprise DS patterns for dense data entry", "params": {"product_type": "enterprise", "surface_type": "forms"}, "topic_hint": "design_tokens"},
	{"id": "CQ-AI-01", "intent": "Heuristics for agentic generative UI chrome", "params": {"surface_type": "app_shell", "problem": "notifications"}, "topic_hint": "agentic_ux"},
	{"id": "CQ-AI-02", "intent": "Conversational plus GUI hybrid control disclosure", "params": {"surface_type": "app_shell", "ui_component": "modal"}, "topic_hint": "agentic_ux"},
]

GAP_INTENTS: list[dict[str, Any]] = [
	{"topic_hint": "typography", "intent": "Base font size and line-height for long-form SaaS UI", "params": {"problem": "typography", "surface_type": "app_shell"}},
	{"topic_hint": "typography", "intent": "Heading scale hierarchy for marketing landing", "params": {"problem": "typography", "surface_type": "landing"}},
	{"topic_hint": "typography", "intent": "Tabular nums and font features for dashboard KPIs", "params": {"problem": "typography", "surface_type": "dashboard", "ui_component": "chart"}},
	{"topic_hint": "typography", "intent": "Readable line length for settings documentation", "params": {"problem": "typography", "surface_type": "settings"}},
	{"topic_hint": "typography", "intent": "Mobile typography scaling responsive breakpoints", "params": {"problem": "typography", "platform": "responsive", "surface_type": "landing"}},
	{"topic_hint": "motion", "intent": "Reduced motion preference and animation fallbacks", "params": {"problem": "motion", "phase": "polish"}},
	{"topic_hint": "motion", "intent": "Micro-interaction duration for form validation feedback", "params": {"problem": "motion", "surface_type": "forms"}},
	{"topic_hint": "motion", "intent": "Page transition timing for onboarding wizard", "params": {"problem": "motion", "surface_type": "onboarding", "ui_component": "wizard"}},
	{"topic_hint": "motion", "intent": "Loading skeleton vs spinner when to use each", "params": {"problem": "motion", "surface_type": "dashboard"}},
	{"topic_hint": "motion", "intent": "Parallax and scroll-driven motion accessibility", "params": {"problem": "motion", "surface_type": "marketing"}},
	{"topic_hint": "auth", "intent": "Login form error messaging and rate-limit UX", "params": {"problem": "authentication", "user_flow": "login", "surface_type": "forms"}},
	{"topic_hint": "auth", "intent": "Password reset flow step minimization", "params": {"problem": "authentication", "user_flow": "signup"}},
	{"topic_hint": "auth", "intent": "OAuth social login button placement and labeling", "params": {"problem": "authentication", "surface_type": "forms"}},
	{"topic_hint": "auth", "intent": "Session timeout warning and re-auth patterns", "params": {"problem": "authentication", "surface_type": "app_shell"}},
	{"topic_hint": "auth", "intent": "Route guard empty states vs redirect UX", "params": {"problem": "authentication", "phase": "feature"}},
	{"topic_hint": "data_tables", "intent": "Sortable column header affordances and a11y", "params": {"problem": "table usability", "ui_component": "data_table", "surface_type": "admin"}},
	{"topic_hint": "data_tables", "intent": "Row selection bulk actions placement", "params": {"problem": "table usability", "surface_type": "dashboard", "ui_component": "data_table"}},
	{"topic_hint": "data_tables", "intent": "Sticky header and horizontal scroll for wide tables", "params": {"problem": "table usability", "product_type": "enterprise"}},
	{"topic_hint": "data_tables", "intent": "Empty and loading states for data grids", "params": {"problem": "table usability", "surface_type": "analytics"}},
	{"topic_hint": "data_tables", "intent": "Pagination vs infinite scroll for admin tables", "params": {"problem": "table usability", "surface_type": "admin"}},
	{"topic_hint": "search", "intent": "Global search shortcut and command palette patterns", "params": {"problem": "search UX", "surface_type": "app_shell", "ui_component": "search_input"}},
	{"topic_hint": "search", "intent": "Autocomplete typeahead debounce and result ranking", "params": {"problem": "search UX", "user_flow": "search"}},
	{"topic_hint": "search", "intent": "Zero-results state and query refinement hints", "params": {"problem": "search UX", "surface_type": "marketing"}},
	{"topic_hint": "search", "intent": "Faceted filter UI for ecommerce browse", "params": {"problem": "search UX", "product_type": "ecommerce", "user_flow": "browse"}},
	{"topic_hint": "search", "intent": "Search results page scannability and highlighting", "params": {"problem": "search UX", "surface_type": "marketing"}},
	{"topic_hint": "notifications", "intent": "Toast vs banner vs inline notification choice", "params": {"problem": "notifications", "ui_component": "toast"}},
	{"topic_hint": "notifications", "intent": "Notification center persistence and grouping", "params": {"problem": "notifications", "surface_type": "app_shell"}},
	{"topic_hint": "notifications", "intent": "Critical alert modal interrupt patterns", "params": {"problem": "notifications", "ui_component": "modal", "phase": "hotfix"}},
	{"topic_hint": "responsive", "intent": "Breakpoint strategy mobile-first component reflow", "params": {"platform": "responsive", "phase": "greenfield"}},
	{"topic_hint": "responsive", "intent": "Touch vs pointer hybrid navigation patterns", "params": {"platform": "mobile", "surface_type": "app_shell"}},
	{"topic_hint": "agentic_ux", "intent": "AI copilot sidebar disclosure and undo affordances", "params": {"surface_type": "app_shell", "problem": "notifications"}, "topic_hint": "agentic_ux"},
	{"topic_hint": "agentic_ux", "intent": "Generative UI preview before apply confirmation", "params": {"phase": "feature", "surface_type": "dashboard"}},
]


def _intent_template(surface: str, phase: str, component: str | None = None) -> str:
	comp = f" {component.replace('_', ' ')}" if component else ""
	return f"Design {surface.replace('_', ' ')}{comp} for {phase} phase"


def _tier_for(params: dict[str, Any]) -> str:
	keys = sum(1 for k in params if params.get(k))
	if keys <= 2:
		return "micro"
	if keys <= 4:
		return "meso"
	return "macro"


def _topic_from_params(params: dict[str, Any]) -> str:
	if params.get("problem") == "typography":
		return "typography"
	if params.get("problem") == "motion":
		return "motion"
	if params.get("problem") == "authentication":
		return "auth"
	if params.get("problem") == "table usability":
		return "data_tables"
	if params.get("problem") == "search UX":
		return "search"
	if params.get("problem") == "notifications":
		return "notifications"
	if params.get("psychology_category"):
		return params["psychology_category"]
	if params.get("surface_type") in ("forms", "checkout"):
		return "forms" if params["surface_type"] == "forms" else "checkout"
	if params.get("surface_type") == "onboarding":
		return "onboarding"
	if params.get("surface_type") in ("landing", "marketing"):
		return "reading_flow"
	if params.get("surface_type") in ("dashboard", "admin", "analytics"):
		return "feedback_systems"
	if params.get("surface_type") == "settings":
		return "settings"
	if params.get("problem") == "accessibility":
		return "a11y_absolute"
	return "general"


def generate_query_catalog(*, max_queries: int = 400) -> dict[str, Any]:
	queries: list[dict[str, Any]] = []
	seen: set[str] = set()
	counter = 0

	def add(
		intent: str,
		params: dict[str, Any],
		*,
		topic_hint: str | None = None,
		expect_pack: str | None = None,
		tier: str | None = None,
		source: str = "matrix",
	) -> None:
		nonlocal counter
		if len(queries) >= max_queries:
			return
		th = topic_hint or _topic_from_params(params)
		ep = expect_pack if expect_pack is not None else TOPIC_PACK_HINT.get(th)
		sig = json.dumps({"intent": intent, **params}, sort_keys=True)
		if sig in seen:
			return
		seen.add(sig)
		counter += 1
		queries.append(
			{
				"id": f"qcat_{counter:04d}",
				"tier": tier or _tier_for(params),
				"intent": intent,
				"params": params,
				"topic_hint": th,
				"expect_pack": ep,
				"source": source,
			}
		)

	# CQ seeds
	for cq in CQ_SEEDS:
		add(
			cq["intent"],
			dict(cq["params"]),
			topic_hint=cq.get("topic_hint"),
			expect_pack=cq.get("expect_pack"),
			tier="macro" if cq["id"].startswith("CQ-SIT") else "meso",
			source=f"cq:{cq['id']}",
		)

	# Gap topic intents
	for g in GAP_INTENTS:
		add(
			g["intent"],
			dict(g["params"]),
			topic_hint=g["topic_hint"],
			expect_pack=TOPIC_PACK_HINT.get(g["topic_hint"]),
			tier="meso",
			source="gap_intent",
		)

	# Surface × phase matrix (meso)
	for surface, phase in itertools.product(SURFACE_TYPES, PHASES):
		params = {"surface_type": surface, "phase": phase}
		add(_intent_template(surface, phase), params, source="surface_phase")

	# Surface × component (micro)
	for surface, comp in itertools.product(
		["forms", "dashboard", "landing", "settings", "app_shell", "onboarding"],
		UI_COMPONENTS[:12],
	):
		params = {"surface_type": surface, "ui_component": comp}
		add(f"Best practices for {comp.replace('_', ' ')} on {surface}", params, tier="micro", source="surface_component")

	# User flow × surface
	for flow, surface in itertools.product(USER_FLOWS, ["forms", "landing", "dashboard", "app_shell", "onboarding"]):
		params = {"user_flow": flow, "surface_type": surface}
		add(f"Optimize {flow.replace('_', ' ')} flow on {surface.replace('_', ' ')}", params, tier="meso", source="flow_surface")

	# Problem × surface
	for problem, surface in itertools.product(PROBLEMS, SURFACE_TYPES[:8]):
		params = {"problem": problem, "surface_type": surface}
		add(f"Fix {problem} on {surface.replace('_', ' ')}", params, tier="meso", source="problem_surface")

	# Psychology × phase
	for psych, phase in itertools.product(PSYCHOLOGY, PHASES):
		params = {"psychology_category": psych, "phase": phase}
		add(f"Apply {psych.replace('_', ' ')} during {phase}", params, tier="macro", source="psychology_phase")

	# Product type × surface
	for prod, surface in itertools.product(PRODUCT_TYPES, ["dashboard", "settings", "forms", "landing"]):
		params = {"product_type": prod, "surface_type": surface}
		add(f"{prod.upper()} {surface.replace('_', ' ')} UX constraints", params, tier="meso", source="product_surface")

	# Platform × surface (mobile/responsive gaps)
	for platform, surface in itertools.product(PLATFORMS, ["forms", "landing", "dashboard", "app_shell", "checkout"]):
		params = {"platform": platform, "surface_type": surface}
		add(f"{platform.capitalize()} {surface.replace('_', ' ')} layout and touch patterns", params, tier="meso", source="platform_surface")

	# Taxonomy gap nodes
	if TAXONOMY.exists():
		tax = yaml.safe_load(TAXONOMY.read_text(encoding="utf-8"))

		def walk(node: dict, path: list[str]) -> None:
			status = node.get("status")
			nid = node.get("id") or ""
			label = node.get("label") or nid
			if status in ("gap", "gap_extrapolated"):
				add(
					f"Research gap: {label}",
					{"problem": label.lower(), "phase": "feature"},
					topic_hint=nid if nid in GAP_TOPICS else "general",
					tier="macro",
					source=f"taxonomy:{nid}",
				)
			for ch in node.get("children") or []:
				walk(ch, path + [nid])

		for root in tax.get("roots") or []:
			walk(root, [])
		for gap in tax.get("gaps") or []:
			add(
				f"Explicit taxonomy gap: {gap.get('label')}",
				{"problem": gap.get("label", "").lower()},
				topic_hint="general",
				tier="macro",
				source=f"taxonomy_gap:{gap.get('id')}",
			)

	catalog = {
		"version": 1,
		"generated_from": ["TOPIC_TAXONOMY", "COMPETENCY_QUESTIONS", "surface_matrix", "gap_intents"],
		"total": len(queries),
		"by_tier": {
			t: sum(1 for q in queries if q["tier"] == t) for t in ("micro", "meso", "macro")
		},
		"by_topic_hint": {},
		"queries": queries[:max_queries],
	}
	for q in catalog["queries"]:
		th = q["topic_hint"]
		catalog["by_topic_hint"][th] = catalog["by_topic_hint"].get(th, 0) + 1

	KB_ROOT.mkdir(parents=True, exist_ok=True)
	QUERY_CATALOG.write_text(yaml.dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")
	REPORTS.mkdir(parents=True, exist_ok=True)
	(REPORTS / "query_catalog.json").write_text(
		json.dumps({"total": catalog["total"], "by_tier": catalog["by_tier"], "by_topic_hint": catalog["by_topic_hint"]}, indent=2),
		encoding="utf-8",
	)
	return catalog


def main() -> None:
	catalog = generate_query_catalog()
	print(json.dumps({"total": catalog["total"], "path": str(QUERY_CATALOG), "by_tier": catalog["by_tier"]}, indent=2))


if __name__ == "__main__":
	main()
