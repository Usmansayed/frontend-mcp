# Community Duplication — Research Report

**Date:** 2026-07-11  
**Method:** Browser Intelligence + Playwright network capture + endpoint probing

---

## Executive summary

Community templates use **`content_id`** (numeric Community file ID). REST **`file_key`** (22-char) only exists **after** duplication into the user's Drafts.

| Stage | Mechanism |
|-------|-----------|
| Discovery | `GET /api/search/resources` → `content_id` |
| Duplication (API) | `POST /api/hub_files/{content_id}/duplicate` (session cookies) |
| Duplication (UI) | Click `[data-testid="community-duplicate-button"]` → Open in Figma |
| file_key available | After duplicate completes → URL `https://www.figma.com/design/{file_key}/…` |
| Deep extraction | Official REST `GET /v1/files/{file_key}` with PAT |

**No public REST API duplicates Community files with PAT alone.** Session cookies or authenticated browser required.

---

## UI flow (observed)

```text
1. User on /community/file/{content_id}/{slug}
2. Page loads hub_files metadata:
     GET /api/resources/hub_files/{content_id}?include_full_category=true
3. User clicks "Open in Figma" (data-testid=community-duplicate-button)
4. If unauthenticated → login modal / no navigation (observed in research session)
5. If authenticated:
     a. POST /api/hub_files/{content_id}/duplicate  (403 without cookies; endpoint exists)
     b. Browser navigates to figma.com/design/{file_key}/{name}
     c. Copy appended "(Community)" in Drafts per Figma docs
6. file_key parseable from design URL immediately
```

---

## Network sequence

| Step | Request | Auth | Notes |
|------|---------|------|-------|
| Page load | `GET /api/resources/hub_files/{content_id}` | WAF session | Rich metadata, no file_key |
| Duplicate click | `POST /api/hub_files/{content_id}/duplicate` | **Cookies required** | Returns new file metadata |
| Alternate | `POST /api/resources/hub_files/{content_id}/duplicate` | Cookies | Also 403 unauthenticated |
| Editor open | Navigation to `/design/{file_key}/…` | Cookies | Primary file_key source |
| Embed preview | `GET embed.figma.com/community/file/{content_id}/canvas` | Session | Preview only, not extraction |

Probed non-viable paths:
- `/community/file/{id}/duplicate` → redirects back (no op when logged out)
- `/file/{content_id}/duplicate` → 404 (content_id ≠ file_key)

---

## file_key extraction

**Preferred:** parse from post-duplication URL:

```text
https://www.figma.com/design/AbCdEf123456/Title
                         ^^^^^^^^^^^^
                         file_key
```

**Fallback:** parse duplicate API JSON (`meta.key`, `meta.file_key`, embedded design URLs).

Implementation: `community_duplication/file_key_resolver.py`

---

## Official API (post-duplication)

With PAT (`file_content:read`, optionally `file_variables:read`):

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/files/{file_key}` | Document tree, components, styles |
| `GET /v1/files/{file_key}/variables/local` | Variables (Enterprise scope) |

From this point the file is a **normal owned Draft** — no Community pages required.

---

## Pipeline architecture

```text
CommunityDuplicationOrchestrator
  ├─ duplicate_via_session_api()     # POST hub_files/duplicate + cookies
  ├─ CommunityDuplicationBrowser     # Playwright fallback
  ├─ file_key_resolver               # URL + JSON parsing
  ├─ FigmaRestClient / load_official_file()
  └─ build_design_snapshot()
```

**Separate from:** Community Discovery, Figma Console MCP, Selection Planner.

---

## Authentication requirements

| Credential | Discovery | Duplicate | REST extract |
|------------|-----------|-----------|--------------|
| None | Search API only | No | No |
| `FIGMA_SESSION_COOKIE` | hub_files detail | **Yes (API path)** | No |
| Browser login | Yes | **Yes (UI path)** | No |
| `figma_pat` / PAT | No | No | **Yes** |

Env vars:
- `figma_pat` — REST extraction
- `FIGMA_SESSION_COOKIE` — optional API duplication shortcut
- `FIGMA_PIPELINE_FILE_KEY` — skip duplication if file already in Drafts

---

## Browser Intelligence gaps (addressed in pipeline)

1. WAF bootstrap wait (8s) before interact
2. Network listener on `hub_files/*/duplicate` responses
3. Parallel wait: main-frame navigation + popup tab
4. Login wall detection → clear `browser_login_required` degraded flag
5. Playwright used for duplication research; **production pipeline uses browser_use** (Browser Intelligence stack)

---

## POC

```powershell
python scripts/run_community_duplication_poc.py
```

Requires `figma_pat` and either `FIGMA_SESSION_COOKIE` or interactive browser login for duplication.
