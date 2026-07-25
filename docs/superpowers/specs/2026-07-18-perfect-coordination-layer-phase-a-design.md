# Perfect Coordination Layer — Phase A Design (Invisible & Fast)

**Date:** 2026-07-18  
**Status:** Approved (user) — ready for implementation plan  
**Charter:** Make Coordination v1 + Evidence v1 **felt** as an invisible episode OS — not more gates.  
**Prerequisites:**  
- [`2026-07-18-final-coordination-layer-synthesis.md`](2026-07-18-final-coordination-layer-synthesis.md)  
- [`2026-07-18-final-evidence-quality-synthesis.md`](2026-07-18-final-evidence-quality-synthesis.md)  
- Research: `evals/ARCHITECTURE_RETHINK.md` §3.8, `evals/PERFORMANCE_REVIEW.md`

**Phase B** (Unified Episode Readout) is deferred until Phase A is green.

---

## 1. Problem

Coordination is correct but **heavy on every MCP tool result**:

1. `_enrich_envelope` embeds a large `data.coordinator` (full briefing + strategy slices).  
2. Every bridge pass recompiles `engineering_strategy` even when the ledger/gate fingerprint did not change.  
3. Agents drown in nested payloads; research target is **&lt;50ms** invisible advisory.

Behavior (gates, host honesty, evidence alerts) must stay identical. Only cost and payload shape change.

---

## 2. Goals & non-goals

### Goals

| ID | Goal | Measure |
|----|------|---------|
| G1 | Slim `data.coordinator` on every tool envelope | Payload keys match §3; no full `briefing.to_dict()` |
| G2 | Skip redundant strategy compile | Fingerprint hit → reuse cached strategy; Decision Lab host/gate identical |
| G3 | Profile harness | Micro-bench for bridge hot path; document p95; optional CI budget once floor known |
| G4 | Baseline unchanged | `python scripts/decision_lab.py run` → **22/22** |

### Non-goals

- New claim gates or quality→gate promotion  
- Route-level backlog (option C)  
- New MCP tools  
- Defaulting `COORDINATION_DISABLED`  
- Phase B `episode_card` packaging (follow-on)

---

## 3. Slim coordinator contract

`data.coordinator` becomes a **compact advisory card**:

```json
{
  "episode_id": "...",
  "integrated": true,
  "host_action": "...",
  "gate": {
    "state": "blocked|provisional|ready|...",
    "next_required_capability": "...",
    "prohibited_actions": ["claim_complete"]
  },
  "suggested_capability": "...",
  "suggested_semantic_action": "...",
  "stop_reason": null,
  "confidence": { "score": 0.42, "band": "low" },
  "portfolio": {
    "paid": ["snapshot", "verify"],
    "unpaid": ["inspiration", "ship"]
  },
  "evidence_quality_alerts": ["EVIDENCE THIN: ..."],
  "recommended_resource": "perception://...",
  "schema": "coordinator_card.v1"
}
```

**Still available elsewhere (not removed):**

- `agent_summary.engineering_strategy` — full strategy (via `surface_engineering_strategy`)  
- Explicit `perception_coordinator_briefing` — full briefing when host asks  

**Removed from every-tool `data.coordinator`:**

- Full `briefing` object  
- Full `evidence_plan` list  
- Full `psm_summary` / investment / routing essays (optional: keep one-line `routing_rationale` max 200 chars if already short)

Compatibility: keep `implementation_gate` alias at top of card **or** only under `gate` — prefer **`gate` only** and duplicate `implementation_gate` as deprecated alias for one release if tests require it. Plan: provide both `gate` and `implementation_gate` (same dict) for one cycle so hosts don't break.

---

## 4. Strategy compile skip

### Fingerprint inputs

Compute `strategy_fingerprint(psm) -> str` from:

- `capability_ledger` entries: for each cap → `(status, advancement_eligible, quality thin/thin_clear/revision_required/soft_seed_partial)`  
- Episode: `verification_status`, `surface_type`, ship clear/run flags, residue flags, section checklist incomplete set  
- Intent/lifecycle/maturity/situation_class (coarse)

### Behavior

After `apply_envelope` / briefing refresh path:

1. Compute fingerprint.  
2. If `psm.briefing.engineering_strategy` exists and fingerprint == `psm.episode.retry_counters["strategy_fingerprint"]`:  
   - **Skip** `compile_engineering_strategy`  
   - Still run `_align_suggestion_with_gate` if needed  
3. Else: compile, store strategy, store fingerprint.

Decision Lab + unit tests must assert host_action / gate.state / alerts unchanged on skip vs compile for identical PSM.

Store fingerprint on `retry_counters["strategy_fingerprint"]` (already persisted) — no new EpisodeState field required unless we prefer a dedicated field later.

---

## 5. Profile harness

Add `evals/decision_lab/bench_bridge.py` or `scripts/bench_coordinator_bridge.py`:

- Start episode, feed N observe/verify envelopes (fixtures).  
- Time `CoordinatorBridge.process` / `service.process_tool_envelope`.  
- Print p50/p95; write JSON under `evals/decision_lab/experiments/` when requested.

CI: initially **report-only** (no hard fail). After a week of numbers, set budget (e.g. p95 &lt; 50ms on fixture hardware) in a follow-on EXP.

---

## 6. Testing strategy

| Layer | What |
|-------|------|
| Unit | `build_coordinator_card(briefing/strategy)` shape; fingerprint stability; skip vs recompile |
| Decision Lab | Existing baseline 22/22; add scenario asserting `data.coordinator` has `schema: coordinator_card.v1` and lacks nested `briefing.engineering_strategy` |
| Bench | Smoke run in plan; not required green for merge |

---

## 7. Rollout

1. Implement card builder + slim enrich (behavior-preserving aliases).  
2. Fingerprint skip.  
3. Lab scenario + baseline promote if stable.  
4. Bench script.  
5. Phase B charter separately.

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Hosts parsing old `data.coordinator.briefing` | Keep `implementation_gate` alias; document break in methodology one-liner |
| Fingerprint too coarse → stale host | Include quality alert-driving fields in fingerprint |
| Fingerprint too fine → never skip | Hash only gate-relevant quality flags, not full quality blobs |

---

## 9. Verdict

Phase A is a **perf + packaging** change on a frozen behavioral contract. Perfect coordination starts by disappearing into the hot path.
