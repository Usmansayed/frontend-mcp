"""Emit ForOpenCode Phase 9 runtime packs from normalized claim cards."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path("ForOpenCode")
CARDS = {
	p.stem: json.loads(p.read_text(encoding="utf-8"))
	for p in (ROOT / "06_corpus" / "normalized").glob("UX_*.json")
}


def stub(cid: str) -> dict:
	c = CARDS[cid]
	return {
		"claim_id": c["id"],
		"name": c["name"],
		"engineering_meaning": c["engineering_meaning"],
		"how_to_detect_violations": c.get("how_to_detect_violations", ""),
		"when_to_apply": c.get("when_to_apply", ""),
		"when_not_to_apply": c.get("when_not_to_apply", ""),
		"confidence": c["confidence"],
		"source_ids": c["supporting_source_ids"],
		"full_card_path": f"06_corpus/normalized/{cid}.json",
	}


PACKS = [
	{
		"pack_id": "pack_a11y_absolute",
		"title": "Absolute Accessibility Constraints",
		"target_surfaces": [
			"perception://verification-guide",
			"perception://ship-council",
			"hotfix",
			"polish",
		],
		"ids": [
			"UX_A11Y_TARG_004",
			"UX_A11Y_CONT_005",
			"UX_A11Y_FOCUS_011",
			"UX_DS_TOKEN_001",
		],
		"conflicts": [],
		"notes": "Hard constraints — never dilute for brand.",
	},
	{
		"pack_id": "pack_forms_checkout",
		"title": "Forms and Checkout",
		"target_surfaces": [
			"perception://design-workflow",
			"feature",
			"greenfield",
		],
		"ids": [
			"UX_ARC_FORM_010",
			"UX_PRD_GUEST_001",
			"UX_INX_ERR_009",
			"UX_INX_SELF_001",
			"UX_ARC_ISO_001",
			"UX_COG_FOGG_013",
			"UX_A11Y_CONT_005",
		],
		"conflicts": [
			{
				"a": "UX_COG_HICK_002",
				"b": "UX_HCI_FITTS_001",
				"decision_hint": "One large primary CTA; disclose secondary options. Never below WCAG target floor.",
			}
		],
		"notes": "Maps to form/checkout playbook guide_form_opt.",
	},
	{
		"pack_id": "pack_greenfield_structure",
		"title": "Greenfield Structural Decisions",
		"target_surfaces": [
			"perception://design-workflow",
			"perception://engineering-strategy",
			"greenfield",
			"redesign",
		],
		"ids": [
			"UX_ARC_ISO_001",
			"UX_COG_HICK_002",
			"UX_HCI_FITTS_001",
			"UX_A11Y_TARG_004",
			"UX_A11Y_CONT_005",
			"UX_COG_FOGG_013",
			"UX_A11Y_FOCUS_011",
		],
		"conflicts": [
			{
				"a": "UX_COG_HICK_002",
				"b": "UX_HCI_FITTS_001",
				"decision_hint": "Prioritize WCAG mins, one primary CTA, then chunk choices.",
			}
		],
		"notes": "Structural influence pack for engineering_strategy unresolved decisions.",
	},
]


def main() -> None:
	out = ROOT / "09_runtime"
	out.mkdir(exist_ok=True)
	for pack in PACKS:
		obj = {
			"pack_id": pack["pack_id"],
			"title": pack["title"],
			"target_surfaces": pack["target_surfaces"],
			"claim_stubs": [stub(i) for i in pack["ids"]],
			"conflict_pairs": pack["conflicts"],
			"budgets": {"max_claim_stubs": 12, "max_rationale_tokens": 1500},
			"created_at": "2026-07-19",
			"notes": pack["notes"],
		}
		assert len(obj["claim_stubs"]) <= 12
		path = out / f"{pack['pack_id']}.json"
		path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
		print("wrote", path, len(obj["claim_stubs"]))


if __name__ == "__main__":
	main()
