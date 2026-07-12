# Planning Pattern — Snapshot → Review → Consistency (Design pipeline)

Design-review chain shared by design_sense and consistency modules.

## Signature

- **Applies to states in:** cluster.design.review_and_snapshot, cluster.consistency.audit_cycle.
- **Preconditions:** scan_id available; PDG present for Consistency.

## Steps

1. **observe** — scan target page.
2. **build_design_snapshot** — normalize into `snapshot_id`.
3. **design_review** (heuristic critique) — optional advisory pass.
4. **consistency_audit** — if PDG present; enumerate deviations.
5. **assess** particular selector when triaging → **propose_fix** → apply → **re-audit**.

## Recovery rules

- Snapshot fails → observe again (page may have changed).
- consistency_audit with empty PDG → refresh PDG first (`global.Sxx.pdg_refresh_failed` on failure).
- Deviation is expected style → `exception_documented`.

## States that embed this pattern

- marketing.S03.design.pdg_empty_snapshot_ready → design_review_open → applying_fix
- dssite.S09.consistency_cleanup.pdg_seeded_* → audit_findings_open → propose_fix_open → applying_fix

## Coordination implications

- Snapshot registry caches per-scan snapshots — do not re-build if cached and page unchanged.
- Design Sense is advisory; Consistency Audit is authoritative — do not conflate.
