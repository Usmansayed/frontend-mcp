# Research: Why redesign skimmed 16 refs / 2 LOOK — and the fix (dev64)

**Date:** 2026-07-30  
**Trigger:** Host collected 16 inspiration blobs, LOOK’d 2, soft-mooded 14, claimed redesign done; chrome stayed GPT-shell; message layout bugs missed.

## Root cause (not “OCR missing” alone)

Frontend-mcp is a **deterministic evidence runtime**. It does **not** run VLM/OCR inside the server. Image *understanding* is **host vision** after MCP attaches pixels.

The product failure was enforcement:

| Behavior | Old gate | Result |
|----------|----------|--------|
| Collect ≥3 blobs | `inspiration` **paid** | Pack “done” without LOOK |
| Soft `borrow: ["navy calm"]` | `look_locked=true` | Extract cleared |
| Redesign critical pack | observe→snapshot→VF→verify (**no** inspiration*) | Claim without digesting galleries |
| After `verified=true` | pre-verify unpaid ignored | Soft-mood claim_ok |
| VF purpose=inspiration | mostly **live page** shots | Blobs not forced into LOOK loop |

\*Snapshot-first redesign also suppressed gallery unpaid — correct for *ordering*, wrong once a pack was already collected.

## Desired product behavior

1. Collect many refs (OK).  
2. **Digest** many images (LOOK attached `inspiration:*` blobs).  
3. Lock **structured** borrow: `{ref_id, section, idea}` for chrome you want to **copy with tweaks**.  
4. Implement from that lock — not invent sidebar/header from ChatGPT memory.  
5. `claim_ok` false until digest clears.

## Fix shipped (`1.2.0.dev64`)

1. `inspiration_look_lock.py` — soft mood alone invalid; require `primary_ref_ids` floor (3 / 5 when ≥10 blobs or very_heavy) + borrow items covering refs.  
2. Portfolio — if inspiration paid and not direction_locked, always owe `inspiration_extract` (including redesign snapshot-first).  
3. `claim_ok` — blocked while `inspiration_extract` unpaid.  
4. VF inspiration — attach up to 8 session blobs + advisory “DIGEST”.  
5. Instructions — explicit digest contract.

## Still host-owned (by design)

Pixel judgment / “copy this sidebar exactly with tweaks” remains **host LOOK**. MCP forces the pixels + structured attestation + claim block — it will not silently OCR 16 JPEGs into a layout DSL inside the server.
