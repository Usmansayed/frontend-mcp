"""Resolver Intelligence service facade."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from navigation.resolver_intelligence.context import ResolverContext, build_resolver_context
from navigation.resolver_intelligence.contracts import (
    ResolverKind,
    ResolverQuery,
    ResolverResult,
    ValidationResult,
)
from navigation.resolver_intelligence.live.correlate import correlate_live
from navigation.resolver_intelligence.registry import ResolverRegistry
from navigation.resolver_intelligence.validators.component_claim import validate_component_claim
from navigation.resolver_intelligence.validators.route_claim import validate_route_claim


class ResolverIntelligenceService:
    def __init__(self, registry: ResolverRegistry | None = None) -> None:
        self._registry = registry or ResolverRegistry()

    def build_context(self, repo_root: Path) -> ResolverContext:
        return build_resolver_context(repo_root)

    def _resolve(
        self,
        kind: ResolverKind,
        repo_root: Path,
        params: dict[str, Any],
        *,
        hints: dict[str, Any] | None = None,
    ) -> ResolverResult:
        ctx = self.build_context(repo_root)
        query = ResolverQuery(kind=kind, params=params, hints=dict(hints or {}))
        return self._registry.resolve(query, ctx)

    def resolve_route(self, repo_root: Path, path: str, *, hints: dict[str, Any] | None = None) -> ResolverResult:
        return self._resolve(ResolverKind.ROUTE, repo_root, {"path": path}, hints=hints)

    def resolve_component(self, repo_root: Path, name: str, *, hints: dict[str, Any] | None = None) -> ResolverResult:
        return self._resolve(ResolverKind.COMPONENT, repo_root, {"name": name}, hints=hints)

    def resolve_design_token(self, repo_root: Path, token: str, *, hints: dict[str, Any] | None = None) -> ResolverResult:
        return self._resolve(ResolverKind.DESIGN_TOKEN, repo_root, {"token": token}, hints=hints)

    def resolve_state_owner(
        self,
        repo_root: Path,
        *,
        key: str = "",
        store_name: str = "",
        hints: dict[str, Any] | None = None,
    ) -> ResolverResult:
        return self._resolve(
            ResolverKind.STATE_OWNER,
            repo_root,
            {"key": key, "store_name": store_name},
            hints=hints,
        )

    def resolve_api_endpoint(
        self,
        repo_root: Path,
        path: str,
        *,
        method: str = "",
        hints: dict[str, Any] | None = None,
    ) -> ResolverResult:
        return self._resolve(
            ResolverKind.API_ENDPOINT,
            repo_root,
            {"path": path, "method": method},
            hints=hints,
        )

    def resolve_layout(self, snapshot: dict[str, Any], *, region: str = "") -> ResolverResult:
        return self._registry.resolve(
            ResolverQuery(
                kind=ResolverKind.LAYOUT,
                params={"snapshot": snapshot, "region": region},
            ),
            build_resolver_context(Path(".")),
        )

    def validate_route_claim(self, repo_root: Path, claim: dict[str, Any]) -> ValidationResult:
        ctx = self.build_context(repo_root)
        return validate_route_claim(claim, ctx)

    def validate_component_claim(self, repo_root: Path, claim: dict[str, Any]) -> ValidationResult:
        ctx = self.build_context(repo_root)
        return validate_component_claim(claim, ctx)

    def correlate_live(
        self,
        scan: dict[str, Any],
        *,
        resolution: dict[str, Any] | None = None,
        claim: dict[str, Any] | None = None,
    ) -> ResolverResult:
        return correlate_live(scan, resolution=resolution, claim=claim)
