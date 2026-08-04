# Coordination Experiments — Protocol

**Purpose:** Treat coordination as the layer that makes **all MCP tool families work as one episode**.  
Use the Decision Lab (no real tools). Each experiment: hypothesis → scenarios/tests → observe → tweak → re-test → **report**.

**Folder:** `evals/decision_lab/experiments/`

## Naming

```text
EXP-NNN-<slug>/
  README.md          # hypothesis, method, results, next
  scenarios/         # YAML fed to decision lab (optional)
  notes.md           # raw observations (optional)
```

Top-level `INDEX.md` lists all experiments and verdicts.

## Loop

1. Write hypothesis (what “one coordination” should do)  
2. Encode as lab scenario(s) +/or pytest  
3. Run pack / experiment scenarios — record **actual** behavior  
4. Tweak coordination (small, reversible)  
5. Re-run — update report with before/after  
6. Do **not** declare final architecture until several experiments converge  

## Families in scope (episode portfolio)

| Family | Example tools |
|--------|----------------|
| observe | navigate_and_observe, screenshot |
| inspiration | inspiration_collect / search |
| figma | figma context |
| snapshot | build_design_snapshot |
| component | select_component_foundation |
| design_review / ship | design_review mode=ship |
| verify | perception_verify (+ sections) |
| resolve | resolve_route / resolve_component |
| seo | seo_audit_* (usually deferred) |

Coordination success = agent can see **portfolio + ROI next**, not only `next_required_capability`.
