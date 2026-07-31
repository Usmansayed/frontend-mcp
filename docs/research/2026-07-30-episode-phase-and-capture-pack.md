# Research + Plan: Episode Phase + Parallel Capture Pack

**Date:** 2026-07-30  
**Target version:** `1.2.0.dev62`  
**Status:** Implementing

## Decisions (narrow state space)

| Runtime switch | Values | Notes |
|----------------|--------|-------|
| Agent face | greenfield / redesign / feature / hotfix / forms | Existing |
| **Episode phase** (new) | `intent` → `flow` → `layout` → `sections` → `components` → `verify` → `ship` | Derived from unpaid pack + claim_extra — **not** 150 leaf states |
| Evidence band | light…very_heavy | Existing |
| Surface | landing / dashboard / … | Existing |

150-state corpus stays research-only (Report 08 freeze).

## Parallelism strategy

| Work | Approach |
|------|----------|
| Inspiration / resources / components | Episode HTTP prefetch (boost: medium+ greenfield/redesign; longer hard budget for multi-category kit) |
| Full + viewport + multi-section visuals | **One observe call** → `capture_design_evidence` pack (sequential shots on primary browser — already fast enough; no multi-Chromium default) |
| Browser tools | Keep flight lock; pack APIs replace parallel MCP observe calls |

## Ship slice (this change)

1. `card.phase` + `phase_hint`  
2. `perception_observe` / `navigate_and_observe`: `screenshot_pack`, `focus_sections`, `max_sections`, `section_id`  
3. Live DOM region probe when snapshot regions missing  
4. Prefetch: include `medium` band for creative classes; hard budget default 8s  
5. Tests + version

## Non-goals

- Required local LLM  
- Default isolated browser pool  
- Exposing leaf state IDs on the card  
