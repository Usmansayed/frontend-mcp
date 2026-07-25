"""Deterministic progressive inspiration search — quality over quantity.

Target: 3–5 high-quality image references, stop as soon as enough evidence exists.
"""
from __future__ import annotations

import re
from typing import Any

# Soft target for host vision — enough to orient, not a gallery dump.
TARGET_IMAGE_REFS = 5
MIN_IMAGE_REFS = 3

# Anti-bot-friendly HTTP/CDN sources — default MCP happy path (no Chromium).
# land-book stays registered for explicit pin only — not in default cascades.
FAST_HTTP_PROVIDER_ORDER: list[str] = [
    "onepagelove",
    "lapa",
    "behance",
    "httpster",
    "siteinspire",
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
    count = 0
    for hit in hits:
        preview = ""
        if isinstance(hit, dict):
            preview = str(hit.get("preview_url") or hit.get("inspiration_blob") or "")
        else:
            preview = str(getattr(hit, "preview_url", "") or getattr(hit, "inspiration_blob", "") or "")
        if preview.startswith("http") or preview.startswith("file:") or preview.endswith((".jpg", ".jpeg", ".png", ".webp")):
            count += 1
        if count >= target_refs:
            return True
    return count >= min_refs


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
