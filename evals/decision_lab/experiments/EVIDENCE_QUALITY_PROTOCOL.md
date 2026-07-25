# Evidence Quality Experiments — Protocol

**Track:** Raise usefulness of Inspiration / Snapshot / Design Review / SpecDiff evidence.  
**Constraint:** No new Coordination gates. Enrich `coordination_evidence.quality`, `agent_summary`, and SpecDiff honesty so agents naturally make better UI decisions.

**Folder:** continues `evals/decision_lab/experiments/EXP-NNN-*` (numbers 016+)

## Loop

1. Characterize weak evidence (what agents see vs what they need)  
2. Lab scenario / pure-function test locks desired quality payload  
3. Tweak producer or `normalize._capability_outcome`  
4. Re-run baseline (must stay green) + promote when stable  

## Non-goals

- New MCP tools  
- Harder claim gates  
- Expanding Ship/section/residue ladders  
