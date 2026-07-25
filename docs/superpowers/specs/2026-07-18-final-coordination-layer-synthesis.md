# Final Coordination Layer — Synthesis (EXP-001 → EXP-013)

**Date:** 2026-07-18  
**Status:** Approved as the working architecture (experiment-backed)  
**Baseline:** `python scripts/decision_lab.py run` → **16/16** (see `packs/baseline.yaml`)  
**Lab:** Decision Layer Lab — fake envelopes only; production `CoordinationIntelligenceService`

---

## 1. What we were building

Coordination is not “another MCP feature.” It is the **episode brain** that makes all Frontend MCP tool families work as **one engineering process**:

```text
observe · inspiration/figma · snapshot · component · verify/sections · ship · residue
```

Agents remain the reasoners. Coordination returns **deterministic facts**: gate, backlog, portfolio, confidence, surface, host_action — so agents cannot honestly claim “done” while unpaid work remains.

---

## 2. Architecture (frozen v1 surface)

```text
                    ┌─────────────────────────────┐
  MCP tools ──env──►│ normalize → capability_ledger│
                    └─────────────┬───────────────┘
                                  ▼
                    compile_engineering_strategy
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
  implementation_gate      episode_backlog          episode_portfolio
  (claim / next)           (ROI top)                (paid/unpaid/deferred)
          │                       │                       │
          └───────────┬───────────┴───────────┬───────────┘
                      ▼                       ▼
              episode_confidence        host_action (one voice)
                      │
                      ▼
              Ship Council (surface-aware) + residue (one pass)
```

### First-class episode fields

| Field | Where | Role |
|-------|--------|------|
| `surface_type` | `EpisodeState` (not retry_counters) | Dashboard vs settings vs auth vs marketing vs mixed |
| `episode_backlog` | strategy | ROI-ranked open work; `top` = single next |
| `episode_portfolio` | strategy | Paid / unpaid / deferred families (advisory) |
| `episode_confidence` | strategy | Process completeness % + contributors (not a gate) |
| `initiative` | strategy | = portfolio.unpaid (compat) |
| `implementation_gate` | strategy | claim / next / section / ship / residue / evidence terminals |

### Gate priority (single ladder)

1. Structural **blocked**  
2. **Section checklist**  
3. **Residue** (one remasure)  
4. **Ship Council**  
5. **Evidence plan** open (completed | skipped-valid | superseded)  
6. Ready / claim allowed  

`host_action` and (on design/redesign/system_setup) `suggested_capability` **must agree** with `gate.next`.

---

## 3. Experiment → requirement map

| Exp | Locked requirement | Enforced by |
|-----|-------------------|-------------|
| 001 | Ship host before evidence host; portfolio exists | strategy host order + `episode_portfolio` |
| 002 | One voice: gate.next wins over playbook on design scopes | `service._align_suggestion_with_gate` |
| 003 | Settings ≠ dashboard ship heuristics | `ship_council` surface signals |
| 004 | Snapshot supersedes design_reference in backlog | `design_reference_posture=snapshot` |
| 005 | Multi-route Meridian stays `mixed`, no inspiration tunnel | baseline scenario |
| 006 | Sections unpaid even if page verify paid; then ship | portfolio family `sections` |
| 007 | Confidence tracks paid families | portfolio coverage in confidence |
| 008 | Full claim path: sections→ship→residue→dispose→claim | lab `run_ship` + residue family |
| 009 | Codebase does not block visual claim | intent-gated `_applies_codebase_context` |
| 010 | `coordination_evidence.status` ≠ silent noop | normalize outcome/status alias |
| 011–012 | Baseline pack + scorecard | `packs/baseline.yaml`, `--scorecard` |
| 013 | Host lists unpaid families (≥2) | host_action suffix |

---

## 4. Done means (design episode)

Claim-complete is honest only when:

1. Page verify passed (and chrome conventions if applicable)  
2. Section checklist complete when required  
3. Residue closed if it was required (one pass max)  
4. `ship_council_clear`  
5. Evidence-plan terminals for structural items: completed / skipped(valid) / superseded  
6. Hotfix/surgical path never picks up this ladder  

Confidence is a **readout**, not a gate. Initiative/portfolio is **advisory**, not a second gate.

---

## 5. What we deliberately stop expanding

After this synthesis, **pause Coordination Intelligence feature growth**.

Next major investment: **evidence quality** from Inspiration, Design Snapshot, Design Review, SpecDiff — so agents produce better UIs because evidence is valuable, not because more gates exist.

*(Update 2026-07-18: Evidence quality v1 is also frozen — see `2026-07-18-final-evidence-quality-synthesis.md`. Next charter = Perfect Coordination Layer.)*

Still allowed:

- Bugfixes proven by Decision Lab baseline  
- New baseline scenarios that lock regressions  
- Evidence-layer improvements that feed the same ledger  

Not allowed without a new experiment charter:

- New MCP coordinator tools  
- Parallel “AI coordinator” runtime  
- Endless polish / multi-residue loops  
- Turning initiative into a hard gate  

---

## 6. How to keep it true

```bash
python scripts/decision_lab.py run                 # baseline
python scripts/decision_lab.py run -p smoke        # fast
python -m pytest tests/decision_lab/ -q
```

Every coordination change: add/adjust a scenario → promote to `packs/baseline.yaml` when stable → never delete an experiment report.

---

## 7. Remaining known gaps (candidates, not v1 blockers)

| Gap | Notes |
|-----|------|
| Per-route backlog tags on `mixed` | Surface is episode-level; route-level tags still thin |
| Playbook semantic actions | Overridden to `follow_gate:*` on design align — acceptable |
| Evidence quality | Out of coordination scope — next investment track |

---

## 8. Verdict

The coordination layer is **experimentally mature** for v1:

- Whole-episode portfolio + ROI backlog  
- Surface-aware Ship Council  
- Bounded residue  
- One voice on the claim ladder  
- Lab + baseline pack as the permanent regression harness  

**Ship this as the coordination contract.** Improve evidence next.
