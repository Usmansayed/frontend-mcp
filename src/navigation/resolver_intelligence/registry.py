"""Resolver plugin registry."""
from __future__ import annotations

import time
from typing import Any

from navigation.resolver_intelligence.context import ResolverContext
from navigation.resolver_intelligence.contracts import (
    ConfidenceLevel,
    FallbackHint,
    ResolverKind,
    ResolverQuery,
    ResolverResult,
    ResolverStatus,
)
from navigation.resolver_intelligence.plugins.api_endpoint import patterns as api_endpoint_plugin
from navigation.resolver_intelligence.plugins.component import resolve_component as resolve_component_plugin
from navigation.resolver_intelligence.plugins.design_token import resolve_design_token as resolve_design_token_plugin
from navigation.resolver_intelligence.plugins.layout import snapshot as layout_plugin
from navigation.resolver_intelligence.plugins.route import react_router_v6
from navigation.resolver_intelligence.plugins.state_owner import react_context as state_owner_plugin


class ResolverRegistry:
    def resolve(self, query: ResolverQuery, ctx: ResolverContext) -> ResolverResult:
        start = time.perf_counter()
        params = query.params

        if query.kind == ResolverKind.ROUTE:
            path = str(params.get("path") or params.get("route") or "").strip()
            if not path:
                return _error(query.kind, "path required", start)
            if react_router_v6.can_handle(ctx):
                return react_router_v6.resolve_route(path, ctx)
            return _unsupported(query.kind, start)

        if query.kind == ResolverKind.COMPONENT:
            name = str(params.get("name") or "").strip()
            return resolve_component_plugin(name, ctx)

        if query.kind == ResolverKind.DESIGN_TOKEN:
            token = str(params.get("token") or "").strip()
            return resolve_design_token_plugin(token, ctx)

        if query.kind == ResolverKind.STATE_OWNER:
            key = str(params.get("key") or "").strip()
            store_name = str(params.get("store_name") or "").strip()
            return state_owner_plugin.resolve_state_owner(key, ctx, store_name=store_name)

        if query.kind == ResolverKind.API_ENDPOINT:
            path = str(params.get("path") or "").strip()
            method = str(params.get("method") or "").strip()
            return api_endpoint_plugin.resolve_api_endpoint(path, ctx, method=method)

        if query.kind == ResolverKind.LAYOUT:
            snapshot = params.get("snapshot")
            if not snapshot:
                return _error(query.kind, "snapshot required", start)
            region = str(params.get("region") or "").strip()
            return layout_plugin.resolve_layout(snapshot, region=region)

        return _unsupported(query.kind, start)


def _error(kind: ResolverKind, message: str, start: float) -> ResolverResult:
    return ResolverResult(
        ok=False,
        kind=kind,
        status=ResolverStatus.ERROR,
        confidence=ConfidenceLevel.NONE,
        error=message,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )


def _unsupported(kind: ResolverKind, start: float) -> ResolverResult:
    return ResolverResult(
        ok=False,
        kind=kind,
        status=ResolverStatus.UNSUPPORTED,
        confidence=ConfidenceLevel.NONE,
        degraded=["no_resolver_plugin"],
        fallback=FallbackHint(
            strategy="host_search",
            message="No resolver plugin for this framework or kind.",
            suggested_tools=["perception_validate_route_claim"],
        ),
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
