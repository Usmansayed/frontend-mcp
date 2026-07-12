# SEO Intelligence — Authentication & Onboarding

## User experience (minimal friction)

```text
Initial setup: Website URL only → SEO Intelligence ready

User requests Search Console / GA4 analysis → Connect Google (OAuth) → tokens stored → never ask again

User requests Bing analysis → Connect Bing Webmaster (OAuth) → tokens stored → never ask again
```

The MCP auto-configures Search Console, GA4, LibreCrawl, Lighthouse, and Browser Intelligence after providers are connected. Users never enter property IDs or service URLs.

### MCP flow

```text
# Initial setup (no OAuth)
perception_seo_connect { "website_url": "https://example.com" }
  → site registered → ready

# On-demand Google (when user requests GSC/GA4 analysis)
perception_seo_connect { "website_url": "https://example.com", "action": "connect_google" }
  → browser opens → Google sign-in → localhost callback → tokens saved

# On-demand Bing (only when user requests Bing analysis)
perception_seo_connect { "website_url": "https://example.com", "provider": "bing", "action": "connect_bing" }
  → browser opens → Microsoft sign-in → localhost callback → tokens saved

# Audit — full audit works without Google; provider-specific intents return auth_required when needed
perception_seo_audit { "website_url": "https://example.com" }
perception_seo_audit { "website_url": "https://example.com", "intents": ["search_queries"] }
```

See `LOCAL_OAUTH.md` for operator redirect URI registration.

## Principles

- **On-demand OAuth** — never prompt during initial setup
- **User-owned data** for Search Console and GA4 via OAuth
- Tokens and site profiles stored locally — never in repo
- MCP does not host a shared SEO API key pool
- Bundled LibreCrawl used automatically in dev

## Operator configuration (once per deployment)

Copy `.env.example` → `.env` at the repo root. The MCP server loads it on startup.

| Variable | Purpose |
|----------|---------|
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud OAuth client |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google Cloud OAuth secret |
| `BING_WEBMASTER_OAUTH_CLIENT_ID` | Bing Webmaster OAuth client (optional) |
| `BING_WEBMASTER_OAUTH_CLIENT_SECRET` | Bing Webmaster OAuth secret (optional) |
| `BING_WEBMASTER_OAUTH_REDIRECT_URI` | Default `http://localhost:8787/bing/callback` |
| `GOOGLE_OAUTH_REDIRECT_URI` | Default `http://localhost:8787/google/callback` |
| `SEO_OAUTH_CALLBACK_PORT` | Local callback port (default `8787`) |

Optional operator overrides (users never see these):

| Variable | Purpose |
|----------|---------|
| `LIBRECRAWL_BASE_URL` | Override bundled LibreCrawl (`http://localhost:5001`) |
| `SEO_GOOGLE_TOKEN_PATH` | Token file path (default `.cache/seo_google_tokens.json`) |
| `SEO_CACHE_DIR` | Cache root for tokens + site profiles |

Enable Google APIs: Search Console API, Google Analytics Data API, **Google Analytics Admin API** (for GA4 auto-discovery).

## Advanced overrides (discovery failure only)

Pass these on `perception_seo_audit` only when auto-discovery could not match a property:

| Param | When |
|-------|------|
| `property_url` | GSC property override |
| `ga4_property_id` | GA4 property override |
| `bing_site_url` | Bing site override |

## Bing Webmaster (optional, on-demand only)

| Item | Value |
|------|-------|
| When | User explicitly requests Bing data or Bing-specific analysis |
| Connect | `perception_seo_connect` with `action=connect_bing` |
| OAuth | Operator registers client in Bing Webmaster → API Access |
| API key | User passes `api_key` once at connect (stored locally, not in `.env`) |
| Site discovery | Auto-matched from `GetUserSites` after connect |
| Token storage | `.cache/seo_bing_tokens.json` |

Bing is **not** surfaced during onboarding.

## Google (Search Console + GA4)

| Item | Value |
|------|-------|
| When | User requests Search Console, GA4, or related analysis |
| Flow | OAuth 2.0 authorization code |
| Scopes (GSC) | `https://www.googleapis.com/auth/webmasters.readonly` |
| Scopes (GA4) | `https://www.googleapis.com/auth/analytics.readonly` |
| Token storage | `.cache/seo_google_tokens.json` |
| Site profiles | `.cache/seo_sites.json` |

## LibreCrawl

Bundled at `http://localhost:5001` by default. Auto-started before audits — see `COMPANION_SERVICES.md`.

## Lighthouse / PageSpeed

Local Lighthouse CLI (no key) or optional `PAGESPEED_API_KEY` for PSI API.

## Browser Intelligence

No separate auth — pass `scan_id` from `perception_observe`.
