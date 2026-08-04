"""Evidence Pack Loop — class × band packs with server-owned subtraction.

Agents follow one integrated loop (ORIENT → LOOK → STRUCTURE → CHECK → HARDEN).
The server starts from a full class pack for the evidence band, then subtracts
families the query clearly does not need. Face card exposes pack + critical.
"""
from __future__ import annotations

from typing import Any

from navigation.coordination_intelligence.planning.right_sizing import (
	EVIDENCE_BANDS,
	normalize_effort_tier,
	tier_to_evidence_band,
)

# Ordered family ids per class × band. Optional families end with "?".
# Critical families (claim/implement gates) omit trailing "?".
_PACK_PHASES: dict[str, dict[str, tuple[str, ...]]] = {
	"greenfield": {
		"light": ("observe", "verify"),
		"medium": ("observe", "visual_feedback", "verify"),
		"heavy": (
			"inspiration",
			"inspiration_extract",
			"component",
			"resources",
			"visual_feedback",
			"fidelity",
			"consistency",
			"observe",
			"verify",
		),
		"very_heavy": (
			"inspiration",
			"inspiration_extract",
			"component",
			"resources",
			"visual_feedback",
			"fidelity",
			"consistency",
			"observe",
			"verify",
			"sections",
			"design_review",
		),
	},
	"redesign": {
		"light": ("observe", "verify"),
		"medium": ("observe", "snapshot", "visual_feedback", "verify"),
		"heavy": (
			"observe",
			"snapshot",
			"inspiration_extract",
			"component",
			"resources",
			"visual_feedback",
			"fidelity",
			"consistency",
			"verify",
		),
		"very_heavy": (
			"observe",
			"snapshot",
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
	},
	"feature": {
		"light": ("observe", "verify"),
		"medium": ("observe", "visual_feedback", "verify"),
		"heavy": ("observe", "component?", "visual_feedback", "verify"),
		"very_heavy": (
			"observe",
			"component?",
			"visual_feedback",
			"verify",
			"design_review",
		),
	},
	"hotfix": {
		"light": ("observe", "verify"),
		"medium": ("observe", "verify"),
		"heavy": ("observe", "verify"),
		"very_heavy": ("observe", "verify"),
	},
	"forms": {
		"light": ("forms", "verify"),
		"medium": ("forms", "verify"),
		"heavy": ("forms", "verify"),
		"very_heavy": ("forms", "verify"),
	},
}

# Families that block implement / claim for greenfield & redesign at heavy+.
_CRITICAL_BY_CLASS: dict[str, frozenset[str]] = {
	"greenfield": frozenset(
		{
			"inspiration",
			"inspiration_extract",
			"component",
			"resources",
			"visual_feedback",
			"fidelity",
			"consistency",
			"verify",
		}
	),
	"redesign": frozenset(
		{
			"observe",
			"snapshot",
			"component",
			"resources",
			"visual_feedback",
			"fidelity",
			"consistency",
			"verify",
		}
	),
	"feature": frozenset({"observe", "verify"}),
	"hotfix": frozenset({"verify"}),
	"forms": frozenset({"forms", "verify"}),
}

_NO_INSPIRATION_CLASSES = frozenset({"hotfix", "forms", "feature"})
_NO_SNAPSHOT_UNLESS_REDESIGN = frozenset({"greenfield", "feature", "hotfix", "forms"})
# HTTP-parallel intel families (never need primary browser lock).
PARALLEL_INTEL_FAMILIES: frozenset[str] = frozenset(
	{
		"inspiration",
		"inspiration_extract",
		"component",
		"resources",
		"consistency",
	}
)

# Still block claim_ok after verify while these remain unpaid (copy/intel enforcement).
CLAIM_STICKY_AFTER_VERIFY: frozenset[str] = frozenset(
	{
		"inspiration_extract",
		"resources",
		"consistency",
		"fidelity",
	}
)


def _strip_optional(family: str) -> tuple[str, bool]:
	if family.endswith("?"):
		return family[:-1], True
	return family, False


def normalize_evidence_band(raw: Any) -> str:
	"""Normalize band or tier string to an evidence band."""
	if raw is None or str(raw).strip() == "":
		return "heavy"
	text = str(raw).strip().lower().replace("-", "_").replace(" ", "_")
	if text in EVIDENCE_BANDS:
		return text
	tier = normalize_effort_tier(text)
	if tier:
		return tier_to_evidence_band(tier)
	return "heavy"


def resolve_evidence_band(strategy: dict[str, Any] | None = None) -> str:
	"""Band from strategy right_sizing / effort_tier / face defaults."""
	strategy = strategy or {}
	rs = strategy.get("right_sizing") if isinstance(strategy.get("right_sizing"), dict) else {}
	raw = (
		rs.get("evidence_band")
		or strategy.get("evidence_band")
		or rs.get("tier")
		or strategy.get("effort_tier")
	)
	# Class floors: design initiative → very_heavy unless agent declared lighter surgical
	face_hint = str(strategy.get("task_scope") or "").lower()
	policy = str(strategy.get("policy_id") or "").lower()
	band = normalize_evidence_band(raw) if raw else None
	if band is None:
		if (
			face_hint in {"design_driven", "redesign", "system_setup"}
			or policy.startswith("design.greenfield")
			or policy.startswith("design.redesign")
		):
			return "very_heavy"
		if face_hint in {"hotfix", "surgical", "debug"}:
			return "light"
		return "heavy"
	# Never demote sticky design below very_heavy unless explicit light/medium surgical
	if (
		(
			face_hint in {"design_driven", "redesign", "system_setup"}
			or policy.startswith("design.greenfield")
			or policy.startswith("design.redesign")
		)
		and band in {"heavy", "medium"}
		and not bool(rs.get("declared"))
	):
		return "very_heavy"
	return band


def _base_phases(face_class: str, band: str) -> list[str]:
	cls = face_class if face_class in _PACK_PHASES else "feature"
	b = band if band in EVIDENCE_BANDS else "heavy"
	table = _PACK_PHASES[cls]
	phases = table.get(b) or table.get("heavy") or ("observe", "verify")
	return list(phases)


def _subtract_phases(
	phases: list[str],
	*,
	face_class: str,
	band: str,
	strategy: dict[str, Any],
) -> list[str]:
	"""Server-owned subtraction — never leave skips to the agent.

	Returns list of family ids (optional marker stripped). Optional families that
	are not already unpaid in the portfolio are kept in the descriptive pack
	via a parallel path in build_evidence_pack — here we only emit required +
	already-unpaid optional families for remaining/owed drive.
	"""
	out: list[str] = []
	portfolio = strategy.get("episode_portfolio") or {}
	paid = {
		str(p.get("family"))
		for p in (portfolio.get("paid") or [])
		if isinstance(p, dict) and p.get("family")
	}
	unpaid = {
		str(u.get("family"))
		for u in (portfolio.get("unpaid") or [])
		if isinstance(u, dict) and u.get("family")
	}
	gate = (
		strategy.get("implementation_gate")
		if isinstance(strategy.get("implementation_gate"), dict)
		else {}
	)
	ceremony_armed = bool(
		gate.get("section_checklist_required")
		or gate.get("ship_council_required")
		or gate.get("spec_revision_required")
		or (
			isinstance(strategy.get("spec_revision_gate"), dict)
			and strategy["spec_revision_gate"].get("revision_required")
		)
	)
	for raw in phases:
		fam, optional = _strip_optional(raw)
		# Band floors
		if band == "light" and fam in {
			"inspiration",
			"inspiration_extract",
			"snapshot",
			"component",
			"resources",
			"consistency",
			"fidelity",
			"sections",
			"design_review",
			"residue",
		}:
			continue
		if band in {"light", "medium"} and fam in {
			"sections",
			"design_review",
			"residue",
			"resources",
			"consistency",
			"fidelity",
		}:
			continue
		# Ceremony only when gate arms it (avoid forever-todo sections on heavy packs).
		if fam in {"sections", "design_review", "residue"} and not ceremony_armed:
			continue
		# Class floors
		if face_class in _NO_INSPIRATION_CLASSES and fam in {
			"inspiration",
			"inspiration_extract",
		}:
			continue
		if face_class in _NO_SNAPSHOT_UNLESS_REDESIGN and fam in {"snapshot", "residue"}:
			continue
		if fam == "component" and face_class == "hotfix":
			continue
		if fam in {"resources", "consistency", "fidelity"} and face_class in {
			"hotfix",
			"forms",
		}:
			continue
		if optional and fam in paid:
			continue
		# Optional: only drive owed when portfolio already marks unpaid
		if optional and fam not in unpaid:
			continue
		out.append(fam)
	# Dedupe preserving order
	seen: set[str] = set()
	deduped: list[str] = []
	for fam in out:
		if fam in seen:
			continue
		seen.add(fam)
		deduped.append(fam)
	return deduped


def _descriptive_phases(
	raw_phases: list[str],
	*,
	face_class: str,
	band: str,
	strategy: dict[str, Any],
) -> list[str]:
	"""Full pack phases for card display (includes optional not yet unpaid)."""
	out: list[str] = []
	paid = {
		str(p.get("family"))
		for p in ((strategy.get("episode_portfolio") or {}).get("paid") or [])
		if isinstance(p, dict) and p.get("family")
	}
	gate = (
		strategy.get("implementation_gate")
		if isinstance(strategy.get("implementation_gate"), dict)
		else {}
	)
	ceremony_armed = bool(
		gate.get("section_checklist_required")
		or gate.get("ship_council_required")
		or gate.get("spec_revision_required")
		or (
			isinstance(strategy.get("spec_revision_gate"), dict)
			and strategy["spec_revision_gate"].get("revision_required")
		)
	)
	for raw in raw_phases:
		fam, optional = _strip_optional(raw)
		if band == "light" and fam in {
			"inspiration",
			"inspiration_extract",
			"snapshot",
			"component",
			"resources",
			"consistency",
			"fidelity",
			"sections",
			"design_review",
			"residue",
		}:
			continue
		if band in {"light", "medium"} and fam in {
			"sections",
			"design_review",
			"residue",
			"resources",
			"consistency",
			"fidelity",
		}:
			continue
		if fam in {"sections", "design_review", "residue"} and not ceremony_armed:
			continue
		if face_class in _NO_INSPIRATION_CLASSES and fam in {
			"inspiration",
			"inspiration_extract",
		}:
			continue
		if face_class in _NO_SNAPSHOT_UNLESS_REDESIGN and fam in {"snapshot", "residue"}:
			continue
		if fam == "component" and face_class == "hotfix":
			continue
		if fam in {"resources", "consistency", "fidelity"} and face_class in {
			"hotfix",
			"forms",
		}:
			continue
		if optional and fam in paid:
			continue
		out.append(fam)
	seen: set[str] = set()
	deduped: list[str] = []
	for fam in out:
		if fam in seen:
			continue
		seen.add(fam)
		deduped.append(fam)
	return deduped


def _critical_families(face_class: str, band: str, phases: list[str]) -> list[str]:
	base = _CRITICAL_BY_CLASS.get(face_class) or frozenset({"verify"})
	# Only critical if still in the pack after subtraction
	phase_set = set(phases)
	critical = [f for f in phases if f in base and f in phase_set]
	# At light band, only verify (and forms) remain critical
	if band == "light":
		critical = [f for f in critical if f in {"verify", "forms", "observe"}]
	# Greenfield/redesign heavy+: keep structural criticals present in phases
	if face_class in {"greenfield", "redesign"} and band in {"heavy", "very_heavy"}:
		ordered = [f for f in phases if f in base]
		return ordered
	return critical


def build_evidence_pack(
	*,
	face_class: str,
	strategy: dict[str, Any] | None = None,
	band: str | None = None,
) -> dict[str, Any]:
	"""Build pack descriptor for agent_summary.card."""
	strategy = strategy or {}
	resolved_band = band or resolve_evidence_band(strategy)
	resolved_band = normalize_evidence_band(resolved_band)
	raw_phases = _base_phases(face_class, resolved_band)
	# Display phases include optional; drive phases omit unpaid-optional-not-in-portfolio.
	phases = _descriptive_phases(
		raw_phases,
		face_class=face_class,
		band=resolved_band,
		strategy=strategy,
	)
	drive = _subtract_phases(
		raw_phases,
		face_class=face_class,
		band=resolved_band,
		strategy=strategy,
	)
	portfolio = strategy.get("episode_portfolio") or {}
	paid = {
		str(p.get("family"))
		for p in (portfolio.get("paid") or [])
		if isinstance(p, dict) and p.get("family")
	}
	# Remaining unpaid phases (pack progress) — drive set only
	remaining = [f for f in drive if f not in paid]
	# Inject portfolio unpaid structural families not already in pack (design pressure)
	unpaid_rows = [
		str(u.get("family"))
		for u in (portfolio.get("unpaid") or [])
		if isinstance(u, dict) and u.get("family")
	]
	for fam in unpaid_rows:
		if fam in {
			"inspiration",
			"inspiration_extract",
			"snapshot",
			"component",
			"resources",
			"consistency",
			"fidelity",
			"visual_feedback",
			"observe",
			"forms",
		}:
			if fam not in phases and fam not in paid:
				# Only add if class allows
				if face_class in _NO_INSPIRATION_CLASSES and fam in {
					"inspiration",
					"inspiration_extract",
				}:
					continue
				if face_class == "hotfix" and fam in {
					"component",
					"snapshot",
					"inspiration",
					"resources",
					"consistency",
					"fidelity",
				}:
					continue
				if face_class == "forms" and fam in {
					"resources",
					"consistency",
					"fidelity",
					"component",
				}:
					continue
				phases.append(fam)
			if fam not in remaining and fam not in paid:
				if face_class in _NO_INSPIRATION_CLASSES and fam in {
					"inspiration",
					"inspiration_extract",
				}:
					continue
				if face_class == "hotfix" and fam in {
					"component",
					"snapshot",
					"inspiration",
					"resources",
					"consistency",
					"fidelity",
				}:
					continue
				if face_class == "forms" and fam in {
					"resources",
					"consistency",
					"fidelity",
					"component",
				}:
					continue
				remaining.append(fam)

	critical = _critical_families(face_class, resolved_band, phases)
	# Once inspiration is paid, digest (extract) is claim-critical too.
	if (
		"inspiration" in paid
		and "inspiration_extract" not in paid
		and face_class not in _NO_INSPIRATION_CLASSES
		and "inspiration_extract" in unpaid_rows
	):
		if "inspiration_extract" not in critical:
			critical = list(critical) + ["inspiration_extract"]
	# Copy/intel enforcement: sticky families unpaid → stay critical on design classes.
	if face_class in {"greenfield", "redesign"} and resolved_band in {
		"heavy",
		"very_heavy",
	}:
		for fam in CLAIM_STICKY_AFTER_VERIFY:
			if fam in unpaid_rows and fam not in paid and fam not in critical:
				critical = list(critical) + [fam]
	critical_unpaid = [f for f in critical if f not in paid]
	pack_id = f"{face_class}.{resolved_band}"
	return {
		"id": pack_id,
		"band": resolved_band,
		"phases": phases,
		"remaining": remaining,
		"critical": critical,
		"critical_unpaid": critical_unpaid,
	}


def pack_implement_blocked(
	*,
	face_class: str,
	pack: dict[str, Any],
) -> bool:
	"""True while greenfield/redesign heavy+ still has structural critical unpaid."""
	band = str(pack.get("band") or "")
	if face_class not in {"greenfield", "redesign"}:
		return False
	if band not in {"heavy", "very_heavy"}:
		return False
	critical_unpaid = list(pack.get("critical_unpaid") or [])
	# verify unpaid does not block *implement* — only pre-verify structural
	structural = [f for f in critical_unpaid if f != "verify"]
	return bool(structural)


def pack_blocks_claim(pack: dict[str, Any], *, face_class: str) -> bool:
	"""Claim blocked while pack critical unpaid (all classes for their critical set)."""
	unpaid = list(pack.get("critical_unpaid") or [])
	if not unpaid:
		return False
	# Hotfix/forms: only verify/forms block (already in critical)
	return True
