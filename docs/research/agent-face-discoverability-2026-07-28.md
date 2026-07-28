# Agent-face discoverability audit — findings

**Date:** 2026-07-28  
**Branch code:** `exp/agent-face-simple`  
**Script:** `scripts/eval_agent_face_discoverability.py`  
**Raw:** `docs/research/agent_face_discoverability.json`

## Honest answer

**No — before this audit we had not tested full-MCP accessibility.**  
We had unit tests for `agent_summary.card`. That is not the same as “can an agent figure out when/how to use the tools?”

This pass evaluated discoverability from the **running Cursor MCP** plus **in-repo face code**.

---

## Verdict: **USABLE_WITH_GAPS** (in-repo face **0.95** / 7 of 8 checks; live Cursor MCP still stale)

| Layer | Easy enough? | Notes |
|-------|--------------|-------|
| Always-on spine (repo rule + new instructions) | **Yes** | ~449 words; clear bootstrap → card → owed → verify |
| Spines in repo | **Yes** | 5 short spines (~33–52 words), each names tools |
| Live MCP instructions (Cursor process) | **No — stale** | Still serves the **old long** preamble (`coordinator` / `recommended_next`, not `card`) |
| Live resources | **No — stale** | `perception://getting-started` is old; `perception://spine/greenfield` → **not found** |
| Tool descriptions (live) | **Yes** | Core: when=100%, how=67%, length=100% (`Does` / `Use when` / `Next`) |
| Tool volume | **Hard** | **~73 tools** — agents drown unless they follow `card.next` |
| In-process card after bootstrap | **Yes** | greenfield → inspiration; redesign → snapshot; hotfix → observe |

Remaining fail: tool volume only (by design until progressive discovery).

---

## What is easy (when the new face is actually loaded)

1. **When to use MCP** — rule + instructions: UI/CSS/design/forms → bootstrap first.  
2. **What to call next** — `agent_summary.card.next` + `owed` (simulated envelopes work).  
3. **Class path** — five spines name concrete `perception_*` tools.  
4. **Core tool blurbs** — e.g. health: “FIRST call… before planning”; verify: “after every UI action… data.verified”.

## What is still hard / broken for real agents right now

1. **MCP server not restarted** — Cursor still injects the old long `serverDescription` and old resources. Until reload, agents never see `card` / spines.  
2. **75-tool haystack** — even with good blurbs, browsing tools/list is not how agents should choose; they must trust `card.next`.  
3. **Hotfix classification** — intent “fix overlapping mobile menu button” became `class=feature` and suggested inspiration (wrong).  
4. **Dual contracts** — live preamble still says read `coordinator`; repo rule says read `card`. Agents will get mixed signals until MCP reload.  
5. **No end-to-end UI task A/B yet** — discoverability ≠ workflow adherence on a real landing/hotfix.

---

## Tool “when/how” sample (live descriptions — good)

| Tool | When/how cue |
|------|----------------|
| `perception_health` | “FIRST call of any UI… before planning”; needs `intent` |
| `perception_inspiration_collect` | “design direction unresolved… high ROI” |
| `perception_verify` | “after every UI action”; `data.verified` ≠ transport ok |

So: **individual tools are fairly self-describing.** The problem is **orchestration discoverability** (which of 75, in what order) — exactly what `card` is meant to fix, once the live server loads it.

---

## Required before claiming “easy to use”

1. **Restart / reload Frontend MCP** in Cursor so instructions + resources match `exp/agent-face-simple`.  
2. Re-fetch `perception://getting-started` and confirm it mentions `agent_summary.card`.  
3. Fix hotfix classification in `classify_agent_face`.  
4. Run one real greenfield + one hotfix chat and score: bootstrap? followed `card.next`? verify before claim?

Until (1), the experiment face exists in git but **is not what agents are using**.
