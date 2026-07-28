# Inspiration — pick a level (search effort)

**Resource:** `perception://guide/inspiration`  
**Rule:** Look at the task. Pick **one** `inspiration_level`. That chooses **how hard we hunt**. It is **not** a hard cap on refs.

Works for **any grain**: full page, section (pricing/hero/footer), component (navbar/modal), or chrome (button/input).

- **Page** → landing galleries (OPL/Behance/…)  
- **Nav / footer / controls** → specialist pattern path first (`navbar.gallery`, `footer.design`, daisyUI CDN) — fast + relevant  
- **Fonts** → routed to Resource Intelligence (`perception_resource_font_search`), not gallery dump  

```text
collect({ query: "navbar with mega menu", inspiration_level: "standard" })
collect({ query: "saas landing page", inspiration_level: "standard" })
```

## How to think → choose

| Level | Choose when… | Search effort |
|-------|----------------|---------------|
| **light** | Look clear; quick pulse (page-scale) | HTTP galleries |
| **standard** | Default — page, section, or component | HTTP + scout when needed |
| **wide** | Want variety across many sites | Broader concurrent scout |
| **max** | Deep research / demos | Widest + optional browser |

Component/section/chrome queries auto-enable corpus scout even on light so you don't get false-green unrelated cards.

## Tools

1. `perception_inspiration_collect({ query, inspiration_level })`  
2. LOOK → `visual_feedback(purpose=inspiration)` borrow/ignore  
3. `perception_inspiration_session_end` when done  

Provider detail: `perception://inspiration-guide`
