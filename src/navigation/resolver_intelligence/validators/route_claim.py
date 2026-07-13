"""Route claim validator."""
from __future__ import annotations

from pathlib import Path

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import CheckResult, ValidationResult
from navigation.resolver_intelligence.plugins.route import react_router_v6


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

    resolve_result = react_router_v6.resolve_route(route, ctx)
    agrees = False
    if resolve_result.matches:
        for match in resolve_result.matches:
            if component_name and match.symbol == component_name:
                agrees = True
            if file_claim and match.file_path.replace("\\", "/").endswith(
                file_claim.replace("\\", "/").lstrip("./")
            ):
                agrees = True
    checks.append(
        CheckResult(
            "resolve_route_agrees",
            agrees,
            resolve_result.status.value,
        )
    )

    valid = all(c.passed for c in checks)
    normalized = resolve_result.matches[0] if agrees and resolve_result.matches else None
    return ValidationResult(
        valid=valid,
        checks=checks,
        mcp_resolve=resolve_result,
        normalized_match=normalized,
        degraded=degraded,
    )
