"""Route claim validator."""
from __future__ import annotations

from pathlib import Path

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    CheckResult,
    ResolverKind,
    ResolverQuery,
    ValidationResult,
)
from navigation.resolver_intelligence.registry import ResolverRegistry


def validate_route_claim(claim: dict, ctx: ResolverContext) -> ValidationResult:
    route = str(claim.get("route") or "").strip()
    file_claim = str(claim.get("file") or "").strip()
    component_block = claim.get("component") or {}
    component_name = ""
    if isinstance(component_block, dict):
        component_name = str(component_block.get("name") or "").strip()
    elif isinstance(component_block, str):
        component_name = component_block.strip()

    checks: list[CheckResult] = []
    degraded: list[str] = []

    if not route:
        checks.append(CheckResult("route_present", False, "claim.route required"))
        return ValidationResult(valid=False, checks=checks, degraded=degraded)

    file_path = Path(file_claim) if file_claim else None
    if file_path and not file_path.is_absolute():
        file_path = ctx.repo_root / file_path
    file_exists = bool(file_path and file_path.is_file())
    checks.append(
        CheckResult(
            "file_exists",
            file_exists,
            str(file_path) if file_path else "claim.file missing",
        )
    )

    name_in_file = False
    if file_exists and component_name and file_path is not None:
        text = file_path.read_text(encoding="utf-8", errors="replace")[:50_000]
        name_in_file = component_name in text
    checks.append(
        CheckResult(
            "component_in_file",
            name_in_file,
            component_name or "claim.component.name missing",
        )
    )

    # Same dispatch as perception_resolve_route (Next App Router before RR v6).
    resolve_result = ResolverRegistry().resolve(
        ResolverQuery(kind=ResolverKind.ROUTE, params={"path": route}),
        ctx,
    )
    agrees = False
    if resolve_result.matches:
        for match in resolve_result.matches:
            if component_name and match.symbol == component_name:
                agrees = True
            if file_claim and match.file_path.replace("\\", "/").endswith(
                file_claim.replace("\\", "/").lstrip("./")
            ):
                agrees = True
        # File+route agreement: resolve found the claimed file even without symbol match.
        if not agrees and file_exists and file_claim:
            for match in resolve_result.matches:
                if match.file_path.replace("\\", "/").endswith(
                    file_claim.replace("\\", "/").lstrip("./")
                ):
                    agrees = True
                    break
    checks.append(
        CheckResult(
            "resolve_route_agrees",
            agrees,
            f"{resolve_result.resolver_id}:{resolve_result.status.value}",
        )
    )

    # When file exists + component in file, and resolve found the route under Next,
    # treat as valid even if symbol naming differs (page.tsx default export).
    if (
        not agrees
        and file_exists
        and (name_in_file or not component_name)
        and resolve_result.matches
        and "next" in str(resolve_result.resolver_id or "").lower()
    ):
        agrees = True
        checks[-1] = CheckResult(
            "resolve_route_agrees",
            True,
            f"{resolve_result.resolver_id}:file_route_aligned",
        )

    valid = all(c.passed for c in checks)
    # Prefer file+component checks: if those pass and resolve found next matches, valid.
    if file_exists and (name_in_file or not component_name) and resolve_result.matches and agrees:
        valid = True
    normalized = resolve_result.matches[0] if agrees and resolve_result.matches else None
    return ValidationResult(
        valid=valid,
        checks=checks,
        mcp_resolve=resolve_result,
        normalized_match=normalized,
        degraded=degraded,
    )
