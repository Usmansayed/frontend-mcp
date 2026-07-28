from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from navigation.coordination_intelligence.models import ProjectSituationModel

CARD_SCHEMA = "coordinator_card.v1"
EPISODE_CARD_SCHEMA = "episode_card.v1"
AGENT_FACE_SCHEMA = "agent_face_card.v1"

_QUALITY_FLAGS = (
	"thin",
	"thin_clear",
	"revision_required",
	"soft_seed_partial",
	"evidence_useful",
	"seed_unresolved_count",
	"usable_image_refs",
)

# Family → default tool (agent face owed list)
# Keep component aligned with portfolio suggested (select, not bare search).
_FAMILY_TOOL: dict[str, str] = {
	"inspiration": "perception_inspiration_collect",
	"inspiration_extract": "perception_visual_feedback",
	"snapshot": "perception_build_design_snapshot",
	"component": "perception_select_component_foundation",
	"observe": "perception_navigate_and_observe",
	"visual_feedback": "perception_visual_feedback",
	"verify": "perception_verify",
	"forms": "perception_probe_form",
	"sections": "perception_observe",
	"residue": "perception_build_design_snapshot",
	"design_review": "perception_design_review",
}

_CAPABILITY_TOOL: dict[str, str] = {
	"inspiration_workflow": "perception_inspiration_collect",
	"design_snapshot": "perception_build_design_snapshot",
	"visual_feedback": "perception_visual_feedback",
	"component_intelligence": "perception_select_component_foundation",
	"component_select": "perception_select_component_foundation",
	"component_search_plan": "perception_plan_component_search",
	"observe": "perception_navigate_and_observe",
	"verify": "perception_verify",
	"design_review": "perception_design_review",
}

# Class-critical unpaid families — keep these in owed top-3 so agents don't tunnel.
_CLASS_OWED_PRIORITY: dict[str, tuple[str, ...]] = {
	"greenfield": (
		"inspiration",
		"inspiration_extract",
		"visual_feedback",
		"snapshot",
		"observe",
		"component",
		"verify",
		"sections",
		"design_review",
	),
	"redesign": (
		"snapshot",
		"observe",
		"visual_feedback",
		"component",
		"verify",
		"residue",
		"sections",
		"design_review",
	),
	"forms": ("forms", "observe", "verify", "visual_feedback", "sections"),
	"hotfix": ("observe", "visual_feedback", "verify"),
	"feature": ("observe", "component", "visual_feedback", "verify", "sections"),
}

# Families that must not appear on the face for a class (gate may still track them).
_CLASS_OWED_EXCLUDE: dict[str, frozenset[str]] = {
	"forms": frozenset({"component", "inspiration", "snapshot", "residue", "inspiration_extract"}),
	"hotfix": frozenset({"inspiration", "component", "snapshot", "residue", "inspiration_extract"}),
	# Feature spine is observe→component→verify — never invent gallery inspiration.
	"feature": frozenset({"inspiration", "inspiration_extract", "snapshot", "residue"}),
}

# Hard class next when owed is empty or only excluded families remain.
_CLASS_SPINE_NEXT: dict[str, str] = {
	"forms": "perception_probe_form",
	"hotfix": "perception_navigate_and_observe",
	"feature": "perception_navigate_and_observe",
	"redesign": "perception_build_design_snapshot",
	"greenfield": "perception_inspiration_collect",
}

# Minimal args a card-following agent must pass (no guide required).
_TOOL_NEXT_ARGS: dict[str, dict[str, Any]] = {
	"perception_select_component_foundation": {
		"query": "<component need from intent, e.g. 'primary CTA button'>",
	},
	"perception_search_components": {
		"query": "<component need from intent>",
	},
	"perception_plan_component_search": {
		"query": "<component need from intent>",
	},
	"perception_integrate_component": {
		"query": "<component need from intent>",
	},
	"perception_inspiration_collect": {
		"query": "<surface / brand direction from intent>",
		"inspiration_level": "light",
	},
	"perception_inspiration_discover": {
		"query": "<surface / brand direction from intent>",
	},
	"perception_visual_feedback": {
		"purpose": "design",
	},
	"perception_verify": {
		"criteria": {"text_contains": ["<expected visible text>"]},
	},
	"perception_probe_form": {
		"form": "<form name or leave for auto>",
	},
	"perception_navigate_and_observe": {
		"url": "<route>",
	},
	"perception_build_design_snapshot": {
		"scan_id": "<from observe>",
	},
}


def strategy_fingerprint(psm: ProjectSituationModel) -> str:
	ledger_bits = []
	for cap, outcome in sorted((psm.evidence.capability_ledger or {}).items()):
		if not isinstance(outcome, dict):
			continue
		q = outcome.get("quality") if isinstance(outcome.get("quality"), dict) else {}
		flags = {k: q.get(k) for k in _QUALITY_FLAGS if k in q}
		ledger_bits.append({
			"cap": cap,
			"status": outcome.get("status"),
			"adv": outcome.get("advancement_eligible"),
			"flags": flags,
		})
	section_raw = psm.episode.retry_counters.get("section_checklist")
	section_bits: list[dict[str, Any]] = []
	section_complete = False
	if isinstance(section_raw, dict):
		section_complete = bool(section_raw.get("complete"))
		for item in section_raw.get("sections") or []:
			if not isinstance(item, dict):
				continue
			section_bits.append({
				"id": item.get("section_id"),
				"o": bool(item.get("observed")),
				"v": bool(item.get("verified")),
			})
		section_bits.sort(key=lambda x: str(x.get("id") or ""))
	residual = {
		"verify": psm.episode.verification_status,
		"surface": getattr(psm.episode, "surface_type", None),
		"ship_clear": bool(psm.episode.retry_counters.get("ship_council_clear")),
		"ship_run": bool(psm.episode.retry_counters.get("ship_council_run")),
		"residue": psm.episode.retry_counters.get("residue_scan"),
		"sections_complete": section_complete,
		"sections": section_bits,
		"lifecycle": psm.situation.lifecycle_stage,
		"maturity": psm.situation.project_maturity,
		"sclass": psm.situation.situation_class,
		"intent": "|".join(f.intent for f in psm.episode.intent_stack),
		"active_route": getattr(psm.episode, "active_route_path", None)
		or psm.episode.retry_counters.get("active_route_path"),
		"routes": sorted(
			(
				f"{e.get('path')}:{e.get('surface')}"
				for e in (getattr(psm.episode, "route_surfaces", None) or {}).values()
				if isinstance(e, dict)
			)
		),
	}
	payload = {"ledger": ledger_bits, "ep": residual}
	raw = json.dumps(payload, sort_keys=True, default=str)
	return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def classify_agent_face(strategy: dict[str, Any]) -> str:
	"""Map strategy → one of five agent-facing spines."""
	scope = str(strategy.get("task_scope") or "").lower()
	surface = str(strategy.get("surface_type") or "").lower()
	resource = str(strategy.get("recommended_resource") or "").lower()
	# Intent / summary only for cue matching — never host_action.
	# Advisory strings like "RIGHT-SIZE POLISH" must not reclassify a feature episode.
	intentish = " ".join(
		str(strategy.get(k) or "")
		for k in ("intent", "summary", "user_intent", "original_intent")
	).lower()
	matters = " ".join(str(x) for x in (strategy.get("what_matters_now") or [])).lower()
	blob = f"{scope} {surface} {resource} {intentish} {matters}"

	rs = strategy.get("right_sizing") if isinstance(strategy.get("right_sizing"), dict) else {}
	tier = str(
		rs.get("tier")
		or strategy.get("effort_tier")
		or ""
	).lower()

	if scope in {"forms"}:
		return "forms"
	# Hard forms path: explicit form routes / probe language.
	if re.search(r"/forms/", blob) or re.search(
		r"\b(validation form|probe[_ ]?form|invalid then valid|invalid[\s-]?submit)\b",
		blob,
	):
		return "forms"
	# Redesign before soft forms keywords ("checkout redesign" must stay redesign).
	if (
		scope in {"redesign"}
		or "redesign" in blob
		or re.search(r"\bmockup\b", blob)
		or re.search(
			r"\b(reference image|uploaded (design|image|mock)|figma|match (this |the )?(design|mockup|reference))\b",
			blob,
		)
	):
		return "redesign"
	# Soft forms keywords — do not steal landing/hero greenfield, stamped features, or surgical fixes.
	if re.search(r"\b(forms?|checkout|sign[\s-]?up|login|auth)\b", blob):
		landingish = re.search(r"\b(landing|greenfield|hero|brand)\b", blob)
		featureish = scope in {"feature_incremental", "feature"} or re.search(
			r"\b(add|new)\b.{0,40}\bfeature\b|\bfeature\b.{0,40}\b(existing|page|toggle)\b",
			blob,
		)
		fixish = (
			scope in {"hotfix", "surgical", "debug"}
			or re.search(r"\bfix\b", blob) is not None
			or any(
				c in blob
				for c in (
					"overlapping",
					"bugfix",
					"css bug",
					"layout bug",
					"typo",
					"regression",
				)
			)
		)
		if not (landingish or featureish or fixish):
			return "forms"
	# Surgical/hotfix cues beat stamped feature_incremental (lifecycle often mid/feature).
	# Do NOT treat bare scope=debug as hotfix when intent is clearly an incremental feature —
	# observe often bumps cluster.debug.* and would otherwise flip the face mid-episode.
	hotfix_cues = (
		"hotfix",
		"bugfix",
		"overlapping",
		"broken",
		"crash",
		"regression",
		"typo",
		"css bug",
		"layout bug",
		"fix overlapping",
		"fix broken",
	)
	hotfix_from_intent = (
		"bugfix" in resource
		or any(c in blob for c in hotfix_cues)
		or re.search(r"\bfix\b", blob) is not None
	)
	if scope in {"hotfix", "surgical"} or hotfix_from_intent:
		return "hotfix"
	# Polish/chrome text cues before greenfield; do not let polish-tier alone steal features.
	polish_cues = (
		"polish",
		"tighten spacing",
		"spacing only",
		"navbar only",
		"chrome only",
		"tighten chrome",
		"touch up",
		"touch-up",
		"visual polish",
	)
	if any(c in blob for c in polish_cues):
		return "hotfix"
	# Feature scope / intent language before polish-tier defaults and before debug→hotfix.
	feature_from_intent = re.search(
		r"\b(add|new)\b.{0,48}\b(feature|toggle)\b"
		r"|\bincremental feature\b"
		r"|\bfeature\b.{0,40}\b(existing|page|toggle)\b",
		blob,
	)
	if (
		scope in {"feature_incremental", "feature"}
		or feature_from_intent
		or (re.search(r"\bfeature\b", resource) and "hotfix" not in blob and "polish" not in blob)
	):
		return "feature"
	if scope in {"debug"}:
		return "hotfix"
	if tier in {"polish", "touch_up"} and scope in {"design_driven", "system_setup", ""}:
		return "hotfix"
	if scope in {"design_driven", "system_setup"} or "design-workflow" in resource:
		return "greenfield"
	# Landing / new page cues before defaulting to influence
	if re.search(r"\b(landing|greenfield|new (saas |product )?page|hero)\b", blob):
		return "greenfield"
	influence = str(strategy.get("influence_level") or "").lower()
	if influence in {"structural", "balanced"}:
		return "greenfield"
	return "hotfix"


def _owed_from_portfolio(
	strategy: dict[str, Any],
	*,
	face_class: str,
	limit: int = 3,
) -> list[dict[str, Any]]:
	portfolio = strategy.get("episode_portfolio") or {}
	unpaid = [row for row in (portfolio.get("unpaid") or []) if isinstance(row, dict)]
	exclude = _CLASS_OWED_EXCLUDE.get(face_class) or frozenset()
	if exclude:
		unpaid = [
			row
			for row in unpaid
			if str(row.get("family") or "") not in exclude
		]
	# Forms class always owes probe until forms family is paid (portfolio often empty
	# outside design-initiative scope — without this, gate steers to component).
	# Once verify passed, do not re-inject (claim_ok + next=probe forever).
	if face_class == "forms" and str(strategy.get("verification_status") or "").lower() != "passed":
		paid = {
			str(p.get("family"))
			for p in (portfolio.get("paid") or [])
			if isinstance(p, dict) and p.get("family")
		}
		if "forms" not in paid and not any(str(u.get("family")) == "forms" for u in unpaid):
			unpaid = [
				{
					"family": "forms",
					"reason": "form not probed",
					"suggested": "perception_probe_form",
				},
				*unpaid,
			]
	# Redesign must keep snapshot owed until measured — observe alone must not drop it.
	if face_class == "redesign":
		paid = {
			str(p.get("family"))
			for p in (portfolio.get("paid") or [])
			if isinstance(p, dict) and p.get("family")
		}
		if "snapshot" not in paid and not any(str(u.get("family")) == "snapshot" for u in unpaid):
			unpaid = [
				{
					"family": "snapshot",
					"reason": "redesign requires measured snapshot",
					"suggested": "perception_build_design_snapshot",
				},
				*unpaid,
			]
	priority = _CLASS_OWED_PRIORITY.get(face_class) or ()
	rank = {fam: i for i, fam in enumerate(priority)}

	def _sort_key(row: dict[str, Any]) -> tuple[int, int]:
		fam = str(row.get("family") or "")
		return (rank.get(fam, 100), 0)

	owed: list[dict[str, Any]] = []
	for row in sorted(unpaid, key=_sort_key):
		family = str(row.get("family") or "").strip()
		if not family:
			continue
		tool = str(row.get("suggested") or _FAMILY_TOOL.get(family) or "").strip()
		if tool == "perception_plan_component_search":
			tool = "perception_select_component_foundation"
		entry: dict[str, Any] = {"family": family, "tool": tool}
		hint = _TOOL_NEXT_ARGS.get(tool)
		if hint:
			entry["args"] = dict(hint)
		owed.append(entry)
		if len(owed) >= limit:
			break
	return owed


def _paid_families(strategy: dict[str, Any]) -> set[str]:
	portfolio = strategy.get("episode_portfolio") or {}
	return {
		str(p.get("family"))
		for p in (portfolio.get("paid") or [])
		if isinstance(p, dict) and p.get("family")
	}


def _pick_class_next(
	*,
	face_class: str,
	owed: list[dict[str, Any]],
	gate: dict[str, Any],
	suggested_capability: str | None,
	strategy: dict[str, Any],
) -> str:
	"""Class spine + done-ladder beat gate leftovers (e.g. plan_component_search)."""
	spine = _CLASS_SPINE_NEXT.get(face_class)

	if owed and owed[0].get("tool"):
		tool = str(owed[0]["tool"])
		# Never surface plan-only as the agent next — select is the resolving call.
		if tool == "perception_plan_component_search":
			return "perception_select_component_foundation"
		return tool

	# Empty owed: finish verify / claim_extra before falling into gate component plan.
	status = str(strategy.get("verification_status") or "").lower()
	extra = _claim_extra(strategy, gate)
	if status != "passed":
		if face_class == "forms":
			paid = _paid_families(strategy)
			return "perception_verify" if "forms" in paid else "perception_probe_form"
		if face_class in {"hotfix", "feature"}:
			# Empty portfolio outside design initiative — still observe before verify.
			return "perception_verify" if "observe" in _paid_families(strategy) else (
				spine or "perception_navigate_and_observe"
			)
		return "perception_verify"
	if "section_checklist" in extra:
		return "perception_observe"
	if "ship_council" in extra:
		return "perception_design_review"
	if "spec_revision" in extra:
		return "perception_build_design_snapshot"

	# G1: verify passed + no claim_extra → episode complete; do not re-spine forever.
	return ""


def _apply_redesign_snapshot_bridge(
	*,
	face_class: str,
	next_tool: str,
	owed: list[dict[str, Any]],
	strategy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
	"""If snapshot is next but live observe unpaid, observe first then resume snapshot."""
	bridge: dict[str, Any] = {}
	if face_class != "redesign":
		return next_tool, bridge
	# Post-verify remeasure (spec revision) — do not force observe-before-snapshot.
	if (
		str(strategy.get("verification_status") or "").lower() == "passed"
		and next_tool == "perception_build_design_snapshot"
	):
		return next_tool, bridge
	snapshot_owed = any(o.get("family") == "snapshot" for o in owed)
	if next_tool != "perception_build_design_snapshot" and not snapshot_owed:
		return next_tool, bridge
	paid = _paid_families(strategy)
	if "observe" in paid or strategy.get("active_route"):
		return (
			"perception_build_design_snapshot"
			if snapshot_owed or next_tool == "perception_build_design_snapshot"
			else next_tool
		), bridge
	# Need a scan before snapshot — sticky then=
	bridge["then"] = "perception_build_design_snapshot"
	return "perception_navigate_and_observe", bridge


def _next_args_for(tool: str, strategy: dict[str, Any], face_class: str) -> dict[str, Any]:
	base = dict(_TOOL_NEXT_ARGS.get(tool) or {})
	intent = " ".join(
		str(strategy.get(k) or "")
		for k in ("intent", "summary", "user_intent", "original_intent")
	).strip()
	# Fill concrete query from intent when possible (avoids bare select hang).
	if "query" in base and intent:
		if tool.startswith("perception_inspiration"):
			base["query"] = intent[:120]
		elif "component" in tool or tool.endswith("_foundation"):
			base["query"] = intent[:120]
	if tool == "perception_visual_feedback":
		base["purpose"] = {
			"forms": "forms",
			"hotfix": "hotfix",
			"greenfield": "inspiration",
			"redesign": "design",
			"feature": "component",
		}.get(face_class, "general")
	if tool == "perception_probe_form" and intent:
		# Prefer concrete form name from intent path when present
		m = re.search(r"/forms/([a-z0-9_-]+)", intent)
		if m:
			base["form"] = m.group(1)
		elif "validation" in intent.lower():
			base["form"] = "validation"
	return base


def _claim_extra(strategy: dict[str, Any], gate: dict[str, Any]) -> list[str]:
	extra: list[str] = []
	if gate.get("section_checklist_required"):
		extra.append("section_checklist")
	if gate.get("ship_council_required"):
		extra.append("ship_council")
	if gate.get("spec_revision_required") or (
		isinstance(strategy.get("spec_revision_gate"), dict)
		and strategy["spec_revision_gate"].get("revision_required")
	):
		extra.append("spec_revision")
	return extra


def _claim_ok(strategy: dict[str, Any], gate: dict[str, Any], owed: list[dict[str, Any]]) -> bool:
	"""Claim-done only when gate allows AND verify is paid AND claim_extra cleared."""
	if "claim_complete" in list(gate.get("prohibited_actions") or []):
		return False
	# G2: ship/sections/spec still listed → never claimable.
	if _claim_extra(strategy, gate):
		return False
	owed_families = {str(r.get("family")) for r in owed}
	if "verify" in owed_families or "sections" in owed_families or "design_review" in owed_families:
		return False
	portfolio = strategy.get("episode_portfolio") or {}
	unpaid = {
		str(u.get("family"))
		for u in (portfolio.get("unpaid") or [])
		if isinstance(u, dict) and u.get("family")
	}
	if "verify" in unpaid or "sections" in unpaid or "design_review" in unpaid:
		return False
	status = str(strategy.get("verification_status") or "").lower()
	if status and status != "passed":
		return False
	# maintenance/ready with empty prohibited but never verified → still not claimable
	if not status:
		paid = {
			str(p.get("family"))
			for p in (portfolio.get("paid") or [])
			if isinstance(p, dict) and p.get("family")
		}
		if "verify" not in paid:
			return False
	return True


# light = surgical verify floor; standard = look+verify; full = initiative ladder
_DEPTH_RANK = {"light": 0, "standard": 1, "full": 2}
_CLASS_DEFAULT_DEPTH: dict[str, str] = {
	"hotfix": "light",
	"forms": "light",
	"feature": "standard",
	"greenfield": "full",
	"redesign": "full",
}
_TIER_TO_DEPTH: dict[str, str] = {
	"touch_up": "light",
	"polish": "standard",
	"feature": "standard",
	"initiative": "full",
}


def _resolve_depth(
	*,
	face_class: str,
	strategy: dict[str, Any],
	gate: dict[str, Any],
	claim_extra: list[str],
) -> str:
	"""How deep the Done ladder must go for this situation."""
	depth = _CLASS_DEFAULT_DEPTH.get(face_class, "standard")
	rs = strategy.get("right_sizing") if isinstance(strategy.get("right_sizing"), dict) else {}
	tier = str(
		rs.get("tier")
		or strategy.get("effort_tier")
		or (gate.get("right_sizing") or {}).get("tier")
		or ""
	).lower()
	if tier in _TIER_TO_DEPTH:
		# Take the deeper of class default and effort tier (never under-serve greenfield).
		cand = _TIER_TO_DEPTH[tier]
		if _DEPTH_RANK[cand] > _DEPTH_RANK[depth]:
			depth = cand
		# Explicit touch_up/polish on hotfix/forms may stay light
		if face_class in {"hotfix", "forms"} and tier in {"touch_up", "polish"}:
			depth = _TIER_TO_DEPTH[tier]
	# Gate ceremony forces full regardless of class default
	if claim_extra or gate.get("ship_council_required") or gate.get("section_checklist_required"):
		depth = "full"
	influence = str(strategy.get("influence_level") or "").lower()
	if influence == "structural" and face_class in {"greenfield", "redesign"}:
		depth = "full"
	return depth


def _finish_item(item_id: str, *, status: str, tool: str | None = None, note: str | None = None) -> dict[str, Any]:
	row: dict[str, Any] = {"id": item_id, "status": status}
	if tool:
		row["tool"] = tool
	if note:
		row["note"] = note
	return row


def _build_finish_checklist(
	*,
	face_class: str,
	depth: str,
	strategy: dict[str, Any],
	owed: list[dict[str, Any]],
	claim_extra: list[str],
	claim_ok: bool,
) -> list[dict[str, Any]]:
	"""Exact done steps for this depth — agent should not invent extra ceremony."""
	paid = _paid_families(strategy)
	verified = str(strategy.get("verification_status") or "").lower() == "passed"
	owed_families = {str(o.get("family")) for o in owed}

	def _fam_status(family: str, *, tool: str) -> dict[str, Any]:
		if family in paid and family not in owed_families:
			return _finish_item(family, status="done", tool=tool)
		if family in owed_families or family not in paid:
			return _finish_item(family, status="todo", tool=tool)
		return _finish_item(family, status="done", tool=tool)

	finish: list[dict[str, Any]] = [
		_finish_item("bootstrap", status="done", note="health → session_start"),
	]

	if face_class == "forms":
		finish.append(_fam_status("forms", tool="perception_probe_form"))
		finish.append(
			_finish_item(
				"verify",
				status="done" if verified else "todo",
				tool="perception_verify",
				note="invalid then valid",
			)
		)
	elif face_class == "hotfix":
		finish.append(_fam_status("observe", tool="perception_navigate_and_observe"))
		finish.append(
			_finish_item("verify", status="done" if verified else "todo", tool="perception_verify")
		)
	elif depth == "standard":
		finish.append(_fam_status("observe", tool="perception_navigate_and_observe"))
		finish.append(_fam_status("visual_feedback", tool="perception_visual_feedback"))
		if "component" in owed_families or "component" in paid:
			finish.append(_fam_status("component", tool="perception_select_component_foundation"))
		finish.append(
			_finish_item("verify", status="done" if verified else "todo", tool="perception_verify")
		)
	else:  # full
		if face_class == "redesign":
			finish.append(_fam_status("observe", tool="perception_navigate_and_observe"))
			finish.append(_fam_status("snapshot", tool="perception_build_design_snapshot"))
			finish.append(_fam_status("visual_feedback", tool="perception_visual_feedback"))
		elif face_class == "feature":
			# Feature never invents gallery inspiration (G4).
			finish.append(_fam_status("observe", tool="perception_navigate_and_observe"))
			finish.append(_fam_status("visual_feedback", tool="perception_visual_feedback"))
			if "component" in owed_families or "component" in paid:
				finish.append(_fam_status("component", tool="perception_select_component_foundation"))
		else:
			finish.append(_fam_status("inspiration", tool="perception_inspiration_collect"))
			finish.append(_fam_status("visual_feedback", tool="perception_visual_feedback"))
			finish.append(_fam_status("observe", tool="perception_navigate_and_observe"))
			if "component" in owed_families or "component" in paid or depth == "full":
				finish.append(_fam_status("component", tool="perception_select_component_foundation"))
		if face_class == "redesign" and (
			"component" in owed_families or "component" in paid or depth == "full"
		):
			finish.append(_fam_status("component", tool="perception_select_component_foundation"))
		finish.append(
			_finish_item("verify", status="done" if verified else "todo", tool="perception_verify")
		)

	if depth == "full" or "section_checklist" in claim_extra:
		sec_done = "sections" in paid and "section_checklist" not in claim_extra
		finish.append(
			_finish_item(
				"section_checklist",
				status="done" if sec_done else ("todo" if "section_checklist" in claim_extra or depth == "full" else "skip"),
				tool="perception_observe",
				note="observe→verify each section when required",
			)
		)
	else:
		finish.append(_finish_item("section_checklist", status="skip", note=f"depth={depth}"))

	if depth == "full" or "ship_council" in claim_extra:
		ship_done = "design_review" in paid and "ship_council" not in claim_extra
		finish.append(
			_finish_item(
				"ship_council",
				status="done" if ship_done else ("todo" if "ship_council" in claim_extra or depth == "full" else "skip"),
				tool="perception_design_review",
				note="mode=ship",
			)
		)
	else:
		finish.append(_finish_item("ship_council", status="skip", note=f"depth={depth}"))

	if "spec_revision" in claim_extra:
		finish.append(
			_finish_item(
				"spec_revision",
				status="todo",
				tool="perception_build_design_snapshot",
				note="revise SpecDiff drifts",
			)
		)

	finish.append(
		_finish_item(
			"claim",
			status="done" if claim_ok and verified else "blocked",
			note="requires data.verified=true and claim_ok",
		)
	)
	# Normalize: full depth marks section/ship as todo until paid even if not yet in claim_extra
	if depth == "full":
		for row in finish:
			if row["id"] in {"section_checklist", "ship_council"} and row["status"] == "skip":
				row["status"] = "todo"
	return finish


def build_agent_face_card(
	*,
	episode_id: str,
	strategy: dict[str, Any] | None,
	suggested_capability: str | None = None,
) -> dict[str, Any]:
	"""Single agent-facing card — next / owed / gate / claim_extra / resource.

	Internals stay rich; this is the only field agents should need each turn.
	"""
	strategy = strategy or {}
	gate = dict(strategy.get("implementation_gate") or {})
	face_class = classify_agent_face(strategy)
	owed = _owed_from_portfolio(strategy, face_class=face_class, limit=3)

	next_tool = _pick_class_next(
		face_class=face_class,
		owed=owed,
		gate=gate,
		suggested_capability=suggested_capability,
		strategy=strategy,
	)
	next_tool, bridge = _apply_redesign_snapshot_bridge(
		face_class=face_class,
		next_tool=next_tool,
		owed=owed,
		strategy=strategy,
	)

	resource = str(strategy.get("recommended_resource") or "")
	spine = f"perception://spine/{face_class}"
	if not resource or resource.startswith("perception://guide/") or resource in {
		"perception://getting-started",
		"perception://frontend-methodology",
		"perception://design-workflow",
		"perception://redesign-workflow",
		"perception://bugfix-workflow",
		"perception://agent-coordination",
	}:
		resource = spine

	next_args = _next_args_for(next_tool, strategy, face_class) if next_tool else {}
	# Prefer owed[0].args when present (already class-tuned).
	if next_tool and owed and isinstance(owed[0].get("args"), dict) and owed[0].get("tool") == next_tool:
		merged = dict(owed[0]["args"])
		merged.update({k: v for k, v in next_args.items() if k not in merged or str(merged[k]).startswith("<")})
		# Intent-filled query wins over placeholder
		if next_args.get("query") and not str(next_args["query"]).startswith("<"):
			merged["query"] = next_args["query"]
		next_args = merged
	if bridge.get("then"):
		next_args["then"] = bridge["then"]
	claim_extra = _claim_extra(strategy, gate)
	# Ship council args when that's the next
	if next_tool == "perception_design_review" and "ship_council" in claim_extra:
		next_args["mode"] = "ship"

	claim_ok = _claim_ok(strategy, gate, owed)
	depth = _resolve_depth(
		face_class=face_class,
		strategy=strategy,
		gate=gate,
		claim_extra=claim_extra,
	)
	finish = _build_finish_checklist(
		face_class=face_class,
		depth=depth,
		strategy=strategy,
		owed=owed,
		claim_extra=claim_extra,
		claim_ok=claim_ok,
	)

	return {
		"schema": AGENT_FACE_SCHEMA,
		"episode_id": episode_id,
		"class": face_class,
		"depth": depth,
		"next": next_tool,
		"next_args": next_args,
		"owed": owed,
		"gate": str(gate.get("state") or "unknown"),
		"claim_ok": claim_ok,
		"claim_extra": claim_extra,
		"finish": finish,
		"resource": resource,
		"host_action": strategy.get("host_action"),
	}


def build_coordinator_card(
	*,
	episode_id: str,
	strategy: dict[str, Any] | None,
	suggested_capability: str | None = None,
	suggested_semantic_action: str | None = None,
	stop_reason: str | None = None,
) -> dict[str, Any]:
	strategy = strategy or {}
	gate = dict(strategy.get("implementation_gate") or {})
	conf = strategy.get("episode_confidence") or {}
	portfolio = strategy.get("episode_portfolio") or {}
	paid = [
		str(p.get("family"))
		for p in (portfolio.get("paid") or [])
		if isinstance(p, dict) and p.get("family")
	]
	unpaid = [
		str(u.get("family"))
		for u in (portfolio.get("unpaid") or [])
		if isinstance(u, dict) and u.get("family")
	]
	return {
		"schema": CARD_SCHEMA,
		"episode_id": episode_id,
		"integrated": True,
		"host_action": strategy.get("host_action"),
		"gate": {
			"state": gate.get("state"),
			"next_required_capability": gate.get("next_required_capability"),
			"prohibited_actions": list(gate.get("prohibited_actions") or []),
		},
		"implementation_gate": gate,  # one-cycle alias
		"suggested_capability": suggested_capability,
		"suggested_semantic_action": suggested_semantic_action,
		"stop_reason": stop_reason,
		"confidence": {
			"score": conf.get("score"),
			"band": conf.get("band"),
		},
		"portfolio": {"paid": paid, "unpaid": unpaid},
		"evidence_quality_alerts": list(strategy.get("evidence_quality_alerts") or []),
		"recommended_resource": strategy.get("recommended_resource"),
		"active_route": strategy.get("active_route"),
		"routes": list(strategy.get("routes") or []),
		"right_sizing": strategy.get("right_sizing"),
	}


def build_episode_card(
	*,
	episode_id: str,
	strategy: dict[str, Any] | None,
	suggested_capability: str | None = None,
	suggested_semantic_action: str | None = None,
	stop_reason: str | None = None,
) -> dict[str, Any]:
	"""Unified agent-facing readout — coordinator card + what_matters one-liner."""
	strategy = strategy or {}
	base = build_coordinator_card(
		episode_id=episode_id,
		strategy=strategy,
		suggested_capability=suggested_capability,
		suggested_semantic_action=suggested_semantic_action,
		stop_reason=stop_reason,
	)
	matters = list(strategy.get("what_matters_now") or [])
	what_matters = str(matters[0]) if matters else str(strategy.get("host_action") or "")
	return {
		**base,
		"schema": EPISODE_CARD_SCHEMA,
		"what_matters": what_matters,
		"surface_type": strategy.get("surface_type") or "unknown",
		"influence_level": strategy.get("influence_level"),
		"active_route": strategy.get("active_route"),
		"routes": list(strategy.get("routes") or []),
		"right_sizing": strategy.get("right_sizing"),
	}
