"""Gemini extract stage."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from . import gemini_client
from .paths import EXTRACTS, RAW, SCHEMAS
from .validate import write_or_draft

GOLD_EXTRACT = EXTRACTS / "src_fitts_law_yorku.json"
MAX_SNAPSHOT_CHARS = 60_000


def read_snapshot(source_id: str) -> str:
	folder = RAW / source_id
	for name in ("snapshot.md", "snapshot.html"):
		path = folder / name
		if path.exists():
			text = path.read_text(encoding="utf-8", errors="replace")
			if len(text) > MAX_SNAPSHOT_CHARS:
				return text[:MAX_SNAPSHOT_CHARS] + "\n\n[TRUNCATED]"
			return text
	raise FileNotFoundError(f"No snapshot for {source_id}")


def build_extract_prompt(source_id: str, snapshot: str) -> str:
	schema = (SCHEMAS / "extract.schema.json").read_text(encoding="utf-8")
	gold = GOLD_EXTRACT.read_text(encoding="utf-8") if GOLD_EXTRACT.exists() else "{}"
	return f"""You are extracting engineering-usable UX/HCI claims from a source snapshot.

RULES:
- Use ONLY facts present in the snapshot. Do not invent locator quotes.
- Every claim must include locator.quote copied from the snapshot (≤500 chars).
- Fill engineering_meaning, how_to_detect_violations, when_to_apply, when_not_to_apply, tradeoffs, common_mistakes, examples.
- status must be "complete" only when those fields are filled; otherwise "incomplete".
- source_id must be exactly: {source_id}
- extracted_at: {date.today().isoformat()}
- extractor: "gemini_pipeline"
- Prefer 1–3 high-signal claims over many thin ones.

JSON SCHEMA (must validate):
{schema}

GOLD EXAMPLE EXTRACT (structure to emulate):
{gold}

SNAPSHOT FOR {source_id}:
---
{snapshot}
---
"""


def extract_source(source_id: str, *, client=None, model: str | None = None) -> dict[str, Any]:
	snapshot = read_snapshot(source_id)
	prompt = build_extract_prompt(source_id, snapshot)
	data = gemini_client.generate_json(prompt=prompt, temperature=0.1, client=client, model=model)
	data["source_id"] = source_id
	data.setdefault("extracted_at", date.today().isoformat())
	data.setdefault("extractor", "gemini_pipeline")
	data.setdefault("schema_version", "1")
	data.setdefault("skipped_notes", [])
	ok, errors = write_or_draft(
		EXTRACTS / f"{source_id}.json",
		data,
		"extract.schema.json",
		label=f"extract_{source_id}",
	)
	if not ok:
		# one retry with errors
		retry_prompt = prompt + "\n\nPREVIOUS OUTPUT FAILED VALIDATION:\n" + "\n".join(errors)
		data = gemini_client.generate_json(
			prompt=retry_prompt, temperature=0.05, client=client, model=model
		)
		data["source_id"] = source_id
		data.setdefault("extracted_at", date.today().isoformat())
		data.setdefault("extractor", "gemini_pipeline")
		data.setdefault("schema_version", "1")
		data.setdefault("skipped_notes", [])
		ok, errors = write_or_draft(
			EXTRACTS / f"{source_id}.json",
			data,
			"extract.schema.json",
			label=f"extract_{source_id}",
		)
	return {"source_id": source_id, "ok": ok, "errors": errors, "path": str(EXTRACTS / f"{source_id}.json")}
