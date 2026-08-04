# Chrome fidelity + parallel intel enforcement (`1.2.0.dev66`)

**Goal:** Force agents to **copy liked visuals at ~80–90%** (with taste tweaks) and to **use** component / resources / consistency intelligence — fast via parallel HTTP, not serial ceremony.

## Why

A one-image "build this" coding agent often beats the full MCP ladder on visual quality because matching the picture is the only win condition. Agents were clearing `claim_ok` via verify/sections without chrome matching locked refs, and under-using Resource / Consistency / Design Graph.

## Enforcement

1. **`chrome_fidelity` attestation** (`planning/chrome_fidelity.py`)
   - VF purpose=design must score zones `nav|aside|main|composer` (aliases: header/sidebar/thread/composer).
   - Mean ≥80, each zone ≥75, bind `ref_id`s.
   - Soft `judgment: ok` without zones → next_action `attest_chrome_fidelity`; family unpaid.

2. **Claim-sticky families** after verify (`CLAIM_STICKY_AFTER_VERIFY`):
   - `inspiration_extract`, `resources`, `consistency`, `fidelity`
   - Greenfield/redesign cannot claim while any remain unpaid.

3. **Pack critical** on greenfield/redesign heavy+:
   - Includes `component`, `resources`, `fidelity`, `consistency` (not optional).

4. **Parallel HTTP** (`card.can_parallel` + `card.parallel_batch`):
   - Fire concurrently: creative_assets ∥ component foundation ∥ inspiration_pulse ∥ design_graph_refresh / consistency_audit.
   - Browser tools stay single-flight.

## Host loop

```
session_start → pulse warm
→ parallel: creative_assets ∥ select_foundation ∥ inspiration_pulse ∥ graph_refresh
→ VF inspiration (primary_ref_ids + borrow) → implement ~80–90% copy + assets
→ VF design + chrome_fidelity zones → consistency_audit
→ verify → claim when claim_ok
```

Hotfix/forms stay lean — no fidelity/resources ladder.
