"""Invoke MCP handlers by execution tier without blocking the stdio event loop."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from navigation.execution_runtime.pool import get_executor
from navigation.execution_runtime.policies.cancellation import CancellationToken
from navigation.execution_runtime.policies.tier import ExecutionTier

HandlerFn = Callable[..., Awaitable[dict[str, Any]]]


async def invoke_handler(
    handler: HandlerFn,
    args: dict[str, Any],
    *,
    tier: ExecutionTier,
    cancellation: CancellationToken | None = None,
) -> dict[str, Any]:
    if cancellation is not None:
        cancellation.check()

    if tier == ExecutionTier.SYNC_FAST:
        return await handler(args)

    if tier == ExecutionTier.SYNC_OFFLOAD:
        loop = asyncio.get_running_loop()

        def _run_in_thread() -> dict[str, Any]:
            async def _coro() -> dict[str, Any]:
                return await handler(args)

            return asyncio.run(_coro())

        return await loop.run_in_executor(get_executor(), _run_in_thread)

    if tier == ExecutionTier.BACKGROUND:
        # Start/poll/cancel handlers enqueue or read the job store only.
        return await handler(args)

    raise ValueError(f"unsupported execution tier: {tier}")
