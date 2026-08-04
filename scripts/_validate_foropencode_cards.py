"""Validate ForOpenCode claim cards have operational fields."""
from __future__ import annotations

import json
import pathlib

OPS = [
	"how_to_detect_violations",
	"when_to_apply",
	"when_not_to_apply",
	"tradeoffs",
	"common_mistakes",
	"examples",
	"why_humans_behave_this_way",
]
root = pathlib.Path("ForOpenCode/06_corpus/normalized")
ok = 0
paths = sorted(root.glob("UX_*.json"))
for path in paths:
	card = json.loads(path.read_text(encoding="utf-8"))
	missing = [k for k in OPS if not card.get(k)]
	status = "OK" if not missing else f"MISSING {missing}"
	print(path.name, status)
	ok += not missing
print(f"complete {ok}/{len(paths)}")
manifest = pathlib.Path("ForOpenCode/06_corpus/raw/src_ibm_carbon/manifest.yaml").read_text(
	encoding="utf-8"
)
print("carbon_has_checksum", 'checksum_sha256: ""' not in manifest and "9b922889" in manifest)
