# Final Evidence Quality Layer — Synthesis (EXP-016 → EXP-020)

**Date:** 2026-07-18  
**Status:** Approved as the working evidence contract (experiment-backed)  
**Baseline:** `python scripts/decision_lab.py run` → **22/22**  
**Companion:** [`2026-07-18-final-coordination-layer-synthesis.md`](2026-07-18-final-coordination-layer-synthesis.md) (Coordination v1)

---

## 1. What we were building

Evidence quality is not “more gates.” It is making Inspiration / Snapshot / Design Review / SpecDiff **honest and readable** so agents naturally make better UI decisions.

```text
tool envelope
  → normalize._capability_outcome (quality payload)
  → capability_ledger
  → compile_engineering_strategy
       → evidence_quality_alerts
       → host_action suffixes (EVIDENCE THIN, SHIP THIN-CLEAR, SPECDIFF…, INSPIRATION SOFT)
  → agent_summary (alerts + advisory)
```

**Constraint (hard):** No new Coordination claim gates. Advancement rules stay transport / blocking / council_clear as before. Thin / soft-seed / revision honesty lives in **quality + host**, not in `implementation_gate`.

---

## 2. Experiment → requirement map

| Exp | Locked requirement | Enforced by |
|-----|-------------------|-------------|
| 016 | Characterize thin evidence as the agent under-use root cause | README findings |
| 017 | Snapshot / inspiration / ship / review ledger `quality` nonempty | `normalize._snapshot_evidence_quality`, `_specdiff` precursors |
| 018 | Thin snapshot + thin-clear ship on host / `evidence_quality_alerts` | `_evidence_quality_host_notes` |
| 019 | SpecDiff `delta_top_ids`, soft-seed skips, `SPECDIFF REVISION/SOFT-SEED` | `_specdiff_quality_fields` + host |
| 020 | Inspiration soft host + promote locks into baseline | `INSPIRATION SOFT/THIN` + `packs/baseline.yaml` |
| 021 | Freeze evidence track; open Perfect Layer charter | this doc |

---

## 3. Quality contract (frozen)

| Family | Must expose in ledger `quality` | Host marker when weak |
|--------|--------------------------------|------------------------|
| Snapshot | regions, interactives, degraded, thin, evidence_useful, SpecDiff fields | `EVIDENCE THIN` / `EVIDENCE DEGRADED` |
| Inspiration | usable_image_refs, profiles_extracted, seed_unresolved_count | `INSPIRATION SOFT` / `INSPIRATION THIN` |
| Ship | coverage, coverage_checks, thin_clear | `SHIP THIN-CLEAR` |
| SpecDiff / review | delta_top_ids, drift counts, soft_seed_partial | `SPECDIFF REVISION` / `SPECDIFF SOFT-SEED` |

`advancement_eligible` may still be true when these fire — honesty without new gates.

---

## 4. What we deliberately stop expanding (evidence track)

After this synthesis, **pause evidence-quality feature growth** unless a Decision Lab scenario proves a regression or a new charter opens.

Still allowed:

- Bugfixes that keep baseline 22/22 green  
- Promoting additional stable scenarios into baseline  
- Producer-side richness (better snapshot_summary fields) that feed existing quality keys  

Not allowed without a new charter:

- Turning quality flags into hard claim gates  
- New MCP tools solely for “more evidence theater”  
- Parallel quality systems outside `coordination_evidence.quality`  

---

## 5. How to keep it true

```bash
python scripts/decision_lab.py run
python -m pytest tests/decision_lab/ -q
```

Scorecard for this freeze:  
`evals/decision_lab/experiments/EXP-021-evidence-synthesis/baseline_scorecard.json`

---

## 6. Bridge to the Perfect Coordination Layer

Coordination v1 + Evidence quality v1 are now both frozen. Research that still sits unused:

| Source | Unrealized for “perfect” layer |
|--------|--------------------------------|
| `evals/ARCHITECTURE_RETHINK.md` §3.8 | Invisible coordinator (<50ms); slim `data.coordinator` |
| Performance review | Bridge must not block MCP event loop |
| EXP-001–015 | Portfolio / one voice / surface ship — already shipped |
| EXP-016–020 | Evidence honesty — already shipped |
| Known gaps in v1 synthesis | Per-route backlog tags on `mixed`; playbook override clarity |

**Perfect Coordination Layer** = the product that makes v1 **felt** as an invisible episode OS: fast, one voice, evidence-honest, surface-aware — without adding gate ladders.

That work needs a **new design charter** (not more EXP-0xx feature spikes under the frozen tracks).

---

## 7. Verdict

Evidence quality is **experimentally mature**:

- Thin / thin-clear / SpecDiff / inspiration soft are readable on host  
- Baseline CI locks the contract (22/22)  
- Coordination v1 remains the only claim ladder  

**Ship this as the evidence contract.** Next: design the Perfect Coordination Layer from research (perf + invisibility + integration), not more evidence gates.
