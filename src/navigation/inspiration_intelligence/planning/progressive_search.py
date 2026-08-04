"""Deterministic progressive inspiration search — quality over quantity.

Soft-stop when a usable image pack exists (latency). Not a hard ref quota —
levels and target_refs only hint when hunting may stop early.
"""
from __future__ import annotations

import re
from typing import Any

# Soft defaults when caller does not pass target/min (levels override in collect).
TARGET_IMAGE_REFS = 8
MIN_IMAGE_REFS = 3

# Anti-bot-friendly HTTP/CDN sources — default MCP happy path (no Chromium).
# land-book stays registered for explicit pin only — not in default cascades.
FAST_HTTP_PROVIDER_ORDER: list[str] = [
    "onepagelove",
    "lapa",
    "behance",
    "httpster",
]

# Full cascade — browser-heavy galleries only after HTTP sources (or explicit provider_ids).
IMAGE_FIRST_PROVIDER_ORDER: list[str] = [
    "onepagelove",
    "lapa",
    "behance",
    "httpster",
    "dribbble",
    "awwwards",
    "siteinspire",
    "godly",
]


def resolve_collect_provider_order(
    provider_ids: list[str] | None = None,
    *,
    fast: bool | None = None,
) -> list[str]:
    """Prefer HTTP-friendly sources unless the caller pins provider_ids."""
    if provider_ids:
        return list(provider_ids)
    if fast is None:
        from navigation.inspiration_intelligence.browser.policy import is_fast_mode

        fast = is_fast_mode()
    if fast:
        return list(FAST_HTTP_PROVIDER_ORDER)
    return list(IMAGE_FIRST_PROVIDER_ORDER)


def progressive_queries(seed: str, *, max_queries: int = 5) -> list[str]:
    """Expand seed into a short ordered ladder. Stop expanding when callers have enough hits."""
    raw = re.sub(r"\s+", " ", (seed or "").strip())
    if not raw:
        return []

    low = raw.lower()
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        norm = re.sub(r"\s+", " ", q.strip().lower())
        if not norm or norm in seen or len(queries) >= max_queries:
            return
        seen.add(norm)
        queries.append(q.strip())

    # Pass 1 — primary intent (exact + ui/interface variants)
    add(raw)
    if "ui" not in low and "dashboard" in low:
        add(f"{raw} ui")
    if "interface" not in low and ("dashboard" in low or "admin" in low):
        add(f"{raw.replace(' dashboard', '')} interface".strip())
    if "dashboard" in low and "analytics" in low:
        add("analytics dashboard interface")
        add("admin dashboard ui")
    elif "dashboard" in low:
        add("admin dashboard ui")
        add("dashboard design")
    elif "landing" in low:
        add(f"{raw} page design")
        add("saas landing page ui")
    elif "login" in low or "sign in" in low:
        add("login page ui")
        add("auth form interface")
    else:
        # Generic expansion
        add(f"{raw} ui")
        add(f"{raw} interface")

    # Pass 2 — broader only if ladder still short
    if len(queries) < 3:
        add("admin panel ui")
        add("crm dashboard")
        add("dashboard design")

    return queries[:max_queries]


def has_enough_image_refs(
    hits: list[dict[str, Any]] | list[Any],
    *,
    min_refs: int = MIN_IMAGE_REFS,
    target_refs: int = TARGET_IMAGE_REFS,
) -> bool:
    """True when we have enough HTTP/CDN (or local) image URLs for host vision."""
    count = image_ref_count(hits)
    if count >= target_refs:
        return True
    return count >= min_refs


def count_relevant_image_refs(
    hits: list[dict[str, Any]] | list[Any],
    *,
    query: str,
    search_query: str = '',
    min_score: float = 0.18,
) -> int:
    """Count refs that both have a preview and match the ask (anti false-green)."""
    from navigation.inspiration_intelligence.query_flex import is_relevant_hit

    n = 0
    for hit in hits:
        if isinstance(hit, dict):
            preview = str(hit.get("preview_url") or "")
            title = str(hit.get("title") or "")
            url = str(hit.get("url") or "")
        else:
            preview = str(getattr(hit, "preview_url", "") or "")
            title = str(getattr(hit, "title", "") or "")
            url = str(getattr(hit, "url", "") or "")
        if not (preview.startswith("http") or preview.startswith("file:")):
            continue
        if is_relevant_hit(
            query, title=title, url=url, search_query=search_query, min_score=min_score
        ):
            n += 1
    return n


def has_enough_relevant_refs(
    hits: list[dict[str, Any]] | list[Any],
    *,
    query: str,
    search_query: str = '',
    min_refs: int = MIN_IMAGE_REFS,
    target_refs: int = TARGET_IMAGE_REFS,
    min_score: float = 0.18,
) -> bool:
    """Soft-stop only when the pack is usable *for this query* — not any 3 random cards."""
    n = count_relevant_image_refs(
        hits, query=query, search_query=search_query, min_score=min_score
    )
    if n >= target_refs:
        return True
    return n >= min_refs


def image_ref_count(hits: list[dict[str, Any]] | list[Any]) -> int:
    n = 0
    for hit in hits:
        if isinstance(hit, dict):
            preview = str(hit.get("preview_url") or "")
        else:
            preview = str(getattr(hit, "preview_url", "") or "")
        if preview.startswith("http") or preview.startswith("file:"):
            n += 1
    return n
