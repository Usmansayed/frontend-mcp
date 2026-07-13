"""Print a compact summary of batch.jsonl sandbox results."""
from __future__ import annotations

import json
from pathlib import Path

path = Path("coordination_sandbox/output/batch.jsonl")
rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
print(f"{len(rows)} scenarios")
hdr = (
    f"{'prompt':30} {'scope':18} {'policy_start':32} "
    f"{'B':>3} {'spent':>5}/{'>total':>5} {'EQG':>5} {'design':>6} heavy_skipped"
)
print(hdr)
print("-" * len(hdr))
for r in rows:
    heavy = [
        s["capability_id"]
        for s in r["skipped"]
        if s["capability_id"]
        in ("inspiration_workflow", "design_review", "seo_evidence_collect", "resource_workflow")
    ]
    print(
        f"{r['prompt'][:30]:30} "
        f"{r['initial_discriminators']['task_scope']:18} "
        f"{r['initial_situation_policy_id']:32} "
        f"{r['engineering_investment_b_base']:3} "
        f"{r['budget_spent']:5}/{r['budget_total']:5} "
        f"{r['estimated_engineering_value']:5.1f} "
        f"{str(r['design_oriented']):>6} "
        f"{','.join(heavy) or '-'}"
    )
