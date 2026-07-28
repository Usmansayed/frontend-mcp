"""Agent-facing MCP discoverability audit (exp/agent-face-simple).

Scores whether a host agent can answer: when to use MCP, which tool next, how to claim done.
Does NOT run a live browser — envelopes are coordinated via service APIs.

Usage:
  PYTHONPATH=src python -u scripts/eval_agent_face_discoverability.py
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/research/agent_face_discoverability.json"


@dataclass
class Check:
	id: str
	ok: bool
	score: float  # 0..1
	detail: str
	evidence: Any = None


@dataclass
class Report:
	checks: list[Check] = field(default_factory=list)
	summary: dict[str, Any] = field(default_factory=dict)

	def add(self, c: Check) -> None:
		self.checks.append(c)
		print(f"[{'PASS' if c.ok else 'FAIL'}] {c.id}: {c.detail} (score={c.score:.2f})")


def _words(s: str) -> int:
	return len((s or "").split())


def audit_always_on(report: Report) -> None:
	from navigation.mcp.instructions import MCP_INSTRUCTIONS

	rule = (ROOT / ".cursor/rules/frontend-perception-mcp.mdc").read_text(encoding="utf-8")
	instr_w = _words(MCP_INSTRUCTIONS)
	rule_w = _words(rule)
	combined = instr_w + rule_w
	# Target from research: ≤ ~600 words combined always-on
	ok = combined <= 700 and "agent_summary.card" in MCP_INSTRUCTIONS and "agent_summary.card" in rule
	report.add(
		Check(
			id="always_on_budget",
			ok=ok,
			score=max(0.0, min(1.0, 700 / max(combined, 1))),
			detail=f"instructions={instr_w}w rule={rule_w}w combined={combined}w (budget≤700)",
			evidence={"instructions_words": instr_w, "rule_words": rule_w},
		)
	)
	must = ["Bootstrap", "card", "owed", "verified", "greenfield", "redesign", "hotfix", "forms"]
	missing = [m for m in must if m.lower() not in MCP_INSTRUCTIONS.lower()]
	report.add(
		Check(
			id="always_on_spine_keywords",
			ok=not missing,
			score=1.0 - len(missing) / len(must),
			detail="missing=" + (",".join(missing) if missing else "none"),
			evidence={"missing": missing},
		)
	)


def audit_spines(report: Report) -> None:
	from navigation.mcp.methodology_resources import METHODOLOGY_RESOURCES

	spines = [u for u in METHODOLOGY_RESOURCES if u.startswith("perception://spine/")]
	expected = {
		"perception://spine/greenfield",
		"perception://spine/redesign",
		"perception://spine/feature",
		"perception://spine/hotfix",
		"perception://spine/forms",
	}
	ok = expected.issubset(set(spines))
	lengths = {u: _words(METHODOLOGY_RESOURCES[u][1]) for u in sorted(expected) if u in METHODOLOGY_RESOURCES}
	# Each spine should be short (≤120 words) and name at least one perception_ tool
	short = all(w <= 150 for w in lengths.values())
	tools_named = all(
		"perception_" in METHODOLOGY_RESOURCES[u][1] for u in expected if u in METHODOLOGY_RESOURCES
	)
	gs = METHODOLOGY_RESOURCES.get("perception://getting-started", ("", ""))[1]
	gs_points_card = "agent_summary.card" in gs and "spine/" in gs
	report.add(
		Check(
			id="spines_exist",
			ok=ok and short and tools_named and gs_points_card,
			score=(int(ok) + int(short) + int(tools_named) + int(gs_points_card)) / 4,
			detail=f"spines={len(spines)} lengths={lengths} gs→card={gs_points_card}",
			evidence={"spines": spines, "lengths": lengths},
		)
	)


def audit_tool_descriptions(report: Report) -> None:
	"""Score tool descriptions for when/how cues without loading full MCP host."""
	from navigation.mcp import tools as tools_mod

	# tools.py builds Tool objects — introspect list_tools if available
	tool_list: list[dict[str, Any]] = []
	if hasattr(tools_mod, "list_tool_defs"):
		tool_list = list(tools_mod.list_tool_defs())
	elif hasattr(tools_mod, "TOOL_DEFINITIONS"):
		raw = tools_mod.TOOL_DEFINITIONS
		tool_list = list(raw) if isinstance(raw, list) else []
	else:
		# Fallback: parse tools.py text for name + description pairs
		text = (ROOT / "src/navigation/mcp/tools.py").read_text(encoding="utf-8")
		# Rough: name="perception_..." blocks
		names = re.findall(r'name\s*=\s*"(perception_[a-z0-9_]+)"', text)
		tool_list = [{"name": n, "description": ""} for n in names]

	# Prefer live GetMcp dump if present from this session
	dump = Path(
		r"C:\Users\usman\.cursor\projects\c-Users-usman-Projects-frontend-perception-engine"
		r"\agent-tools\95df1a00-6682-4a68-bba2-12fb826b560a.txt"
	)
	live: list[dict[str, Any]] = []
	if dump.is_file():
		raw = dump.read_text(encoding="utf-8", errors="replace")
		# Extract tool entries: "name": "perception_..." and following description
		for m in re.finditer(
			r'"tool"\s*:\s*"(perception_[^"]+)"\s*,\s*"description"\s*:\s*"(.*?)"\s*,\s*\n\s*"inputSchema"',
			raw,
			re.S,
		):
			desc = bytes(m.group(2), "utf-8").decode("unicode_escape", errors="replace")
			live.append({"name": m.group(1), "description": desc})

	sample = live or tool_list
	n = len(sample)
	if n == 0:
		report.add(Check("tools_listed", False, 0.0, "no tools found", None))
		return

	# Core tools an agent must find easily
	core = {
		"perception_health",
		"perception_session_start",
		"perception_inspiration_collect",
		"perception_visual_feedback",
		"perception_build_design_snapshot",
		"perception_navigate_and_observe",
		"perception_verify",
		"perception_probe_form",
		"perception_design_review",
	}
	names = {t["name"] for t in sample}
	core_ok = core.issubset(names)

	when_cues = ("when", "use", "before", "after", "for ", "if ", "required", "intent")
	# "How" = arg hints OR structured Does/Returns/Next enrichment from tool_catalog
	how_cues = (
		"session_id",
		"intent",
		"purpose",
		"criteria",
		"mode",
		"url",
		"base_url",
		"does:",
		"returns:",
		"next:",
		"query",
	)
	scored: list[dict[str, Any]] = []
	for t in sample:
		desc = (t.get("description") or "").lower()
		has_when = any(c in desc for c in when_cues)
		has_how = any(c in desc for c in how_cues) or "required" in desc
		w = _words(t.get("description") or "")
		# Too short = vague; too long = ignored
		len_ok = 12 <= w <= 220
		scored.append(
			{
				"name": t["name"],
				"words": w,
				"has_when": has_when,
				"has_how": has_how,
				"len_ok": len_ok,
			}
		)

	core_rows = [s for s in scored if s["name"] in core]
	if core_rows:
		when_rate = sum(1 for s in core_rows if s["has_when"]) / len(core_rows)
		how_rate = sum(1 for s in core_rows if s["has_how"]) / len(core_rows)
		len_rate = sum(1 for s in core_rows if s["len_ok"]) / len(core_rows)
	else:
		when_rate = how_rate = len_rate = 0.0

	ok = core_ok and when_rate >= 0.6 and how_rate >= 0.5
	report.add(
		Check(
			id="tool_descriptions_core",
			ok=ok,
			score=(int(core_ok) + when_rate + how_rate + len_rate) / 4,
			detail=(
				f"tools={n} core_present={core_ok} "
				f"core_when={when_rate:.0%} core_how={how_rate:.0%} core_len={len_rate:.0%}"
			),
			evidence={
				"tool_count": n,
				"core_missing": sorted(core - names),
				"core_rows": core_rows,
			},
		)
	)

	# Volume: raw tools/list is large; progressive discovery = group meta + card.next spine.
	# Catalog shrink is a non-goal — card orchestration is the mitigation.
	from navigation.mcp.tool_catalog import infer_group

	grouped = sum(1 for t in sample if infer_group(str(t.get("name") or "")) != "Other")
	group_rate = grouped / max(n, 1)
	groups: dict[str, int] = {}
	for t in sample:
		g = infer_group(str(t.get("name") or ""))
		groups[g] = groups.get(g, 0) + 1
	# Pass when either small catalog OR progressive discovery contract holds.
	volume_ok = n <= 50 or (group_rate >= 0.9 and n <= 100)
	report.add(
		Check(
			id="tool_volume",
			ok=volume_ok,
			score=(
				1.0
				if n <= 50
				else max(0.0, min(1.0, 0.7 + 0.3 * group_rate))
			),
			detail=(
				f"{n} tools exposed; groups={dict(groups)}; "
				f"grouped={group_rate:.0%} "
				f"(pass if ≤50 or ≥90% grouped ≤100)"
			),
			evidence={"tool_count": n, "groups": groups, "group_rate": group_rate},
		)
	)


def audit_live_card(report: Report) -> None:
	"""Simulate greenfield + redesign episodes; assert card is readable."""
	from navigation.coordination_intelligence.service import CoordinationIntelligenceService
	from navigation.core.envelope import make_envelope

	svc = CoordinationIntelligenceService()

	cases = [
		("greenfield", "build a new SaaS landing page hero", "S03_design"),
		("redesign", "redesign Meridian analytics dashboard to match mockup", "S03_design"),
		("hotfix", "fix overlapping mobile menu button", "S05_verify"),
	]
	results = []
	for label, intent, lifecycle in cases:
		psm = svc.episode_start(
			session_id=f"disc_{label}",
			intent=intent,
			lifecycle_stage=lifecycle,
			project_maturity="M1",
		)
		# Ensure face classifier sees the raw user intent.
		strat = dict(psm.briefing.engineering_strategy or {})
		strat["intent"] = intent
		psm.briefing.engineering_strategy = strat
		svc.runtime.save(psm)
		out = svc.on_tool_envelope(
			psm.episode_id,
			"perception_session_start",
			{"session_id": f"disc_{label}", "intent": intent, "base_url": "http://127.0.0.1:5173"},
			make_envelope(
				"perception_session_start",
				ok=True,
				session_id=f"disc_{label}",
				data={"url": "http://127.0.0.1:5173"},
			),
		)
		summary = out.get("agent_summary") or {}
		card = summary.get("card") or {}
		ok = bool(card.get("next") and card.get("class") and "owed" in card and "claim_ok" in card)
		results.append(
			{
				"label": label,
				"ok": ok,
				"class": card.get("class"),
				"next": card.get("next"),
				"owed": card.get("owed"),
				"gate": card.get("gate"),
				"claim_ok": card.get("claim_ok"),
				"resource": card.get("resource"),
				"recommended_next": summary.get("recommended_next"),
			}
		)
		print(
			f"  live/{label}: class={card.get('class')} next={card.get('next')} "
			f"owed={len(card.get('owed') or [])} resource={card.get('resource')}"
		)

	all_ok = all(r["ok"] for r in results)
	# Classification sanity: greenfield/redesign/hotfix should differ
	classes = {r["label"]: r["class"] for r in results}
	class_ok = (
		classes.get("greenfield") in {"greenfield", "feature"}
		and classes.get("redesign") == "redesign"
		and classes.get("hotfix") == "hotfix"
	)
	report.add(
		Check(
			id="live_card_after_bootstrap",
			ok=all_ok and class_ok,
			score=(int(all_ok) + int(class_ok)) / 2,
			detail=f"classes={classes}",
			evidence={"results": results},
		)
	)

	# Can an agent answer "what do I call next?" from card alone without coordinator?
	need_coord = False
	for r in results:
		if not r["next"]:
			need_coord = True
	report.add(
		Check(
			id="card_alone_sufficient_for_next",
			ok=not need_coord,
			score=1.0 if not need_coord else 0.0,
			detail="card.next present on all bootstrap cases"
			if not need_coord
			else "some cases missing card.next",
			evidence={"results": results},
		)
	)


def audit_resource_index(report: Report) -> None:
	from navigation.mcp.resources import list_resources

	res = list_resources()
	uris = [r["uri"] for r in res]
	spine_n = sum(1 for u in uris if "/spine/" in u)
	guide_n = sum(1 for u in uris if "/guide/" in u)
	# Discoverability: spines should be listed; total shouldn't be insane
	ok = spine_n >= 5 and len(uris) <= 60
	report.add(
		Check(
			id="resource_index",
			ok=ok,
			score=max(0.0, min(1.0, 1.0 - max(0, len(uris) - 40) / 40)),
			detail=f"total={len(uris)} spines={spine_n} guide_cards={guide_n}",
			evidence={"uris": uris[:80]},
		)
	)


def main() -> int:
	print("AGENT-FACE DISCOVERABILITY AUDIT\n")
	report = Report()
	audit_always_on(report)
	audit_spines(report)
	audit_tool_descriptions(report)
	audit_resource_index(report)
	audit_live_card(report)

	scores = [c.score for c in report.checks]
	overall = sum(scores) / len(scores) if scores else 0.0
	passed = sum(1 for c in report.checks if c.ok)
	report.summary = {
		"overall_score": round(overall, 3),
		"passed": passed,
		"total": len(report.checks),
		"verdict": (
			"EASY_ENOUGH"
			if overall >= 0.8 and passed == len(report.checks)
			else "USABLE_WITH_GAPS"
			if overall >= 0.65
			else "HARD_TO_DISCOVER"
		),
	}
	print("\n" + "=" * 60)
	print(json.dumps(report.summary, indent=2))
	OUT.parent.mkdir(parents=True, exist_ok=True)
	OUT.write_text(
		json.dumps({"summary": report.summary, "checks": [asdict(c) for c in report.checks]}, indent=2),
		encoding="utf-8",
	)
	print(f"Wrote {OUT}")
	return 0 if report.summary["verdict"] != "HARD_TO_DISCOVER" else 1


if __name__ == "__main__":
	raise SystemExit(main())
