# SEO Intelligence — Authentication

## Principles

- **User-owned data only** for Search Console and GA4
- OAuth tokens stored locally — never in repo
- MCP does not host a shared SEO API key pool

## Google (Search Console + GA4)

| Item | Value |
|------|-------|
| Flow | OAuth 2.0 authorization code |
| Scopes (GSC) | `https://www.googleapis.com/auth/webmasters.readonly` |
| Scopes (GA4) | `https://www.googleapis.com/auth/analytics.readonly` |
| Token storage | `SEO_GOOGLE_TOKEN_PATH` (default `.cache/seo_google_tokens.json`) |
| Client config | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` |

Phase 1 ships `perception_seo_connect` for Google OAuth (Search Console + GA4).

## LibreCrawl

| Item | Value |
|------|-------|
| Auth | None (local/self-hosted) |
| Config | `LIBRECRAWL_BASE_URL` |

## Lighthouse / PageSpeed

| Item | Value |
|------|-------|
| Local | Lighthouse CLI via subprocess (no key) |
| Remote | `PAGESPEED_API_KEY` for PSI API (optional, quota limits) |

## Bing Webmaster (optional)

| Item | Value |
|------|-------|
| Auth | API key |
| Config | `BING_WEBMASTER_API_KEY` |

## Browser Intelligence

No separate auth — requires `scan_id` from `perception_observe` / `perception_navigate_and_observe`.

## OpenSEO (optional)

| Item | Value |
|------|-------|
| Instance | `OPENSEO_BASE_URL` or `OPENSEO_MCP_URL` (e.g. `http://localhost:3001/mcp`) |
| DataForSEO | Configured on **OpenSEO instance** `.env` — not in MCP by default |
| Paid gate | `allow_paid_providers` on `perception_seo_audit` |
| Opt-out | `allow_openseo=false` |

See `OPENSEO_PROVIDER.md`.
