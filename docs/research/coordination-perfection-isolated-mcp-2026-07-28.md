# Isolated MCP test run — 2026-07-28

## Environment
- Sandbox: `http://127.0.0.1:18765`
- Package: `1.2.0.dev50` (local + MCP process after prior reload)

## Results

| Board | Result |
|-------|--------|
| `test_coordinator_card` + bootstrap | **34 passed** (after fixes) |
| Phase 2 obedience (6 intents) | **PASS 6/6** |
| Discoverability | **0.95** — 7/8 (only known fail: tool volume 73) |
| No-guide E2E | **BOARD PASS 4/4** |
| Live Cursor MCP health | reachable; skew=false |

## Bugs found → fixed

1. **Hotfix misclassified as feature** when lifecycle stamps `feature_incremental` but intent is `fix overlapping…`  
   - Cause: feature scope checked before hotfix cues  
   - Fix: hotfix cues/scope before feature; polish *text* cues before feature; polish *tier* only for design_driven/empty

2. **Feature empty owed jumped to verify** (skip observe)  
   - Fix: feature joins hotfix empty-owed climb → observe unless observe already paid

## Remaining (non-blocking)
- Tool catalog volume (73) — progressive discovery later (Phase 3-ish)
- Cursor MCP process must **reload** after this commit to pick up classify fixes in the live server
