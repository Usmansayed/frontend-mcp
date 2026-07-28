# Inspiration gap fixes — research + ship notes

**Date:** 2026-07-27  
**Gaps addressed:** flaky live SS, thin specialists, search fallback, look-lock Phase 1

## Fixes shipped

| Gap | Fix |
|-----|-----|
| Live screenshots hang/WAF | `asyncio.wait_for` (~10s) on capture; `screenshot_url` block-detect + `ready_timeout=8` |
| Web live SS overrun | Same wait_for in `web_inspire` screenshot wave |
| Thin pricing/sidebar | Specialists: `saasframe`, `saasinterface`, `saaslandingpage`; wired `section_doc_pages` (Flowbite) |
| DDG-only search | `search_web()`: Serper → Brave → DuckDuckGo (env keys optional) |
| Collect ≠ direction | VF `look_lock` / `borrow` → `implement_from_borrow`; unpaid `inspiration_extract`; collect sets `direction_locked=false` |

## Spike (HTTP)

| Source | Result |
|--------|--------|
| saasframe.io | ~100ms, Webflow CDN — **pricing winner** |
| saasinterface.com | ~0.5s, many imgs — **sidebar** |
| saaslandingpage.com | ~0.5s — pricing backup |
| saaspo.com | 403 — skip |
| Flowbite docs | generic OG skipped; page imgs still used |

## Agent flow (after Phase 1)

```text
collect (level) → LOOK VF purpose=inspiration
  → fill borrow + look_lock + primary_ref_ids
  → next_actions: implement_from_borrow (not re-collect)
```

Env (optional): `SERPER_API_KEY`, `BRAVE_API_KEY`

## Still open

- Headed retry after bot_challenge
- Design VF `vs_inspiration` when refs bound
- Region crop for nav/pricing screenshots
