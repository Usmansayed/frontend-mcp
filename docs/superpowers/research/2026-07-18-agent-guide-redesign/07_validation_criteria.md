# 07 — Validation Criteria (for redesigned guides)

Guides are not “done” when they look clean. They pass when decisions improve.

## V1 — Offline Guide Lab (required)

| Pack | Bar |
|------|-----|
| Base Q01–Q24 | B ≥ 95% |
| Hard H01–H24 | B ≥ 90% |
| A (singular tunnel) remains weak | Sanity check that gold still punishes tunnel |

After redesign, **re-encode** `decide_arm_b` to match new guides (or LLM mode) and re-run.

## V2 — Coverage checklist (manual review)

Each P0 failure mode (see 02) has:

- An explicit hard-fail line in guides  
- At least one quiz scenario  
- A clear owe/skip row for the relevant class  

## V3 — Length budget

| Artifact | Target |
|----------|--------|
| Primary scoreboard card | ≤ 1 screen (~400–600 words) |
| Each situation card | ≤ 1 screen |
| Hard fails card | ≤ 1 screen |
| Total primary pack | Prefer ≤ ~2.5k words |
| Deep methodology | Unchanged; linked, not inlined |

## V4 — Contradiction scan

Before promote: diff primary pack vs production rule for C1–C11; no “always follow next” without unpaid.

## V5 — Optional later (not blocking research)

- LLM quiz mode: same YAML, prompt = arm_a_large vs new guides  
- 2–3 live redesign sessions on Guide Lab MCP only  

## Success definition for “what to do”

**Adopt redesigned clean guides as the agent primary contract** if V1–V4 pass.  
Keep MCP facts simple. Promote to production rule/methodology only after explicit approval.
