# Companion Services

LibreCrawl is a **core platform service** for technical crawl evidence. It runs as a native background process — no Docker required.

## Lifecycle

```text
perception_seo_audit
  → health check LibreCrawl (localhost:5001)
  → start native process if unhealthy
  → wait until healthy
  → collect technical crawl evidence
```

## Service

| Service | Default URL | Runtime |
|---------|-------------|---------|
| LibreCrawl | `http://localhost:5001` | Python + Playwright |

## First-run setup

On first audit, the companion manager:

1. Clones LibreCrawl from GitHub into `.cache/companions/LibreCrawl`
2. Creates a Python venv and installs requirements
3. Installs Playwright Chromium
4. Starts the crawl API on the configured port

## Requirements

| Dependency | Used for |
|------------|----------|
| **Git** | Clone LibreCrawl |
| **Python 3.10+** | LibreCrawl venv |

## Configuration

| Variable | Purpose |
|----------|---------|
| `LIBRECRAWL_BASE_URL` | Override LibreCrawl URL |
| `LIBRECRAWL_PORT` | Bind port (default 5001) |
| `LIBRECRAWL_ROOT` | Use existing LibreCrawl checkout |
| `SEO_COMPANIONS_AUTO_START` | `false` to disable auto-start |
| `SEO_SKIP_COMPANION_BOOTSTRAP` | `1` to skip bootstrap in tests |
| `SEO_COMPANIONS_START_TIMEOUT_S` | Health wait timeout |

## Logs

| Path | Content |
|------|---------|
| `.cache/companions/logs/librecrawl.log` | LibreCrawl stdout/stderr |

## Common degraded notes

- `git_not_found:install_git_for_companion_setup`
- `librecrawl_pip_failed:exit_*`
- `companion_unhealthy:librecrawl:librecrawl_unreachable`

## Relationship to SEO Intelligence

LibreCrawl supplies **technical crawl evidence** — canonicals, redirects, broken links, schema, internal links. SEO reasoning happens in the recommendation engine, not in LibreCrawl.
