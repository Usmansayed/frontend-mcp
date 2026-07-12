# SEO Intelligence — Local Browser OAuth

## On-demand auth flow

OAuth runs only when the user requests analysis that needs provider data — not during initial setup.

```text
# Initial setup (no browser)
perception_seo_connect { "website_url": "https://example.com" }
  → site registered → SEO Intelligence ready

# When user requests Search Console / GA4 analysis
perception_seo_connect { "website_url": "https://example.com", "action": "connect_google" }
  → browser opens → Google sign-in
  → http://localhost:8787/google/callback receives code
  → tokens stored in .cache/
  → GSC / GA4 auto-discovered

# When user requests Bing analysis
perception_seo_connect { "website_url": "https://example.com", "provider": "bing", "action": "connect_bing" }
  → browser opens → Microsoft sign-in
  → http://localhost:8787/bing/callback receives code
  → tokens stored → Bing sites auto-discovered
```

No manual authorization code copying. No API key pasting unless Bing OAuth client is not configured.

## Operator setup (once)

### Google Cloud

1. Create OAuth Desktop client.
2. Add authorized redirect URI: `http://localhost:8787/google/callback`
3. Enable APIs: Search Console, Analytics Data, **Analytics Admin**
4. Set in `.env`:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`

### Bing Webmaster

1. Bing Webmaster Tools → Settings → API Access → OAuth Client
2. Register redirect URI: `http://localhost:8787/bing/callback`
3. Set in `.env`:
   - `BING_WEBMASTER_OAUTH_CLIENT_ID`
   - `BING_WEBMASTER_OAUTH_CLIENT_SECRET`

## MCP calls

```text
# Register website (default action=setup)
perception_seo_connect { "website_url": "https://example.com" }

# Connect Google on demand
perception_seo_connect { "website_url": "https://example.com", "action": "connect_google" }

# Connect Bing on demand (only when user wants Bing data)
perception_seo_connect { "website_url": "https://example.com", "provider": "bing", "action": "connect_bing" }
```

## Internal components

| Module | Role |
|--------|------|
| `auth/local_server.py` | Temporary localhost callback server |
| `auth/connect.py` | `connect_google()`, `connect_bing()` browser workflows |
| `auth/google.py` | Token storage + refresh + GSC/GA4 APIs |
| `auth/bing.py` | Token storage + refresh + Bing Webmaster APIs |
| `setup/auth_requirements.py` | Maps intents → required OAuth; `auth_required` on audit |

## Configuration

| Variable | Default |
|----------|---------|
| `SEO_OAUTH_CALLBACK_PORT` | `8787` |
| `SEO_OAUTH_CALLBACK_HOST` | `127.0.0.1` |
| `SEO_OAUTH_CALLBACK_TIMEOUT_S` | `300` |
| `SEO_GOOGLE_TOKEN_PATH` | `.cache/seo_google_tokens.json` |
| `SEO_BING_TOKEN_PATH` | `.cache/seo_bing_tokens.json` |

Set `interactive=false` on `perception_seo_connect` to return `authorization_url` only (headless/CI).

## Token storage

Development: JSON files under `.cache/`. Future: OS credential store (Windows Credential Manager, macOS Keychain, Linux Secret Service).
