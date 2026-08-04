# Inspiration flexibility — honest production status

**Date:** 2026-07-27

## Verdict

**Not perfect. Not “production-grade for anything” yet.**  
**Usable now for page-scale landing/dashboard-style asks. Improving for section/component/chrome.**

| Ask type | Example | Status |
|----------|---------|--------|
| Full page | `saas landing page` | **Strong** — HTTP galleries match well, fast |
| Section | `pricing section cards` | **Partial** — rewrite + scout; gallery titles often still page-level |
| Component | `navbar with mega menu` | **Partial** — scope/rewrite/relevance filter shipped; sources often lack labeled nav crops |
| Chrome | `primary button hover` | **Weak** — need pattern/showcase sources with control-level previews |
| Smart “when to use inspiration for small polish” | — | **Later** (routing policy) |

## What was wrong (measured)

Same three One Page Love titles (`PP Neue Montreal`, …) returned for navbar, modal, button, pricing — **false green**: fast `ok` with irrelevant cards because soft-stop counted any 3 image URLs.

## What we shipped toward “anything”

1. **Query scope** — `page | section | component | chrome` (`query_flex.py`)  
2. **Hunt rewrite** — e.g. navbar → `website navigation header menu ui design`  
3. **Relevance soft-stop** — stop only when hits match the ask  
4. **Filter + rank** — fine-grain scopes drop junk cards (keep ≤2 weak bootstrap), rank by score  
5. **Auto scout** for non-page scopes even on light  
6. **Taxonomy** — `navigation` intent + broader section/component rules  

## Remaining gaps (to be truly robust)

1. **Sources** — Collect UI / Mobbin / Refero / component showcase **deep pages** (not homepage dumps) for nav/modal/button  
2. **Provider search quality** — Behance/Dribbble-quality text search for components; OPL genres are page-biased  
3. **Crop / region** — optional viewport focus on header/nav when screenshotting demos  
4. **Agent policy** — when polish should call inspiration vs skip (later, as you said)

## Agent guidance (now)

```text
# any grain — same tool
collect({ query: "navbar with mega menu", inspiration_level: "standard" })
collect({ query: "saas landing page", inspiration_level: "standard" })
```

Prefer **standard/wide** for component/section. Treat returned pack critically: LOOK + borrow/ignore. Empty or weak relevance → widen level or rephrase query — don’t invent UI from junk cards.
