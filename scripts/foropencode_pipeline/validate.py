"""JSON Schema validation + draft fallback."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft202012Validator

from .paths import DRAFTS, NORMALIZED, SCHEMAS

OPS = [
	"how_to_detect_violations",
	"when_to_apply",
	"when_not_to_apply",
	"tradeoffs",
	"common_mistakes",
	"examples",
	"why_humans_behave_this_way",
]


def load_schema(name: str) -> dict[str, Any]:
	path = SCHEMAS / name
	return json.loads(path.read_text(encoding="utf-8"))


def validate_instance(instance: dict[str, Any], schema_name: str) -> list[str]:
	schema = load_schema(schema_name)
	validator = Draft202012Validator(schema)
	return [
		f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}"
		for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
	]


def write_or_draft(
	path: Path,
	data: dict[str, Any],
	schema_name: str,
	*,
	label: str,
) -> tuple[bool, list[str]]:
	"""Validate and write to path, or dump draft and return errors."""
	errors = validate_instance(data, schema_name)
	text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
	if errors:
		DRAFTS.mkdir(parents=True, exist_ok=True)
		draft = DRAFTS / f"{label}_{date.today().isoformat()}.json"
		draft.write_text(text, encoding="utf-8")
		return False, errors
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(text, encoding="utf-8")
	return True, []


def operational_card_gaps(card: dict[str, Any]) -> list[str]:
	return [k for k in OPS if not card.get(k)]


def validate_all_cards() -> tuple[int, int, list[str]]:
	ok = 0
	lines: list[str] = []
	paths = sorted(NORMALIZED.glob("UX_*.json"))
	for path in paths:
		card = json.loads(path.read_text(encoding="utf-8"))
		schema_errs = validate_instance(card, "claim_card.schema.json")
		ops = operational_card_gaps(card)
		if not schema_errs and not ops:
			ok += 1
			lines.append(f"{path.name} OK")
		else:
			lines.append(f"{path.name} FAIL schema={schema_errs} ops={ops}")
	return ok, len(paths), lines
