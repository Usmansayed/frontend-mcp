"""Inspiration LOOK lock — collect alone is not direction.

Deterministic gates (no LLM / OCR in MCP). Host must LOOK at attached blobs and
file structured borrow + primary_ref_ids before direction_locked clears.
"""
from __future__ import annotations

from typing import Any

# Floor of distinct refs that must be named after a successful collect.
_MIN_PRIMARY_HEAVY = 3
_MIN_PRIMARY_VERY_HEAVY = 5
_MIN_BORROW_ITEMS = 3


def min_primary_refs(
	*,
	usable_image_refs: int | None = None,
	evidence_band: str | None = None,
) -> int:
	"""How many primary_ref_ids are required for a valid look-lock."""
	usable = int(usable_image_refs or 0)
	band = str(evidence_band or "heavy").strip().lower()
	target = _MIN_PRIMARY_VERY_HEAVY if band == "very_heavy" else _MIN_PRIMARY_HEAVY
	# Wide hunts (many blobs) raise the floor even if band stamp is missing.
	if usable >= 10 and band not in {"light", "medium"}:
		target = max(target, _MIN_PRIMARY_VERY_HEAVY)
	if usable <= 0:
		return target
	return max(1, min(usable, target))


def _as_str_list(raw: Any) -> list[str]:
	if isinstance(raw, str) and raw.strip():
		return [raw.strip()]
	if not isinstance(raw, list):
		return []
	out: list[str] = []
	for item in raw:
		if isinstance(item, str) and item.strip():
			out.append(item.strip())
		elif isinstance(item, dict):
			rid = str(
				item.get("ref_id")
				or item.get("candidate_id")
				or item.get("id")
				or ""
			).strip()
			idea = str(
				item.get("idea")
				or item.get("section")
				or item.get("borrow")
				or item.get("note")
				or ""
			).strip()
			if rid and idea:
				out.append(f"{rid}:{idea}")
			elif rid:
				out.append(rid)
			elif idea:
				out.append(idea)
	return out


def _primary_ref_ids(feedback: dict[str, Any]) -> list[str]:
	raw = feedback.get("primary_ref_ids") or feedback.get("looked_ref_ids") or []
	if isinstance(raw, str) and raw.strip():
		return [p.strip() for p in raw.split(",") if p.strip()]
	if not isinstance(raw, list):
		return []
	out: list[str] = []
	for item in raw:
		if isinstance(item, str) and item.strip():
			out.append(item.strip())
		elif isinstance(item, dict):
			rid = str(
				item.get("ref_id")
				or item.get("candidate_id")
				or item.get("id")
				or ""
			).strip()
			if rid:
				out.append(rid)
	# Dedupe preserve order
	seen: set[str] = set()
	deduped: list[str] = []
	for rid in out:
		if rid in seen:
			continue
		seen.add(rid)
		deduped.append(rid)
	return deduped


def _borrow_items(feedback: dict[str, Any]) -> list[Any]:
	raw = feedback.get("borrow")
	if isinstance(raw, str) and raw.strip():
		return [raw.strip()]
	if isinstance(raw, list):
		return [x for x in raw if x not in (None, "", [])]
	return []


def _borrow_covers_refs(borrow: list[Any], primary: list[str]) -> int:
	"""Count how many primary refs are named in borrow items."""
	if not primary:
		return 0
	blob = " ".join(
		str(
			(b.get("ref_id") if isinstance(b, dict) else b)
			or (b.get("candidate_id") if isinstance(b, dict) else "")
			or (b.get("idea") if isinstance(b, dict) else "")
			or ""
		)
		for b in borrow
	).lower()
	hit = 0
	for rid in primary:
		token = str(rid).strip().lower()
		if token and token in blob:
			hit += 1
	return hit


def evaluate_inspiration_look_lock(
	feedback: dict[str, Any] | None,
	*,
	usable_image_refs: int | None = None,
	evidence_band: str | None = None,
) -> dict[str, Any]:
	"""Return look_locked + reasons. Soft mood-only borrow is NOT enough."""
	fb = feedback if isinstance(feedback, dict) else {}
	primary = _primary_ref_ids(fb)
	borrow = _borrow_items(fb)
	min_primary = min_primary_refs(
		usable_image_refs=usable_image_refs,
		evidence_band=evidence_band,
	)
	min_borrow = max(_MIN_BORROW_ITEMS, min_primary)
	# Soft look_lock dict alone no longer clears — must accompany primary refs.
	look_lock = fb.get("look_lock")
	has_look_lock_shape = (
		(isinstance(look_lock, dict) and any(bool(v) for v in look_lock.values()))
		or (isinstance(look_lock, str) and bool(look_lock.strip()))
	)
	covered = _borrow_covers_refs(borrow, primary)
	reasons: list[str] = []
	if len(primary) < min_primary:
		reasons.append(
			f"primary_ref_ids need ≥{min_primary} distinct looked refs "
			f"(got {len(primary)}); LOOK more inspiration blobs"
		)
	if len(borrow) < min_borrow:
		reasons.append(
			f"borrow need ≥{min_borrow} concrete section/ideas "
			f"(got {len(borrow)}); name what to copy with tweaks per ref"
		)
	need_cover = max(1, (min_primary + 1) // 2)
	if primary and covered < need_cover:
		reasons.append(
			f"borrow must name ≥{need_cover} of primary_ref_ids "
			f"(covered {covered}); bind ideas to ref ids"
		)
	if not has_look_lock_shape and not borrow:
		reasons.append("look_lock or borrow required after LOOK")

	look_locked = not reasons
	return {
		"look_locked": look_locked,
		"primary_ref_ids": primary,
		"primary_ref_count": len(primary),
		"min_primary_refs": min_primary,
		"borrow_count": len(borrow),
		"min_borrow_items": min_borrow,
		"borrow_covers_primary": covered,
		"reasons": reasons,
		"hint": (
			"LOOK attached inspiration blobs → fill primary_ref_ids (≥ floor) + "
			"borrow[{ref_id, section?, idea}] for each liked section to copy with tweaks."
			if not look_locked
			else "direction locked from multi-ref LOOK"
		),
	}
