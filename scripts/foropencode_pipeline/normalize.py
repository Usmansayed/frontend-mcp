"""Gemini normalize → claim cards."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from . import gemini_client
from .paths import EXTRACTS, NORMALIZED, SCHEMAS
from .scrape import load_pass
from .validate import write_or_draft

GOLD_CARD = NORMALIZED / "UX_HCI_FITTS_001.json"


def build_normalize_prompt(claim_id: str, source_id: str, extract: dict[str, Any]) -> str:
	schema = (SCHEMAS / "claim_card.schema.json").read_text(encoding="utf-8")
	gold = GOLD_CARD.read_text(encoding="utf-8")
	return f"""Normalize one operational claim card for the Frontend MCP UX corpus.

TARGET claim id (must use exactly): {claim_id}
Primary source_id: {source_id}

RULES:
- Match the gold card field names and style (id, name, category, definition, engineering_meaning, …).
- supporting_source_ids must include {source_id}.
- extract_ids must reference this extract like "{source_id}.json#c01".
- Fill how_to_detect_violations, when_to_apply, when_not_to_apply, tradeoffs, common_mistakes, examples, why_humans_behave_this_way.
- evidence_class: law|standard|empirical|heuristic|opinion as appropriate.
- consensus_status: single_source unless clearly multi-source.
- version: 1 (or increment if revising an existing card), last_reviewed: {date.today().isoformat()}
- revision_notes: "Gemini pipeline normalize"
- additionalProperties are forbidden — only schema fields.
- Do not dilute Absolute a11y cards.

JSON SCHEMA:
{schema}

GOLD CARD EXAMPLE:
{gold}

SOURCE EXTRACT JSON:
{json.dumps(extract, indent=2)}
"""


def normalize_card(
	claim_id: str,
	source_id: str,
	*,
	client=None,
	model: str | None = None,
) -> dict[str, Any]:
	extract_path = EXTRACTS / f"{source_id}.json"
	extract = json.loads(extract_path.read_text(encoding="utf-8"))
	prompt = build_normalize_prompt(claim_id, source_id, extract)
	data = gemini_client.generate_json(prompt=prompt, temperature=0.1, client=client, model=model)
	if "claim_id" in data and "id" not in data:
		data["id"] = data.pop("claim_id")
	data["id"] = claim_id
	if isinstance(data.get("common_mistakes"), list):
		data["common_mistakes"] = "; ".join(str(x) for x in data["common_mistakes"])
	if isinstance(data.get("examples"), str):
		data["examples"] = [data["examples"]]
	# Preserve higher version if revising existing card
	existing = NORMALIZED / f"{claim_id}.json"
	if existing.exists():
		try:
			prev = json.loads(existing.read_text(encoding="utf-8"))
			data["version"] = int(prev.get("version") or 1) + 1
		except Exception:  # noqa: BLE001
			data.setdefault("version", 1)
	else:
		data.setdefault("version", 1)
	data.setdefault("last_reviewed", date.today().isoformat())
	if source_id not in data.get("supporting_source_ids", []):
		data["supporting_source_ids"] = list(
			dict.fromkeys([*(data.get("supporting_source_ids") or []), source_id])
		)
	schema = json.loads((SCHEMAS / "claim_card.schema.json").read_text(encoding="utf-8"))
	allowed = set(schema.get("properties", {}))
	data = {k: v for k, v in data.items() if k in allowed}
	ok, errors = write_or_draft(
		NORMALIZED / f"{claim_id}.json",
		data,
		"claim_card.schema.json",
		label=f"card_{claim_id}",
	)
	if not ok:
		retry = prompt + "\n\nVALIDATION ERRORS:\n" + "\n".join(errors)
		data = gemini_client.generate_json(
			prompt=retry, temperature=0.05, client=client, model=model
		)
		if "claim_id" in data and "id" not in data:
			data["id"] = data.pop("claim_id")
		data["id"] = claim_id
		if isinstance(data.get("common_mistakes"), list):
			data["common_mistakes"] = "; ".join(str(x) for x in data["common_mistakes"])
		if isinstance(data.get("examples"), str):
			data["examples"] = [data["examples"]]
		data.setdefault("version", 1)
		data.setdefault("last_reviewed", date.today().isoformat())
		data = {k: v for k, v in data.items() if k in allowed}
		ok, errors = write_or_draft(
			NORMALIZED / f"{claim_id}.json",
			data,
			"claim_card.schema.json",
			label=f"card_{claim_id}",
		)
	return {"claim_id": claim_id, "ok": ok, "errors": errors}


def normalize_pass(
	pass_num: int = 1,
	*,
	client=None,
	model: str | None = None,
) -> list[dict[str, Any]]:
	out = []
	for entry in load_pass(pass_num):
		out.append(
			normalize_card(
				entry["claim_id"],
				entry["source_id"],
				client=client,
				model=model,
			)
		)
	return out


def normalize_pass1(*, client=None, model: str | None = None) -> list[dict[str, Any]]:
	return normalize_pass(1, client=client, model=model)
