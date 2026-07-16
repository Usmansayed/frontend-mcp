"""Deterministic progressive inspiration search — quality over quantity.

Target: 3–5 high-quality image references, stop as soon as enough evidence exists.
"""
from __future__ import annotations

import re
from typing import Any

# Soft target for host vision — enough to orient, not a gallery dump.
TARGET_IMAGE_REFS = 5
MIN_IMAGE_REFS = 3

# HTTP-friendly providers first (no Chromium for discovery when possible).
IMAGE_FIRST_PROVIDER_ORDER: list[str] = [
    "behance",
    "onepagelove",
    "dribbble",
    "awwwards",
    "siteinspire",
    "godly",
    "land-book",
]


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
