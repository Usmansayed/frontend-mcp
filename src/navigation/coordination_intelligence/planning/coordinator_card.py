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
	"resources": "perception_creative_assets",
	"consistency": "perception_consistency_audit",
	"fidelity": "perception_visual_feedback",
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
	"resource_workflow": "perception_creative_assets",
	"observe": "perception_navigate_and_observe",
	"verify": "perception_verify",
	"design_review": "perception_design_review",
}

# Class-critical unpaid families — keep these in owed top-3 so agents don't tunnel.
_CLASS_OWED_PRIORITY: dict[str, tuple[str, ...]] = {
	"greenfield": (
		"inspiration",
		"inspiration_extract",
		"component",
		"resources",
		"visual_feedback",
		"fidelity",
		"consistency",
		"snapshot",
		"observe",
		"verify",
		"sections",
		"design_review",
	),
	"redesign": (
		"snapshot",
		"observe",
		"inspiration_extract",
		"component",
		"resources",
		"visual_feedback",
		"fidelity",
		"consistency",
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
	"forms": frozenset(
		{
			"component",
			"inspiration",
			"snapshot",
			"residue",
			"inspiration_extract",
			"resources",
			"consistency",
			"fidelity",
		}
	),
	"hotfix": frozenset(
		{
			"inspiration",
			"component",
			"snapshot",
			"residue",
			"inspiration_extract",
			"resources",
			"consistency",
			"fidelity",
		}
	),
	# Feature spine is observe→component→verify — never invent gallery inspiration.
	"feature": frozenset({"inspiration", "inspiration_extract", "snapshot", "residue", "fidelity"}),
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
	"perception_creative_assets": {
		"query": "<fonts / patterns / gradients / icons / motion / graphics from intent>",
		"categories": ["font", "pattern", "gradient", "icon"],
	},
	"perception_consistency_audit": {
		"repo_root": "<repo root>",
		"scan_id": "<from observe>",
	},
	"perception_design_graph_refresh": {
		"repo_root": "<repo root>",
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


def _unpaid_families(strategy: dict[str, Any]) -> set[str]:
	portfolio = strategy.get("episode_portfolio") or {}
	return {
		str(u.get("family"))
		for u in (portfolio.get("unpaid") or [])
		if isinstance(u, dict) and u.get("family")
	}


def _structural_design_pressure(strategy: dict[str, Any]) -> bool:
	"""True when gate/portfolio/policy say greenfield/redesign ladder — not surgical hotfix."""
	policy = str(strategy.get("policy_id") or "").lower()
	if policy.startswith("design.greenfield") or policy.startswith("design.redesign"):
		return True
	gate = strategy.get("implementation_gate") if isinstance(strategy.get("implementation_gate"), dict) else {}
	next_cap = str(gate.get("next_required_capability") or "").lower()
	if next_cap in {
		"inspiration_workflow",
		"design_snapshot",
		"component_intelligence",
		"component_select",
		"component_search_plan",
	}:
		scope = str(strategy.get("task_scope") or "").lower()
		if scope in {"design_driven", "system_setup", "redesign", ""}:
			return True
	unpaid = _unpaid_families(strategy)
	if unpaid & {"inspiration", "inspiration_extract", "snapshot"}:
		scope = str(strategy.get("task_scope") or "").lower()
		if scope in {"design_driven", "system_setup", "redesign"}:
			return True
	# Initiative tier + structural influence + unpaid visual/component is design work.
	rs = strategy.get("right_sizing") if isinstance(strategy.get("right_sizing"), dict) else {}
	tier = str(rs.get("tier") or strategy.get("effort_tier") or "").lower()
	influence = str(strategy.get("influence_level") or "").lower()
	if (
		tier == "initiative"
		and influence == "structural"
		and unpaid & {"inspiration", "inspiration_extract", "snapshot", "component", "visual_feedback"}
	):
		return True
	return False


def _redesign_intent_cues(intent_blob: str) -> bool:
	"""True when user intent is mockup/reference match or explicit redesign."""
	return bool(
		re.search(r"\bredesign\b", intent_blob)
		or re.search(r"\brestyle\b", intent_blob)
		or re.search(r"\bmockup\b", intent_blob)
		or re.search(
			r"\b(reference image|uploaded (design|image|mock)|figma|"
			r"match (this |the )?(design|mockup|reference|new brand|brand system))\b",
			intent_blob,
		)
		or re.search(
			r"\b(match|align).{0,48}\b(brand(ing)?|design system|brand system)\b",
			intent_blob,
		)
		or _design_fix_intent_cues(intent_blob)
	)


def _defect_fix_intent_cues(intent_blob: str) -> bool:
	"""True for broken/overlapping/bug language — stay surgical hotfix."""
	return bool(
		re.search(
			r"\b("
			r"hotfix|bugfix|overlapping|broken|crash|regression|typo|"
			r"css\s+bug|layout\s+bug|fix\s+overlapping|fix\s+broken|"
			r"fix\s+(the\s+)?(broken|overlapping|css|bug)\b|"
			r"fix\s+.{0,24}\b(bug|broken|overlapping|crash)\b"
			r")\b",
			intent_blob,
		)
		or re.search(
			r"\bfix\b.{0,40}\b(padding|margin|gap)\b.{0,24}\b(from\s+)?\d+",
			intent_blob,
		)
	)


def _design_fix_intent_cues(intent_blob: str) -> bool:
	"""Vague 'fix the design / look / footer' without defect words → redesign.

	Bare 'fix' often means taste/direction, not a CSS bug. Defect language
	still wins via _defect_fix_intent_cues / surgical cues.
	"""
	text = str(intent_blob or "").strip().lower()
	if not text or _defect_fix_intent_cues(text):
		return False
	# Explicit design-direction / taste language.
	if re.search(
		r"\b("
		r"fix\s+(the\s+)?(design|look|appearance|styling|visuals?|ui|ux|brand(ing)?|theme|style)\b|"
		r"fix\s+how\s+it\s+looks|"
		r"make\s+(it|this|the\s+\w+).{0,24}\blook\s+(better|nicer|cleaner|modern|good|great)|"
		r"make\s+(it|this).{0,16}\b(prettier|nicer|better\s+looking)|"
		r"looks?\s+(bad|ugly|cheap|dated|off[-\s]?brand|wrong|off)|"
		r"improve\s+(the\s+)?(design|look|visual|ui|ux|branding)|"
		r"(needs?|could use)\s+(a\s+)?(redesign|restyle|visual\s+refresh)|"
		r"visual\s+refresh|design\s+refresh"
		r")\b",
		text,
	):
		return True
	# Vague fix of a design surface / page chrome (surface must follow "fix" closely).
	# Avoid "fix checkout copy on the existing page" false positives.
	if re.search(
		r"\bfix\s+(the\s+|a\s+|our\s+|this\s+|that\s+)?("
		r"footer|header|hero|navbar|nav|landing(\s+page)?|homepage|home\s+page|"
		r"page|section|layout|sidebar|drawer|modal|"
		r"marketing(\s+site)?|site|screen|ui|ux|design|look|appearance|styling"
		r")\b",
		text,
	):
		return True
	# Ultra-vague: "fix it / fix this / just fix it" with no defect specificity.
	if re.search(r"\b(just\s+)?fix\s+(it|this|that|everything)\b", text):
		return True
	return False


def _additive_feature_intent(intent_blob: str) -> bool:
	"""True when user intent is clearly adding a block/control to an existing surface."""
	return bool(
		re.search(
			r"\b(add|new)\b.{0,64}\b("
			r"feature|toggle|section|block|module|bell|button|component|widget"
			r"|comparison|carousel|control"
			r")\b"
			r"|\b(add|new)\b.{0,64}\bto (the |an )?existing\b"
			r"|\bincremental feature\b"
			# Mid-product polish of an existing shell — not greenfield initiative.
			r"|\bimprove\b.{0,64}\bexisting\b"
			r"|\bimprove\b.{0,80}\b(page|hierarchy|cta|copy|marketing)\b",
			intent_blob,
		)
	)


def _greenfield_intent_cues(intent_blob: str) -> bool:
	"""Strong from-scratch / brand-landing language — beats stamped hotfix scope."""
	return bool(
		re.search(
			r"\b("
			r"from scratch|greenfield|new (saas |product )?(landing|marketing|site)"
			r"|brand(-|\s)?first|distinctive brand|strong brand hero|branded (landing|marketing)"
			r")\b",
			intent_blob,
		)
	)


def _surgical_intent_cues(intent_blob: str, *, scope: str = "", resource: str = "") -> bool:
	"""True only for explicit surgical / chrome language in user intent (not advisory prose)."""
	if scope in {"hotfix", "surgical"}:
		# Stamped hotfix/surgical scope must not steal greenfield/redesign intents (H02).
		if _greenfield_intent_cues(intent_blob) or _redesign_intent_cues(intent_blob):
			return False
		return True
	if "bugfix" in resource:
		return True
	# Defect / bug language — surgical.
	if _defect_fix_intent_cues(intent_blob):
		return True
	# Vague design-fix ("fix the footer/look/design") is redesign, not hotfix.
	if _design_fix_intent_cues(intent_blob):
		return False
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
	if any(c in intent_blob for c in polish_cues):
		return True
	# Bare "fix": surgical only when not a design-direction ask.
	if re.search(r"\bfix\b", intent_blob) is None:
		return False
	# "Add a feature to fix X" — fix is the job → surgical.
	if re.search(r"\b(add|new)\b.{0,40}\bfeature\b.{0,32}\bto fix\b", intent_blob):
		return True
	if _additive_feature_intent(intent_blob):
		# Trailing soft fix ("— then fix any spacing if needed") must not steal feature.
		if re.search(
			r"[—\-–]|(\bthen\b.{0,24}\bfix\b)|(\bfix\b.{0,24}\bif needed\b)",
			intent_blob,
		):
			return False
		# Leading additive clause without strong fix coupling → not surgical.
		if re.search(
			r"^\s*(add|new)\b",
			intent_blob,
		) and not re.search(r"\bto fix\b|\bfix (the |a )?(broken|overlapping|bug)", intent_blob):
			return False
	# Leftover bare "fix …" without design-surface/taste cues → keep surgical.
	return True


def classify_agent_face(strategy: dict[str, Any]) -> str:
	"""Map strategy → one of five agent-facing spines."""
	scope = str(strategy.get("task_scope") or "").lower()
	surface = str(strategy.get("surface_type") or "").lower()
	resource = str(strategy.get("recommended_resource") or "").lower()
	# Lexical cues: user-authored intent only.
	# Never match summary / what_matters_now / host_action — those often say
	# "observe, fix, verify" or "RIGHT-SIZE POLISH" and poisoned Run 6 into hotfix
	# under design.greenfield unpaid inspiration.
	intent_blob = " ".join(
		str(strategy.get(k) or "")
		for k in ("intent", "user_intent", "original_intent")
	).lower()
	# Stamps + intent for route/scope signals (not advisory prose).
	blob = f"{scope} {surface} {resource} {intent_blob}"

	rs = strategy.get("right_sizing") if isinstance(strategy.get("right_sizing"), dict) else {}
	tier = str(
		rs.get("tier")
		or strategy.get("effort_tier")
		or ""
	).lower()

	if scope in {"forms"}:
		return "forms"
	# Hard forms path: explicit form routes / probe / validation language.
	# Beats feature_incremental stamps ("Wire up the contact form validation").
	if re.search(r"/forms/", blob) or re.search(
		r"\b("
		r"validation form|probe[_ ]?form|invalid then valid|invalid[\s-]?submit"
		r"|form\s+validation|contact\s+form"
		r"|wire\s+up.{0,48}\bform"
		r")\b",
		intent_blob,
	):
		return "forms"
	# Redesign before soft forms keywords ("checkout redesign" must stay redesign).
	if scope in {"redesign"} or _redesign_intent_cues(intent_blob):
		return "redesign"
	# Run 6b P0: design.greenfield / unpaid inspiration must win BEFORE surgical defaults
	# when the user intent is not explicitly a fix/polish. Conflict-only was insufficient
	# for card-only hosts.
	if _structural_design_pressure(strategy) and not _surgical_intent_cues(
		intent_blob, scope=scope, resource=resource
	):
		if not _additive_feature_intent(intent_blob):
			return "greenfield"
	# Soft forms keywords — do not steal landing/hero greenfield, stamped features, or surgical fixes.
	if re.search(r"\b(forms?|checkout|sign[\s-]?up|login|auth)\b", intent_blob):
		landingish = re.search(r"\b(landing|greenfield|hero|brand)\b", intent_blob)
		featureish = scope in {"feature_incremental", "feature"} or _additive_feature_intent(
			intent_blob
		)
		fixish = _surgical_intent_cues(intent_blob, scope=scope, resource=resource)
		if not (landingish or featureish or fixish):
			return "forms"
	# Surgical/hotfix cues beat stamped feature_incremental (lifecycle often mid/feature).
	if _surgical_intent_cues(intent_blob, scope=scope, resource=resource):
		return "hotfix"
	# Feature scope / intent language before polish-tier defaults and before debug→hotfix.
	feature_from_intent = _additive_feature_intent(intent_blob)
	# Explicit structural / greenfield intent language beats lifecycle feature stamps.
	if not feature_from_intent and (
		_greenfield_intent_cues(intent_blob)
		or re.search(r"\b(structural|coordination review)\b", intent_blob)
	):
		return "greenfield"
	if (
		scope in {"feature_incremental", "feature"}
		or feature_from_intent
		or (
			re.search(r"\bfeature\b", resource)
			and "hotfix" not in intent_blob
			and "polish" not in intent_blob
		)
	):
		return "feature"
	if scope in {"debug"}:
		return "hotfix"
	if tier in {"polish", "touch_up"} and scope in {"design_driven", "system_setup", ""}:
		return "hotfix"
	if scope in {"design_driven", "system_setup"} or "design-workflow" in resource:
		return "greenfield"
	# Landing / new page cues before defaulting to influence
	if re.search(r"\b(landing|greenfield|new (saas |product )?page|hero)\b", intent_blob):
		return "greenfield"
	influence = str(strategy.get("influence_level") or "").lower()
	if influence in {"structural", "balanced"}:
		return "greenfield"
	return "hotfix"


_CAPABILITY_FAMILY: dict[str, str] = {
	"inspiration_workflow": "inspiration",
	"design_snapshot": "snapshot",
	"visual_feedback": "visual_feedback",
	"component_intelligence": "component",
	"component_select": "component",
	"component_search_plan": "component",
	"resource_workflow": "resources",
	"observe": "observe",
	"browser_observe": "observe",
	"verify": "verify",
	"browser_verify": "verify",
	"design_review": "design_review",
}


def _owed_from_portfolio(
	strategy: dict[str, Any],
	*,
	face_class: str,
	limit: int = 3,
	pack_remaining: list[str] | None = None,
) -> list[dict[str, Any]]:
	portfolio = strategy.get("episode_portfolio") or {}
	paid = {
		str(p.get("family"))
		for p in (portfolio.get("paid") or [])
		if isinstance(p, dict) and p.get("family")
	}
	# Drop stale unpaid rows that are already paid (H21: forms paid + forms unpaid stub).
	unpaid = [
		row
		for row in (portfolio.get("unpaid") or [])
		if isinstance(row, dict) and str(row.get("family") or "") not in paid
	]
	exclude = _CLASS_OWED_EXCLUDE.get(face_class) or frozenset()
	# Never hide structural unpaid families when policy/gate say design ladder
	# (Run 6c J: hotfix exclude dropped component while gate wanted it).
	# Only lift excludes for greenfield/redesign faces — feature/hotfix/forms must
	# keep inspiration/gallery out of owed (live kit G04).
	if face_class in {"greenfield", "redesign"} and _structural_design_pressure(strategy):
		exclude = exclude - {
			"inspiration",
			"inspiration_extract",
			"snapshot",
			"component",
		}
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
	# Evidence Pack Loop: inject pack remaining families missing from portfolio unpaid.
	# After verify passed, never re-inject — claim_extra / done ladder owns next.
	portfolio_unpaid_families = {str(u.get("family") or "") for u in unpaid}
	pack_remaining = [str(f) for f in (pack_remaining or []) if f]
	if pack_remaining and str(strategy.get("verification_status") or "").lower() != "passed":
		present = set(portfolio_unpaid_families)
		paid = {
			str(p.get("family"))
			for p in (portfolio.get("paid") or [])
			if isinstance(p, dict) and p.get("family")
		}
		injected: list[dict[str, Any]] = []
		for fam in pack_remaining:
			if fam in present or fam in paid:
				continue
			if fam in exclude:
				continue
			injected.append(
				{
					"family": fam,
					"reason": f"evidence pack remaining ({face_class})",
					"suggested": _FAMILY_TOOL.get(fam, ""),
				}
			)
			present.add(fam)
		if injected:
			unpaid = [*injected, *unpaid]

	priority = _CLASS_OWED_PRIORITY.get(face_class) or ()
	rank = {fam: i for i, fam in enumerate(priority)}
	# Pack order outranks class default priority (integrated loop) — pre-verify only.
	if str(strategy.get("verification_status") or "").lower() != "passed":
		for i, fam in enumerate(pack_remaining):
			rank[fam] = i
	# Gate-required family outranks only when EQG/portfolio already marks it unpaid
	# (do not let pack-injected component leapfrog unpaid inspiration).
	gate = strategy.get("implementation_gate") if isinstance(strategy.get("implementation_gate"), dict) else {}
	gate_fam = _CAPABILITY_FAMILY.get(str(gate.get("next_required_capability") or "").lower())
	if gate_fam and gate_fam in portfolio_unpaid_families:
		insp_still_unpaid = bool(
			portfolio_unpaid_families & {"inspiration", "inspiration_extract"}
		)
		# H11: on greenfield/redesign, unpaid inspiration still beats component gate.
		if not (
			face_class in {"greenfield", "redesign"}
			and gate_fam == "component"
			and insp_still_unpaid
		):
			rank[gate_fam] = -1

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
		# Prefer the resolving tool for the gate family when present.
		if family == gate_fam and gate_fam == "component":
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
		elif tool == "perception_creative_assets":
			base["query"] = intent[:120]
			base.setdefault(
				"categories",
				["font", "pattern", "gradient", "icon", "illustration", "animation"],
			)
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


def _claim_ok(
	strategy: dict[str, Any],
	gate: dict[str, Any],
	owed: list[dict[str, Any]],
	*,
	pack: dict[str, Any] | None = None,
	face_class: str | None = None,
) -> bool:
	"""Claim-done only when gate allows AND verify is paid AND claim_extra cleared.

	Evidence Pack Loop: also false while pack.critical unpaid (esp. greenfield/redesign).
	Live kit D01: after hard verify + empty claim_extra, stale claim_complete in
	prohibited_actions is gate lag — do not keep claim_ok false forever.
	"""
	status = str(strategy.get("verification_status") or "").lower()
	extra = _claim_extra(strategy, gate)
	prohibited = list(gate.get("prohibited_actions") or [])
	if "claim_complete" in prohibited:
		# Verified + no ceremony left → allow claim despite lagging claim_complete flag.
		if not (status == "passed" and not extra):
			return False
	# G2: ship/sections/spec still listed → never claimable.
	if extra:
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
	# Digested inspiration is claim-critical once a pack was collected.
	if "inspiration_extract" in unpaid:
		return False
	# Copy/intel sticky: resources + consistency + fidelity stay claim-blocking
	# even after verify (agents must USE them, not skip after ceremony).
	from navigation.coordination_intelligence.planning.evidence_pack import (
		CLAIM_STICKY_AFTER_VERIFY,
	)

	sticky_hit = unpaid & CLAIM_STICKY_AFTER_VERIFY
	if sticky_hit and str(face_class or "") in {"greenfield", "redesign"}:
		return False
	# Pack critical unpaid blocks claim (greenfield/redesign heavy+ and class criticals).
	# After hard verify passed, claim_extra owns the finish ladder — do not re-block on
	# unpaid pre-verify pack families (VF still listed as remaining).
	# Exception: CLAIM_STICKY_AFTER_VERIFY stays blocking.
	if pack and pack.get("critical_unpaid"):
		if status != "passed":
			from navigation.coordination_intelligence.planning.evidence_pack import (
				pack_blocks_claim,
			)

			if pack_blocks_claim(pack, face_class=str(face_class or "")):
				return False
		else:
			sticky_pack = [
				f
				for f in (pack.get("critical_unpaid") or [])
				if f in CLAIM_STICKY_AFTER_VERIFY
			]
			if sticky_pack:
				return False
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
		# Creative assets + consistency + chrome fidelity (design heavy enforcement).
		if face_class in {"greenfield", "redesign"}:
			if "resources" in owed_families or "resources" in paid or depth == "full":
				finish.append(_fam_status("resources", tool="perception_creative_assets"))
			if "consistency" in owed_families or "consistency" in paid or depth == "full":
				finish.append(
					_fam_status("consistency", tool="perception_consistency_audit")
				)
			if "fidelity" in owed_families or "fidelity" in paid or depth == "full":
				finish.append(
					_finish_item(
						"fidelity",
						status="done" if "fidelity" in paid else "todo",
						tool="perception_visual_feedback",
						note="chrome_fidelity zones nav|aside|main|composer ≥80% mean copy",
					)
				)
		finish.append(
			_finish_item("verify", status="done" if verified else "todo", tool="perception_verify")
		)

	# Ceremony items are todo only when the gate requires them (claim_extra).
	# Full depth alone must not leave section_checklist=todo forever when
	# section_checklist_required=false (Run 6 host loop trap).
	if "section_checklist" in claim_extra:
		sec_done = "sections" in paid and "section_checklist" not in claim_extra
		finish.append(
			_finish_item(
				"section_checklist",
				status="done" if sec_done else "todo",
				tool="perception_observe",
				note="observe→verify each section when required",
			)
		)
	else:
		finish.append(
			_finish_item(
				"section_checklist",
				status="skip",
				note="not required by gate",
			)
		)

	if "ship_council" in claim_extra:
		ship_done = "design_review" in paid and "ship_council" not in claim_extra
		finish.append(
			_finish_item(
				"ship_council",
				status="done" if ship_done else "todo",
				tool="perception_design_review",
				note="mode=ship",
			)
		)
	else:
		finish.append(
			_finish_item(
				"ship_council",
				status="skip",
				note="not required by gate",
			)
		)

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
	return finish


def _build_orders(
	*,
	face_class: str,
	owed: list[dict[str, Any]],
	implement_blocked: bool,
) -> list[str]:
	"""Short imperatives on the face — motivate when hosts ignore soft prose."""
	if face_class not in {"greenfield", "redesign", "mockup"}:
		return []
	owed_fams = {
		str(o.get("family") or "").strip()
		for o in owed
		if isinstance(o, dict)
	}
	orders: list[str] = []
	if "inspiration" in owed_fams or "inspiration_extract" in owed_fams:
		orders.append(
			"LOOK many inspiration blobs → LEARN chrome → COPY ~80–90% "
			"(nav/aside/main/composer); soft vibe-borrow is invalid"
		)
	if "component" in owed_fams:
		orders.append("USE component foundation (select → integrate); do not invent chrome alone")
	if "resources" in owed_fams:
		orders.append("APPLY creative_assets (fonts/patterns/motion) into the UI — search≠apply")
	if "consistency" in owed_fams:
		orders.append(
			"After copy: reconcile to THIS product via design_graph + consistency_audit"
		)
	if "fidelity" in owed_fams:
		orders.append(
			"Attest chrome_fidelity zones mean≥80 / each≥75 vs primary_ref_ids before claim"
		)
	if implement_blocked and not orders:
		orders.append("Pay owed evidence before implement — MCP refuses mutation tools while blocked")
	elif implement_blocked:
		orders.insert(0, "implement_blocked: gather evidence only until owed critical is paid")
	return orders[:6]


def _reconcile_face_class(face_class: str, strategy: dict[str, Any]) -> str:
	"""Last-line correction: policy/unpaid design ladder beats a misclassified hotfix face.

	Run 6c proved classify alone can still emit hotfix under design.greenfield.* when
	intent cues are polluted; card-only hosts need the face itself corrected.

	Live kit A02/G04: design.greenfield policy must NOT demote redesign/feature intents.
	"""
	policy = str(strategy.get("policy_id") or "").lower()
	intent = str(strategy.get("intent") or "").lower()
	resource = str(strategy.get("recommended_resource") or "").lower()
	scope = str(strategy.get("task_scope") or "").lower()
	explicit_surgical = bool(
		re.search(
			r"\b("
			r"hotfix|bugfix|css bug|layout bug|overlapping|broken"
			r"|fix\s+(the\s+)?(broken|overlapping|css|button|bug)"
			r"|tighten\s+spacing|spacing\s+only|navbar\s+only|chrome\s+only"
			r"|visual\s+polish|touch[\s-]?up"
			r")\b",
			intent,
		)
	) and not _design_fix_intent_cues(intent)
	# Vague design-fix ("fix the footer/look/design") → redesign spine.
	if _design_fix_intent_cues(intent) and not _defect_fix_intent_cues(intent):
		return "redesign"
	# Intent-led redesign wins over greenfield policy stamps.
	if face_class == "redesign" or (
		_redesign_intent_cues(intent) and not explicit_surgical
	):
		return "redesign"
	# Keep classified feature (do not let greenfield policy demote it).
	if face_class == "feature":
		return "feature"
	# Upgrade greenfield→feature when additive intent is clear and not surgical.
	# Do not upgrade hotfix when "add a feature to fix X" (fix is the job).
	if (
		face_class == "greenfield"
		and _additive_feature_intent(intent)
		and not explicit_surgical
		and not _surgical_intent_cues(intent, scope=scope, resource=resource)
	):
		return "feature"
	if policy.startswith("design.greenfield") and not explicit_surgical:
		return "greenfield"
	if policy.startswith("design.redesign") and not explicit_surgical:
		return "redesign"
	if (
		face_class == "hotfix"
		and _structural_design_pressure(strategy)
		and not explicit_surgical
	):
		return "greenfield"
	return face_class


def build_agent_face_card(
	*,
	episode_id: str,
	strategy: dict[str, Any] | None,
	suggested_capability: str | None = None,
) -> dict[str, Any]:
	"""Single agent-facing card — next / owed / gate / claim_extra / resource.

	Internals stay rich; this is the only field agents should need each turn.
	Evidence Pack Loop: evidence_band + pack + implement_blocked drive owed/claim.
	"""
	from navigation.coordination_intelligence.planning.evidence_pack import (
		build_evidence_pack,
		pack_implement_blocked,
		resolve_evidence_band,
	)

	strategy = strategy or {}
	gate = dict(strategy.get("implementation_gate") or {})
	face_class = _reconcile_face_class(classify_agent_face(strategy), strategy)
	# Enrich strategy with face_class for band floors (greenfield → very_heavy).
	band_strategy = dict(strategy)
	if face_class == "greenfield" and not band_strategy.get("task_scope"):
		band_strategy["task_scope"] = "design_driven"
	elif face_class == "redesign" and not band_strategy.get("task_scope"):
		band_strategy["task_scope"] = "redesign"
	elif face_class == "hotfix" and not band_strategy.get("task_scope"):
		band_strategy["task_scope"] = "hotfix"
	elif face_class == "forms" and not band_strategy.get("task_scope"):
		band_strategy["task_scope"] = "hotfix"  # light band floor
	evidence_band = resolve_evidence_band(band_strategy)
	# Face-class floors (declared agent tier wins).
	rs = strategy.get("right_sizing") if isinstance(strategy.get("right_sizing"), dict) else {}
	if not rs.get("declared"):
		if face_class in {"hotfix", "forms"}:
			evidence_band = "light"
		elif face_class == "feature":
			# Additive feature: heavy. Do not inherit very_heavy from greenfield policy stamps,
			# and do not keep light from stale debug/hotfix task_scope.
			if evidence_band != "medium":
				evidence_band = "heavy"
		elif face_class in {"greenfield", "redesign"} and evidence_band in {
			"light",
			"medium",
			"heavy",
		}:
			evidence_band = "very_heavy"
	pack = build_evidence_pack(
		face_class=face_class,
		strategy=band_strategy,
		band=evidence_band,
	)
	owed = _owed_from_portfolio(
		strategy,
		face_class=face_class,
		limit=3,
		pack_remaining=list(pack.get("remaining") or []),
	)

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
	# Inject warm discover_token into inspiration next_args when prefetch ready.
	if next_tool and "inspiration" in next_tool:
		try:
			from navigation.coordination_intelligence.planning.episode_prefetch import (
				peek_inspiration_prefetch,
			)

			warm = peek_inspiration_prefetch(
				episode_id=episode_id,
				query=str(next_args.get("query") or ""),
			)
			if warm and warm.get("discover_token") and not next_args.get("discover_token"):
				next_args["discover_token"] = warm["discover_token"]
		except Exception:
			pass
	claim_extra = _claim_extra(strategy, gate)
	# Ship council args when that's the next
	if next_tool == "perception_design_review" and "ship_council" in claim_extra:
		next_args["mode"] = "ship"

	claim_ok = _claim_ok(
		strategy,
		gate,
		owed,
		pack=pack,
		face_class=face_class,
	)
	implement_blocked = pack_implement_blocked(face_class=face_class, pack=pack)
	if str(strategy.get("verification_status") or "").lower() == "passed":
		implement_blocked = False
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
	conflict = _face_conflict(
		face_class=face_class,
		strategy=strategy,
		gate=gate,
		owed=owed,
		next_tool=next_tool,
	)

	card: dict[str, Any] = {
		"schema": AGENT_FACE_SCHEMA,
		"episode_id": episode_id,
		"class": face_class,
		"depth": depth,
		"evidence_band": evidence_band,
		"pack": {
			"id": pack.get("id"),
			"phases": list(pack.get("phases") or []),
			"critical": list(pack.get("critical") or []),
			"remaining": list(pack.get("remaining") or []),
		},
		"implement_blocked": implement_blocked,
		"next": next_tool,
		"next_args": next_args,
		"owed": owed,
		"gate": str(gate.get("state") or "unknown"),
		"claim_ok": claim_ok,
		"claim_extra": claim_extra,
		"finish": finish,
		# `resource` = methodology spine URI (not Resource Intelligence).
		"resource": resource,
		"spine": resource,
		"host_action": strategy.get("host_action"),
	}
	# Episode HTTP prefetch (inspiration/component/creative_kit) — never browser.
	try:
		from navigation.coordination_intelligence.planning.episode_prefetch import (
			get_prefetch_snapshot,
			peek_creative_kit,
		)

		prefetch = get_prefetch_snapshot(episode_id)
		if prefetch:
			card["prefetch"] = prefetch
			card["can_parallel"] = list(prefetch.get("can_parallel") or [])
		kit = peek_creative_kit(episode_id=episode_id)
		if kit:
			card["creative_kit"] = {
				"ready": True,
				"asset_count": kit.get("asset_count"),
				"categories": list(kit.get("categories") or []),
				"tool": "perception_creative_assets",
				"suggested_calls": list(kit.get("suggested_calls") or [])[:4],
			}
		elif face_class in {"greenfield", "redesign"} and evidence_band in {
			"heavy",
			"very_heavy",
		}:
			# Nudge even before prefetch finishes — core atmosphere assets.
			card["creative_kit"] = {
				"ready": False,
				"tool": "perception_creative_assets",
				"categories": ["font", "pattern", "gradient", "icon", "illustration", "animation"],
				"note": (
					"Use perception_creative_assets for fonts, bg patterns, gradients/palettes, "
					"graphics, and motion — do not invent flat chrome only."
				),
			}
	except Exception:
		pass
	# Continuous HTTP inspiration pulse (parallel thumbs) — never browser.
	try:
		from navigation.coordination_intelligence.planning.inspiration_pulse_loop import (
			get_pulse_snapshot,
		)

		pulse = get_pulse_snapshot(episode_id)
		if pulse:
			card["inspiration_pulse"] = pulse
			card["can_parallel"] = list(
				dict.fromkeys(list(card.get("can_parallel") or []) + ["inspiration"])
			)
	except Exception:
		pass
	# Parallel HTTP intel batch — fire concurrently (never primary browser).
	try:
		from navigation.coordination_intelligence.planning.evidence_pack import (
			PARALLEL_INTEL_FAMILIES,
		)

		owed_fams = {
			str(r.get("family"))
			for r in owed
			if isinstance(r, dict) and r.get("family")
		}
		remaining = set(pack.get("remaining") or []) if isinstance(pack, dict) else set()
		portfolio_unpaid = {
			str(u.get("family"))
			for u in ((strategy.get("episode_portfolio") or {}).get("unpaid") or [])
			if isinstance(u, dict) and u.get("family")
		}
		parallel_now = sorted(
			(owed_fams | remaining | portfolio_unpaid) & PARALLEL_INTEL_FAMILIES
		)
		# Always surface known-safe parallel families on design heavy+.
		if face_class in {"greenfield", "redesign"} and evidence_band in {
			"heavy",
			"very_heavy",
		}:
			parallel_now = list(
				dict.fromkeys(
					parallel_now
					+ [
						f
						for f in ("inspiration", "component", "resources", "consistency")
						if f in PARALLEL_INTEL_FAMILIES
					]
				)
			)
		if parallel_now:
			card["can_parallel"] = list(
				dict.fromkeys(list(card.get("can_parallel") or []) + parallel_now)
			)
			card["parallel_batch"] = {
				"families": parallel_now,
				"note": (
					"HTTP intel — call concurrently (no browser lock): "
					"creative_assets ∥ select_component_foundation ∥ inspiration_pulse ∥ "
					"design_graph_refresh/consistency_audit. Browser tools stay serial."
				),
			}
	except Exception:
		pass
	if conflict:
		card["conflict"] = conflict
	# Narrow decision state — creation pipeline phase (not 150-state leaves).
	try:
		from navigation.coordination_intelligence.planning.episode_phase import (
			resolve_episode_phase,
		)

		phase_info = resolve_episode_phase(
			face_class=face_class,
			strategy=strategy,
			owed=owed,
			pack=pack,
			claim_extra=claim_extra,
			claim_ok=claim_ok,
		)
		card["phase"] = phase_info.get("phase")
		card["phase_hint"] = phase_info.get("hint")
	except Exception:
		pass
	orders = _build_orders(
		face_class=face_class,
		owed=owed,
		implement_blocked=implement_blocked,
	)
	if orders:
		card["orders"] = orders
	return card


def _face_conflict(
	*,
	face_class: str,
	strategy: dict[str, Any],
	gate: dict[str, Any],
	owed: list[dict[str, Any]],
	next_tool: str,
) -> dict[str, Any] | None:
	"""Flag when card class/owed still disagree with structural unpaid or gate."""
	unpaid = _unpaid_families(strategy)
	structural = unpaid & {"inspiration", "inspiration_extract", "snapshot", "component"}
	owed_fams = {str(o.get("family")) for o in owed}
	policy = str(strategy.get("policy_id") or "")
	next_cap = str(gate.get("next_required_capability") or "")
	reasons: list[str] = []
	if face_class in {"hotfix", "feature"} and structural and _structural_design_pressure(strategy):
		# Explicit surgical intents may still exclude inspiration from owed — warn.
		missing = sorted(structural - owed_fams)
		if missing:
			reasons.append(
				f"class={face_class} omits unpaid structural families: {', '.join(missing)}"
			)
	if policy.startswith("design.greenfield") and face_class == "hotfix":
		reasons.append(f"policy={policy} disagrees with class=hotfix")
	cap_tool = _CAPABILITY_TOOL.get(next_cap)
	if (
		cap_tool
		and next_tool
		and next_tool != cap_tool
		and face_class in {"greenfield", "redesign"}
		and next_cap in {"inspiration_workflow", "design_snapshot", "component_select", "component_search_plan"}
	):
		reasons.append(f"next={next_tool} lags gate capability={next_cap}")
	# Forms/hotfix: face card is the routing contract — gate may still echo structural leftovers.
	if face_class in {"forms", "hotfix"} and next_cap in {
		"inspiration_workflow",
		"design_snapshot",
		"component_select",
		"component_search_plan",
	}:
		reasons.append(
			f"class={face_class} should ignore structural gate capability={next_cap}"
		)
	if not reasons:
		return None
	prefer = "face.card" if face_class in {"forms", "hotfix"} else "gate+unpaid"
	note = (
		"Prefer agent_summary.card class/phase/owed/next over implementation_gate for forms/hotfix."
		if prefer == "face.card"
		else "Follow implementation_gate.next_required_capability and episode_portfolio.unpaid when set."
	)
	return {
		"reasons": reasons,
		"prefer": prefer,
		"note": note,
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
