## After (Tweak A)

| After feed | gate.next | host_theme | portfolio.paid | portfolio.unpaid |
|------------|-----------|------------|----------------|------------------|
| inspiration | (component…) | EVIDENCE/other | inspiration | component, snapshot, … |
| snapshot | … | … | inspiration, snapshot | component, … |
| component | … | … | +component | … |
| verify | **design_review** | **SHIP GATE** | +verify | **design_review**, observe |

### Fixed
- `host_action` priority now matches gate: ship before evidence_plan.  
- `episode_portfolio` exposes paid/unpaid/deferred families.  
- Scenario `ship_host_aligns.yaml` + pytest green.

### Still open
- `suggested_capability` can still disagree with `gate.next` (playbook vs gate) — EXP-002 target.  
- Observe unpaid after verify is correct advisory; ensure agents don't prefer it over ship.

## Verdict

**Partial win.** Coordination no longer lies about SHIP vs EVIDENCE after verify. Portfolio makes multi-family episode visible. Not yet “one voice” for suggested_capability.

## Next

EXP-002 — force gate.next to win when claim is prohibited (align briefing suggestion).
