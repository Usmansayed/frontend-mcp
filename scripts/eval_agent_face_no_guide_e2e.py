"""Full MCP E2E: follow agent_summary.card only — never read guides/spines.

Simulates a host agent that:
  1. Bootstraps with intent (health → session_start)
  2. Each turn reads card.next / card.owed and calls one tool
  3. Never calls resources/read (no perception://guide|spine|getting-started)
  4. Claims only when card.claim_ok and verify has passed

Usage:
  $env:PYTHONPATH="src"
  python -u scripts/eval_agent_face_no_guide_e2e.py
  python -u scripts/eval_agent_face_no_guide_e2e.py --cases forms,hotfix
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "browser-use")) if (ROOT / "browser-use").is_dir() else None

OUT = ROOT / "docs/research/agent_face_no_guide_e2e.json"
DEFAULT_URL = "http://127.0.0.1:18765"

# Tools we refuse — proves no-guide policy
FORBIDDEN_RESOURCE_PREFIXES = (
	"perception://guide/",
	"perception://spine/",
	"perception://getting-started",
	"perception://frontend-methodology",
	"perception://design-workflow",
	"perception://redesign-workflow",
	"perception://bugfix-workflow",
	"perception://agent-guide",
	"perception://agent-coordination",
)


@dataclass
class CaseSpec:
	id: str
	intent: str
	expect_class: str
	route: str
	max_steps: int = 10
	# After structural owed payment, run a case-specific finish path
	finish: str = ""  # forms | verify_text | none


CASES: list[CaseSpec] = [
	CaseSpec(
		id="forms",
		intent="Verify the validation form at /forms/validation: invalid submit shows errors, valid submit shows success",
		expect_class="forms",
		route="/forms/validation",
		max_steps=8,
		finish="forms",
	),
	CaseSpec(
		id="hotfix",
		intent="Fix overlapping CTA button layout bug on the homepage — surgical CSS hotfix",
		expect_class="hotfix",
		route="/",
		max_steps=6,
		finish="verify_text",
	),
	CaseSpec(
		id="greenfield",
		intent="Build a new SaaS product landing page with a strong brand hero — greenfield design",
		expect_class="greenfield",
		route="/",
		max_steps=8,
		finish="structural_verify",
	),
	CaseSpec(
		id="redesign",
		intent="Redesign the dashboard layout to match the mockup — measured redesign with snapshot",
		expect_class="redesign",
		route="/",
		max_steps=8,
		finish="structural_verify",
	),
]


@dataclass
class StepRecord:
	i: int
	tool: str
	ok: bool
	latency_ms: int
	card_class: str | None = None
	card_next: str | None = None
	card_gate: str | None = None
	card_claim_ok: bool | None = None
	owed_families: list[str] = field(default_factory=list)
	followed_card: bool = False
	error: str | None = None


@dataclass
class CaseReport:
	id: str
	ok: bool = False
	expect_class: str = ""
	got_class: str | None = None
	class_ok: bool = False
	card_present_rate: float = 0.0
	followed_card_rate: float = 0.0
	guides_read: int = 0
	claim_ok_at_end: bool | None = None
	verified: bool | None = None
	finish_ok: bool | None = None
	steps: list[StepRecord] = field(default_factory=list)
	notes: list[str] = field(default_factory=list)
	error: str | None = None


def _card(env: dict[str, Any]) -> dict[str, Any]:
	summary = env.get("agent_summary") or {}
	card = summary.get("card")
	if isinstance(card, dict):
		return card
	# Some envelopes nest under data
	data = env.get("data") or {}
	inner = (data.get("agent_summary") or {}).get("card")
	return inner if isinstance(inner, dict) else {}


def _owed_tools(card: dict[str, Any]) -> set[str]:
	out: set[str] = set()
	nxt = card.get("next")
	if nxt:
		out.add(str(nxt))
	for row in card.get("owed") or []:
		if isinstance(row, dict) and row.get("tool"):
			out.add(str(row["tool"]))
	return out


def _pick_tool(card: dict[str, Any], *, prefer: str | None = None) -> str:
	owed = list(card.get("owed") or [])
	if prefer:
		for row in owed:
			if isinstance(row, dict) and row.get("tool") == prefer:
				return prefer
		if card.get("next") == prefer:
			return prefer
	if card.get("next"):
		return str(card["next"])
	if owed and isinstance(owed[0], dict) and owed[0].get("tool"):
		return str(owed[0]["tool"])
	return "perception_navigate_and_observe"


class NoGuideAgent:
	"""Card-only agent — never reads methodology resources."""

	def __init__(self, runtime: Any, *, url: str, repo_root: str) -> None:
		self.rt = runtime
		self.url = url
		self.repo_root = repo_root
		self.session_id: str | None = None
		self.scan_id: str | None = None
		self.guides_read = 0
		self.last_card: dict[str, Any] = {}
		self.verified = False

	async def call(self, tool: str, args: dict[str, Any] | None = None) -> tuple[dict[str, Any], int]:
		# Hard policy: never resource-read guides
		if tool in {"resources/read", "read_resource"}:
			uri = str((args or {}).get("uri") or "")
			if any(uri.startswith(p) for p in FORBIDDEN_RESOURCE_PREFIXES):
				self.guides_read += 1
				raise RuntimeError(f"no-guide policy violated: {uri}")
		t0 = time.perf_counter()
		result = await self.rt.execute_tool(tool, args or {}, allow_repeat=True)
		ms = int((time.perf_counter() - t0) * 1000)
		env = result.envelope if hasattr(result, "envelope") else result
		if not isinstance(env, dict):
			env = {"ok": False, "error": "non-dict envelope"}
		card = _card(env)
		if card:
			self.last_card = card
		sid = env.get("session_id") or (env.get("data") or {}).get("session_id")
		if sid:
			self.session_id = str(sid)
		scan = env.get("scan_id") or (env.get("data") or {}).get("scan_id")
		if scan:
			self.scan_id = str(scan)
		if tool == "perception_verify":
			self.verified = bool((env.get("data") or {}).get("verified"))
		return env, ms

	def args_for(self, tool: str, case: CaseSpec) -> dict[str, Any]:
		sid = self.session_id
		base: dict[str, Any] = {}
		if sid and tool not in {"perception_health", "perception_session_start"}:
			base["session_id"] = sid

		# Prefer card.next_args (face contract) — resolve placeholders.
		card_args = dict((self.last_card or {}).get("next_args") or {})
		if (self.last_card or {}).get("next") == tool and card_args:
			merged = {**base}
			for k, v in card_args.items():
				sv = str(v)
				if sv.startswith("<") and sv.endswith(">"):
					continue
				merged[k] = v
			# Always ensure session + concrete route/query
			if tool == "perception_navigate_and_observe":
				merged.setdefault("url", case.route)
				merged.setdefault("include_screenshot", True)
			if "query" not in merged and tool in {
				"perception_select_component_foundation",
				"perception_search_components",
				"perception_inspiration_collect",
			}:
				merged["query"] = case.intent[:120]
			if tool == "perception_build_design_snapshot" and self.scan_id:
				merged.setdefault("scan_id", self.scan_id)
			if tool == "perception_visual_feedback":
				merged.setdefault(
					"purpose",
					{
						"forms": "forms",
						"hotfix": "hotfix",
						"greenfield": "inspiration",
						"redesign": "design",
					}.get(case.expect_class, "general"),
				)
				merged.setdefault(
					"visual_feedback",
					{"judgment": "ok", "notes": f"no-guide look {case.id}"},
				)
			if tool == "perception_verify":
				merged.setdefault(
					"criteria",
					{"text_contains": ["Validated form"] if case.id == "forms" else ["Home"]},
				)
			if tool == "perception_select_component_foundation":
				merged.setdefault("repo_root", self.repo_root)
			return merged

		if tool == "perception_health":
			return {"url": self.url, "intent": case.intent}
		if tool == "perception_session_start":
			return {
				"base_url": self.url,
				"intent": case.intent,
				"headless": True,
				"repo_root": self.repo_root,
			}
		if tool == "perception_navigate_and_observe":
			return {
				**base,
				"url": case.route,
				"include_screenshot": True,
				"detail": "summary_only",
			}
		if tool == "perception_observe":
			return {**base, "include_screenshot": True, "detail": "summary_only"}
		if tool == "perception_probe_form":
			return {**base, "form": "validation"}
		if tool == "perception_inspiration_collect":
			return {
				**base,
				"query": case.intent[:120],
				"inspiration_level": "light",
				"bind_as_reference": True,
			}
		if tool == "perception_inspiration_discover":
			return {**base, "query": case.intent[:80], "inspiration_level": "light"}
		if tool == "perception_build_design_snapshot":
			args = {**base, "bind_as_reference": case.expect_class == "redesign"}
			if self.scan_id:
				args["scan_id"] = self.scan_id
			return args
		if tool == "perception_visual_feedback":
			purpose = {
				"forms": "forms",
				"hotfix": "hotfix",
				"greenfield": "inspiration",
				"redesign": "design",
			}.get(case.expect_class, "general")
			return {
				**base,
				"purpose": purpose,
				"screenshot_pack": "viewport",
				"visual_feedback": {
					"judgment": "ok",
					"notes": f"no-guide e2e look for {case.id}",
				},
			}
		if tool in {
			"perception_search_components",
			"perception_select_component_foundation",
			"perception_plan_component_search",
			"perception_integrate_component",
		}:
			return {
				**base,
				"query": case.intent[:120],
				"repo_root": self.repo_root,
			}
		if tool == "perception_verify":
			return {
				**base,
				"criteria": {"text_contains": ["Validated form"] if case.id == "forms" else ["Home"]},
			}
		if tool == "perception_design_review":
			return {
				**base,
				"user_task": case.intent,
				"repo_root": self.repo_root,
				"mode": "ship" if self.last_card.get("claim_ok") else "review",
			}
		return base

	async def finish_structural_verify(self, needle: str = "Home") -> tuple[bool, list[str]]:
		"""Pay LOOK + verify without claiming ship (structural ladder floor)."""
		notes: list[str] = []
		assert self.session_id
		if not self.scan_id:
			env, _ = await self.call(
				"perception_navigate_and_observe",
				{
					"session_id": self.session_id,
					"url": "/",
					"include_screenshot": True,
				},
			)
			notes.append(f"observe_ok={bool(env.get('ok'))}")
		# Prefer snapshot for redesign if owed
		owed_tools = _owed_tools(self.last_card)
		if "perception_build_design_snapshot" in owed_tools and self.scan_id:
			env, _ = await self.call(
				"perception_build_design_snapshot",
				{
					"session_id": self.session_id,
					"scan_id": self.scan_id,
					"bind_as_reference": True,
				},
			)
			notes.append(f"snapshot_ok={bool(env.get('ok'))}")
		env, _ = await self.call(
			"perception_visual_feedback",
			{
				"session_id": self.session_id,
				"purpose": "design",
				"screenshot_pack": "viewport",
				"visual_feedback": {"judgment": "ok", "notes": "structural ladder look"},
			},
		)
		notes.append(f"vf_ok={bool(env.get('ok'))}")
		env, _ = await self.call(
			"perception_verify",
			{"session_id": self.session_id, "criteria": {"text_contains": [needle]}},
		)
		ok = bool((env.get("data") or {}).get("verified"))
		notes.append(f"verify={ok}")
		notes.append(f"claim_ok={self.last_card.get('claim_ok')}")
		# After verify, claim_ok may still be false if claim_extra (ship) remains — that's OK
		return ok, notes

	async def finish_forms(self) -> tuple[bool, list[str]]:
		notes: list[str] = []
		assert self.session_id
		# Invalid submit
		env, _ = await self.call(
			"perception_execute_actions",
			{
				"session_id": self.session_id,
				"actions": [{"type": "click_button", "text": "Validate & submit"}],
				"capture_insights_during": False,
			},
		)
		if not env.get("ok"):
			notes.append(f"invalid_act_fail:{env.get('error')}")
			return False, notes
		env, _ = await self.call(
			"perception_verify",
			{"session_id": self.session_id, "criteria": {"text_contains": ["Invalid email"]}},
		)
		inv = bool((env.get("data") or {}).get("verified"))
		notes.append(f"verify_invalid={inv}")
		if not inv:
			return False, notes
		# Valid path (checkbox via script, then fill)
		await self.call(
			"perception_execute_script",
			{
				"session_id": self.session_id,
				"script": (
					"(() => { const c = document.querySelector('input[type=checkbox]'); "
					"if (c && !c.checked) c.click(); return true; })()"
				),
				"capture_insights_during": False,
			},
		)
		env, _ = await self.call(
			"perception_execute_actions",
			{
				"session_id": self.session_id,
				"actions": [
					{"type": "set_input", "label": "Email", "value": "test@example.com"},
					{"type": "set_input", "label": "Phone", "value": "1234567890"},
					{"type": "set_input", "label": "Age", "value": "25"},
					{"type": "click_button", "text": "Validate & submit"},
				],
				"capture_insights_during": False,
			},
		)
		if not env.get("ok"):
			notes.append(f"valid_act_fail:{env.get('error')}")
			return False, notes
		env, _ = await self.call(
			"perception_verify",
			{"session_id": self.session_id, "criteria": {"text_contains": ["Form is valid"]}},
		)
		ok = bool((env.get("data") or {}).get("verified"))
		notes.append(f"verify_valid={ok}")
		return ok, notes

	async def finish_verify_text(self, needle: str) -> tuple[bool, list[str]]:
		env, _ = await self.call(
			"perception_verify",
			{"session_id": self.session_id, "criteria": {"text_contains": [needle]}},
		)
		ok = bool((env.get("data") or {}).get("verified"))
		return ok, [f"verify_text({needle})={ok}"]


async def run_case(runtime: Any, case: CaseSpec, *, url: str, repo_root: str) -> CaseReport:
	report = CaseReport(id=case.id, expect_class=case.expect_class)
	agent = NoGuideAgent(runtime, url=url, repo_root=repo_root)
	card_hits = 0
	follow_hits = 0
	tool_steps = 0

	try:
		# Bootstrap (always — not from card yet)
		for boot_tool in ("perception_health", "perception_session_start"):
			env, ms = await agent.call(boot_tool, agent.args_for(boot_tool, case))
			card = _card(env)
			if card:
				card_hits += 1
			rec = StepRecord(
				i=len(report.steps),
				tool=boot_tool,
				ok=bool(env.get("ok")),
				latency_ms=ms,
				card_class=card.get("class"),
				card_next=card.get("next"),
				card_gate=card.get("gate"),
				card_claim_ok=card.get("claim_ok") if "claim_ok" in card else None,
				owed_families=[str(r.get("family")) for r in (card.get("owed") or []) if isinstance(r, dict)],
				followed_card=True,  # bootstrap is mandated by spine instructions, not guide URI
				error=None if env.get("ok") else str(env.get("error") or "fail"),
			)
			report.steps.append(rec)
			if not env.get("ok"):
				report.error = f"{boot_tool} failed: {env.get('error')}"
				return report

		# Prefer observe early so scan_id exists for snapshot tools
		prefer: str | None = None
		if case.expect_class in {"forms", "hotfix", "redesign", "greenfield"}:
			# First card-driven step: if next is structural and we have no scan, observe first when owed
			card0 = agent.last_card
			owed_tools = _owed_tools(card0)
			if "perception_navigate_and_observe" in owed_tools or case.expect_class in {
				"forms",
				"hotfix",
			}:
				prefer = "perception_navigate_and_observe"
			if case.expect_class == "forms" and "perception_probe_form" in owed_tools:
				# Observe first if unpaid observe is ahead; else probe after observe
				pass

		probe_done = False
		fail_counts: dict[str, int] = {}
		for _ in range(case.max_steps):
			card = agent.last_card
			if not card:
				report.notes.append("card_missing_mid_loop")
				break
			tool = _pick_tool(card, prefer=prefer)
			prefer = None  # only first preference
			# Skip tools that already failed once for slow component path (timeout/schema)
			skip_after = 1 if "component" in tool else 2
			if fail_counts.get(tool, 0) >= skip_after:
				alts = [
					t
					for t in _owed_tools(card)
					if fail_counts.get(t, 0) < skip_after and t != tool
				]
				# Prefer LOOK / snapshot over hammering foundation
				prefer_order = (
					"perception_visual_feedback",
					"perception_build_design_snapshot",
					"perception_navigate_and_observe",
					"perception_verify",
				)
				alts_sorted = [t for t in prefer_order if t in alts] + [
					t for t in alts if t not in prefer_order
				]
				if alts_sorted:
					tool = alts_sorted[0]
					report.notes.append(f"skip_failing_next→{tool}")
				else:
					report.notes.append(f"stuck_on_failing_tool:{tool}")
					break
			# Forms: after landing observe, prefer probe when owed
			if case.expect_class == "forms" and not probe_done:
				if tool == "perception_navigate_and_observe" or agent.scan_id:
					# After we have a page, next prefer probe if owed
					if "perception_probe_form" in _owed_tools(card) or card.get("class") == "forms":
						if agent.scan_id and tool != "perception_probe_form":
							# If next is inspiration etc., still pay observe first once
							if tool == "perception_navigate_and_observe":
								pass
							elif "perception_probe_form" in _owed_tools(card):
								tool = "perception_probe_form"

			args = agent.args_for(tool, case)
			# Snapshot without scan → observe first, then resume snapshot next turn
			if tool == "perception_build_design_snapshot" and not agent.scan_id and not args.get("scan_id"):
				tool = "perception_navigate_and_observe"
				args = agent.args_for(tool, case)
				prefer = "perception_build_design_snapshot"

			followed = tool in _owed_tools(card) or tool == card.get("next")
			# Sticky then= from redesign snapshot bridge counts as followed
			then = str((card.get("next_args") or {}).get("then") or "")
			if then and tool == "perception_navigate_and_observe" and then == "perception_build_design_snapshot":
				followed = True
			env, ms = await agent.call(tool, args)
			if not env.get("ok"):
				fail_counts[tool] = fail_counts.get(tool, 0) + 1
			# Treat timeout errors as hard skip for component
			err_l = str(env.get("error") or "").lower()
			if "timeout" in err_l or "timed out" in err_l:
				fail_counts[tool] = max(
					fail_counts.get(tool, 0),
					1 if "component" in tool else 2,
				)
			new_card = _card(env)
			if new_card:
				card_hits += 1
			tool_steps += 1
			if followed:
				follow_hits += 1
			# After observe, resume snapshot when card.then says so
			if (
				tool == "perception_navigate_and_observe"
				and env.get("ok")
				and then == "perception_build_design_snapshot"
			):
				prefer = "perception_build_design_snapshot"
			report.steps.append(
				StepRecord(
					i=len(report.steps),
					tool=tool,
					ok=bool(env.get("ok")),
					latency_ms=ms,
					card_class=new_card.get("class") or card.get("class"),
					card_next=new_card.get("next") or card.get("next"),
					card_gate=new_card.get("gate") or card.get("gate"),
					card_claim_ok=new_card.get("claim_ok") if new_card else card.get("claim_ok"),
					owed_families=[
						str(r.get("family"))
						for r in ((new_card or card).get("owed") or [])
						if isinstance(r, dict)
					],
					followed_card=followed,
					error=None if env.get("ok") else str(env.get("error") or "fail"),
				)
			)
			if tool == "perception_probe_form" and env.get("ok"):
				probe_done = True
			# Stop structural loop when forms probe paid, or owed empty + gate ready
			end_card = agent.last_card
			owed_left = end_card.get("owed") or []
			if case.finish == "forms" and probe_done:
				break
			if case.finish == "verify_text" and tool == "perception_navigate_and_observe" and env.get("ok"):
				break
			if case.finish == "structural_verify" and tool_steps >= 4:
				# Paid enough owed families — climb verify ladder
				break
			if case.finish == "none" and tool_steps >= 3:
				# Paid a few owed families — enough for card-adherence score
				break
			if not owed_left and end_card.get("gate") in {"ready", "open", "clear"}:
				break

		# Case finishers (still no guides)
		if case.finish == "forms":
			# Ensure on form page
			if not agent.scan_id:
				await agent.call(
					"perception_navigate_and_observe",
					agent.args_for("perception_navigate_and_observe", case),
				)
			ok_f, notes = await agent.finish_forms()
			report.finish_ok = ok_f
			report.verified = agent.verified
			report.notes.extend(notes)
		elif case.finish == "verify_text":
			ok_f, notes = await agent.finish_verify_text("Home")
			report.finish_ok = ok_f
			report.verified = agent.verified
			report.notes.extend(notes)
		elif case.finish == "structural_verify":
			ok_f, notes = await agent.finish_structural_verify("Home")
			report.finish_ok = ok_f
			report.verified = agent.verified
			report.notes.extend(notes)
		else:
			report.finish_ok = True  # structural adherence only
			report.verified = agent.verified

		report.got_class = (agent.last_card or {}).get("class")
		# Also check early session_start card class
		for s in report.steps:
			if s.tool == "perception_session_start" and s.card_class:
				report.got_class = s.card_class
				break
		# Prefer last non-null class
		for s in reversed(report.steps):
			if s.card_class:
				report.got_class = s.card_class
				break

		report.class_ok = report.got_class == case.expect_class
		n_card_eligible = max(1, len(report.steps))
		report.card_present_rate = card_hits / n_card_eligible
		report.followed_card_rate = (follow_hits / tool_steps) if tool_steps else 1.0
		report.guides_read = agent.guides_read
		report.claim_ok_at_end = (agent.last_card or {}).get("claim_ok")

		# Card-driven tool failures (missing args / schema) — face gap signal
		card_tool_fails = [
			s for s in report.steps if s.followed_card and not s.ok and s.tool.startswith("perception_")
			and s.tool not in {"perception_health", "perception_session_start", "perception_session_end"}
		]
		if card_tool_fails:
			report.notes.append(
				"card_next_tool_failed:"
				+ ",".join(f"{s.tool}({s.error})" for s in card_tool_fails[:3])
			)

		# Pass criteria — full ladder for structural cases requires verified
		pass_parts = [
			report.class_ok,
			report.guides_read == 0,
			report.card_present_rate >= 0.5,
			report.followed_card_rate >= 0.5,
			report.finish_ok is True,
			any(
				s.ok and s.followed_card and s.i >= 2
				for s in report.steps
			),
		]
		if case.finish in {"forms", "verify_text", "structural_verify"}:
			pass_parts.append(report.verified is True)
		# Hard fail: claim_ok true without verify
		if report.claim_ok_at_end and not report.verified:
			report.notes.append("FAIL:claim_ok_without_verified")
			pass_parts.append(False)
		report.ok = all(pass_parts)

	except Exception as exc:
		report.error = str(exc)
		report.ok = False
	finally:
		if agent.session_id:
			try:
				await asyncio.wait_for(
					agent.call("perception_session_end", {"session_id": agent.session_id}),
					timeout=8.0,
				)
			except Exception:
				pass

	return report


async def main() -> int:
	parser = argparse.ArgumentParser(description="No-guide agent_summary.card E2E")
	parser.add_argument("--url", default=DEFAULT_URL)
	parser.add_argument("--cases", default="forms,hotfix,greenfield,redesign")
	parser.add_argument("--out", default=str(OUT))
	args = parser.parse_args()

	from navigation.core.scan_registry import ScanRegistry
	from navigation.core.snapshot_registry import SnapshotRegistry
	from navigation.execution_runtime.runtime import ExecutionRuntime, configure
	from navigation.visual_browser_intelligence.browser.session_store import SessionStore

	wanted = {c.strip() for c in args.cases.split(",") if c.strip()}
	cases = [c for c in CASES if c.id in wanted]

	store = SessionStore(artifacts_root=ROOT / "artifacts" / "mcp-eval-no-guide")
	runtime = ExecutionRuntime(store, ScanRegistry(), SnapshotRegistry())
	configure(runtime)

	print(f"No-guide E2E — url={args.url} cases={[c.id for c in cases]}")
	print("Policy: follow agent_summary.card only; never read guides/spines\n")

	reports: list[CaseReport] = []
	try:
		for case in cases:
			print(f"=== {case.id} (expect class={case.expect_class}) ===")
			rep = await run_case(runtime, case, url=args.url, repo_root=str(ROOT))
			reports.append(rep)
			status = "PASS" if rep.ok else "FAIL"
			print(
				f"  {status} class={rep.got_class} card_rate={rep.card_present_rate:.2f} "
				f"follow={rep.followed_card_rate:.2f} guides={rep.guides_read} "
				f"finish={rep.finish_ok} verified={rep.verified}"
			)
			for s in rep.steps:
				flag = "✓" if s.followed_card else "·"
				err = f" err={s.error}" if s.error else ""
				print(
					f"    {flag} [{s.i}] {s.tool} ok={s.ok} {s.latency_ms}ms "
					f"class={s.card_class} next={s.card_next} gate={s.card_gate} "
					f"owed={s.owed_families}{err}"
				)
			for n in rep.notes:
				print(f"    note: {n}")
			if rep.error:
				print(f"    error: {rep.error}")
			print()
	finally:
		try:
			await asyncio.wait_for(store.end_all(), timeout=10.0)
		except Exception:
			pass

	payload = {
		"suite": "agent_face_no_guide_e2e",
		"url": args.url,
		"ok": all(r.ok for r in reports) and bool(reports),
		"passed": sum(1 for r in reports if r.ok),
		"total": len(reports),
		"cases": [asdict(r) for r in reports],
	}
	out = Path(args.out)
	out.parent.mkdir(parents=True, exist_ok=True)
	out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
	print(f"BOARD: {'PASS' if payload['ok'] else 'FAIL'} ({payload['passed']}/{payload['total']})")
	print(f"Wrote {out}")
	return 0 if payload["ok"] else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
