"""Chrome fidelity attestation — force 80–90% visual copy vs locked refs.

Deterministic (no LLM). Host must LOOK at inspiration + live chrome and file
per-zone fidelity scores. Soft "looks fine" without zones does not clear.
"""
from __future__ import annotations

from typing import Any

# Required chrome zones for greenfield/redesign chat/workspace/landing shells.
REQUIRED_ZONES: tuple[str, ...] = (
	"nav",
	"aside",
	"main",
	"composer",
)

_ZONE_ALIASES: dict[str, str] = {
	"header": "nav",
	"navbar": "nav",
	"topbar": "nav",
	"sidebar": "aside",
	"rail": "aside",
	"thread": "main",
	"content": "main",
	"chat": "main",
	"hero": "main",
	"footer": "composer",
	"input": "composer",
	"prompt": "composer",
}

_MIN_ZONE_FIDELITY = 75
_MIN_MEAN_FIDELITY = 80
_MIN_ZONES = 4


def _norm_zone(raw: str) -> str:
	z = str(raw or "").strip().lower().replace(" ", "_")
	return _ZONE_ALIASES.get(z, z)


def _score(raw: Any) -> float | None:
	if raw is None:
		return None
	if isinstance(raw, (int, float)):
		return float(max(0.0, min(100.0, raw)))
	text = str(raw).strip().lower()
	if not text:
		return None
	# Named bands
	named = {
		"exact": 95.0,
		"copy": 92.0,
		"high": 88.0,
		"match": 85.0,
		"close": 82.0,
		"medium": 70.0,
		"partial": 60.0,
		"low": 40.0,
		"ignore": 0.0,
		"different": 20.0,
	}
	if text in named:
		return named[text]
	# "85%" / "85"
	try:
		if text.endswith("%"):
			text = text[:-1]
		return float(max(0.0, min(100.0, float(text))))
	except ValueError:
		return None


def _zones_from_feedback(feedback: dict[str, Any]) -> list[dict[str, Any]]:
	raw = (
		feedback.get("chrome_fidelity")
		or feedback.get("fidelity_zones")
		or feedback.get("vs_inspiration_chrome")
		or []
	)
	if isinstance(raw, dict):
		# {nav: 90, aside: 85, ...} or {nav: {fidelity: 90, ref_id: ...}}
		rows: list[dict[str, Any]] = []
		for key, val in raw.items():
			zone = _norm_zone(str(key))
			if isinstance(val, dict):
				rows.append(
					{
						"zone": zone,
						"fidelity": _score(val.get("fidelity") or val.get("score") or val.get("match")),
						"ref_id": val.get("ref_id") or val.get("primary_ref_id"),
						"notes": val.get("notes") or val.get("idea") or val.get("tweak"),
					}
				)
			else:
				rows.append({"zone": zone, "fidelity": _score(val), "ref_id": None, "notes": None})
		return rows
	if not isinstance(raw, list):
		return []
	out: list[dict[str, Any]] = []
	for item in raw:
		if not isinstance(item, dict):
			continue
		zone = _norm_zone(str(item.get("zone") or item.get("section") or ""))
		if not zone:
			continue
		out.append(
			{
				"zone": zone,
				"fidelity": _score(
					item.get("fidelity")
					or item.get("score")
					or item.get("match")
					or item.get("pct")
				),
				"ref_id": item.get("ref_id") or item.get("primary_ref_id"),
				"notes": item.get("notes") or item.get("tweak") or item.get("idea"),
			}
		)
	return out


def evaluate_chrome_fidelity(
	feedback: dict[str, Any] | None,
	*,
	min_mean: float = _MIN_MEAN_FIDELITY,
	min_zone: float = _MIN_ZONE_FIDELITY,
) -> dict[str, Any]:
	"""Return fidelity_locked + reasons. Target ~80–90% copy with taste tweaks."""
	fb = feedback if isinstance(feedback, dict) else {}
	zones = _zones_from_feedback(fb)
	by_zone: dict[str, dict[str, Any]] = {}
	for row in zones:
		z = row["zone"]
		if z and row.get("fidelity") is not None:
			by_zone[z] = row

	reasons: list[str] = []
	missing = [z for z in REQUIRED_ZONES if z not in by_zone]
	if missing:
		reasons.append(
			"chrome_fidelity missing zones: "
			+ ", ".join(missing)
			+ " — LOOK refs + live UI; score each zone 0–100 (target 80–90% copy)"
		)

	scores: list[float] = []
	weak: list[str] = []
	unrefed: list[str] = []
	for z in REQUIRED_ZONES:
		row = by_zone.get(z)
		if not row:
			continue
		sc = float(row["fidelity"])
		scores.append(sc)
		if sc < min_zone:
			weak.append(f"{z}={sc:.0f}")
		if not str(row.get("ref_id") or "").strip():
			unrefed.append(z)

	mean = sum(scores) / len(scores) if scores else 0.0
	if scores and mean < min_mean:
		reasons.append(
			f"mean chrome fidelity {mean:.0f}% < {min_mean:.0f}% — "
			"replicate chrome more closely from primary_ref_ids (taste tweaks OK)"
		)
	if weak:
		reasons.append(
			"zones below "
			+ f"{min_zone:.0f}%: "
			+ ", ".join(weak)
			+ " — copy structure/spacing/chrome from refs, then tweak"
		)
	if unrefed and len(unrefed) > 1:
		reasons.append(
			"bind ref_id on chrome zones (which inspiration blob you copied): "
			+ ", ".join(unrefed)
		)

	# Explicit host claim of intentional low fidelity is still a fail for claim —
	# they must raise scores by implementing, not by arguing.
	locked = not reasons and len(scores) >= _MIN_ZONES and mean >= min_mean
	return {
		"fidelity_locked": locked,
		"mean_fidelity": round(mean, 1) if scores else None,
		"min_mean_required": min_mean,
		"min_zone_required": min_zone,
		"zones_scored": list(by_zone.keys()),
		"zone_scores": {z: by_zone[z]["fidelity"] for z in by_zone},
		"reasons": reasons,
		"hint": (
			"FILL chrome_fidelity: [{zone:nav|aside|main|composer, fidelity:80-95, "
			"ref_id, notes:tweak}]. Goal: 80–90% visual copy of locked refs + taste."
			if not locked
			else f"chrome fidelity locked (mean={mean:.0f}%)"
		),
	}
