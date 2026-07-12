"""Tool executor — invoke MCP handlers with reliability, idempotency, and observability."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from navigation.coordination_intelligence.integration.bridge import process_tool_envelope
from navigation.coordination_intelligence.models import CompiledStep
from navigation.execution_runtime.dispatch_registry import DispatchRegistry
from navigation.execution_runtime.idempotency import (
    IdempotencyEntry,
    compute_idempotency_key,
)
from navigation.execution_runtime.ledger import ExecutionLedger
from navigation.execution_runtime.models import (
    CompiledExecutionResult,
    ExecutionMetadata,
    ExecutionRecord,
    ExecutionResult,
    _new_execution_id,
    attach_execution_metadata,
)
from navigation.execution_runtime.observability import ExecutionTraceEvent
from navigation.execution_runtime.policies.config import ExecutionPolicies
from navigation.execution_runtime.policies.failures import FailureClass, classify_failure
from navigation.execution_runtime.policies.recovery import evaluate_recovery
from navigation.execution_runtime.policies.retry import RetryDecision, evaluate_retry

logger = logging.getLogger(__name__)


def _normalize_compiled_step(
    compiled_step: CompiledStep | dict[str, Any],
) -> tuple[str | None, str | None, str | None, str | None, list[dict[str, Any]]]:
    if isinstance(compiled_step, CompiledStep):
        return (
            compiled_step.capability_id,
            compiled_step.semantic_action,
            compiled_step.step_id,
            compiled_step.playbook_id,
            list(compiled_step.tools),
        )
    return (
        compiled_step.get("capability_id"),
        compiled_step.get("semantic_action"),
        compiled_step.get("step_id"),
        compiled_step.get("playbook_id"),
        list(compiled_step.get("tools") or []),
    )


def _episode_id_from_envelope(envelope: dict[str, Any]) -> str | None:
    coord = (envelope.get("data") or {}).get("coordinator") or {}
    briefing = coord.get("briefing") or {}
    episode_id = briefing.get("episode_id") or coord.get("episode_id")
    return str(episode_id) if episode_id else None


def _injected_envelope(tool: str, failure_class: str) -> dict[str, Any]:
    if failure_class == FailureClass.TIMEOUT.value:
        error = "timed out (injected)"
    elif failure_class == FailureClass.CANCELLED.value:
        error = "execution cancelled (injected)"
    elif failure_class == FailureClass.PERMANENT.value:
        error = "permanent failure (injected)"
    else:
        error = "transient failure (injected)"
    return {
        "contract_version": "1.0",
        "tool": tool,
        "ok": False,
        "error": error,
        "data": {},
    }


class ToolExecutor:
    """Deterministic tool invocation — no planning or routing logic."""

    def __init__(
        self,
        registry: DispatchRegistry,
        *,
        ledger: ExecutionLedger | None = None,
        policies: ExecutionPolicies | None = None,
    ) -> None:
        self._registry = registry
        self._ledger = ledger or ExecutionLedger()
        self._policies = policies or ExecutionPolicies()

    @property
    def ledger(self) -> ExecutionLedger:
        return self._ledger

    @property
    def policies(self) -> ExecutionPolicies:
        return self._policies

    async def _invoke_handler(
        self,
        tool: str,
        args: dict[str, Any],
        *,
        attempt: int,
    ) -> tuple[dict[str, Any], BaseException | None]:
        injector = self._policies.failure_injector
        if injector:
            injected = injector.failure_for(tool, attempt)
            if injected:
                return _injected_envelope(tool, injected), None

        handler = self._registry.get(tool)
        if handler is None:
            return {
                "contract_version": "1.0",
                "tool": tool,
                "ok": False,
                "error": f"unknown tool: {tool}",
                "data": {},
            }, None

        timeout_s = self._policies.timeout.timeout_for(tool)
        try:
            envelope = await asyncio.wait_for(handler(args), timeout=timeout_s)
            return envelope, None
        except asyncio.TimeoutError as exc:
            return {
                "contract_version": "1.0",
                "tool": tool,
                "ok": False,
                "error": f"timed out after {timeout_s}s",
                "data": {},
            }, exc
        except Exception as exc:
            logger.exception("execution_runtime tool %s failed", tool)
            return {
                "contract_version": "1.0",
                "tool": tool,
                "ok": False,
                "error": str(exc),
                "data": {},
            }, exc

    async def execute_tool(
        self,
        tool: str,
        arguments: dict[str, Any] | None = None,
        *,
        attempt: int = 1,
        correlation_id: str | None = None,
        allow_repeat: bool = False,
    ) -> ExecutionResult:
        """Execute a single MCP tool and return the coordinator-enriched envelope."""
        args = dict(arguments or {})
        corr, trace, metrics = self._policies.ensure_observability()
        corr = correlation_id or corr
        safe_registry = self._policies.safe_tools
        idempotency_store = self._policies.idempotency

        idem_key = compute_idempotency_key(
            tool,
            args,
            scope=corr,
            explicit_key=args.get("idempotency_key"),
        )

        if safe_registry.allows_auto_dedupe(tool) and not allow_repeat:
            cached = idempotency_store.get(idem_key)
            if cached is not None:
                replayed_env = dict(cached.envelope)
                metadata = ExecutionMetadata(
                    execution_id=cached.execution_id,
                    correlation_id=corr,
                    tool=tool,
                    attempt=attempt,
                    latency_ms=0,
                    replayed=True,
                    idempotency_key=idem_key,
                )
                attach_execution_metadata(replayed_env, metadata)
                trace.record(
                    ExecutionTraceEvent(
                        event="replay",
                        tool=tool,
                        execution_id=cached.execution_id,
                        correlation_id=corr,
                        attempt=attempt,
                        replayed=True,
                    )
                )
                metrics.record(ok=True, latency_ms=0, replayed=True)
                record = ExecutionRecord(
                    execution_id=cached.execution_id,
                    tool=tool,
                    ok=True,
                    latency_ms=0,
                    correlation_id=corr,
                    attempt=attempt,
                    replayed=True,
                    idempotency_key=idem_key,
                )
                self._ledger.append(record)
                return ExecutionResult(
                    execution_id=cached.execution_id,
                    tool=tool,
                    envelope=replayed_env,
                    latency_ms=0,
                    attempt=attempt,
                    correlation_id=corr,
                    replayed=True,
                    record=record,
                )

        try:
            self._policies.cancellation.check()
        except asyncio.CancelledError:
            return self._cancelled_result(tool, corr, attempt, idem_key)

        current_attempt = attempt
        max_attempts = self._policies.retry.max_attempts_for(tool, safe_registry)
        if not safe_registry.allows_retry(tool, allow_repeat=allow_repeat):
            max_attempts = 1

        last_result: ExecutionResult | None = None
        while current_attempt <= max_attempts:
            try:
                self._policies.cancellation.check()
            except asyncio.CancelledError:
                return self._cancelled_result(tool, corr, current_attempt, idem_key)
            execution_id = _new_execution_id()
            start = time.perf_counter()

            envelope, exc = await self._invoke_handler(tool, args, attempt=current_attempt)
            envelope = process_tool_envelope(tool, args, envelope)
            latency_ms = int((time.perf_counter() - start) * 1000)

            failure_class = classify_failure(
                tool=tool,
                envelope=envelope,
                error=envelope.get("error"),
                exc=exc,
            )
            recovery = evaluate_recovery(
                tool=tool,
                envelope=envelope,
                failure_class=failure_class,
            )

            metadata = ExecutionMetadata(
                execution_id=execution_id,
                correlation_id=corr,
                tool=tool,
                attempt=current_attempt,
                latency_ms=latency_ms,
                failure_class=failure_class.value,
                recovery_trigger=(
                    recovery.trigger_id if recovery.action.value != "none" else None
                ),
                cancelled=failure_class == FailureClass.CANCELLED,
                idempotency_key=idem_key,
            )
            attach_execution_metadata(envelope, metadata)

            session_id = envelope.get("session_id") or args.get("session_id")
            if isinstance(session_id, str):
                session_id = session_id or None

            record = ExecutionRecord(
                execution_id=execution_id,
                tool=tool,
                ok=bool(envelope.get("ok")) and failure_class == FailureClass.NONE,
                latency_ms=latency_ms,
                correlation_id=corr,
                error=envelope.get("error") if not envelope.get("ok") else None,
                session_id=session_id,
                episode_id=_episode_id_from_envelope(envelope),
                attempt=current_attempt,
                failure_class=failure_class.value,
                recovery_trigger=metadata.recovery_trigger,
                cancelled=failure_class == FailureClass.CANCELLED,
                idempotency_key=idem_key,
            )
            self._ledger.append(record)

            retried = current_attempt > attempt
            trace.record(
                ExecutionTraceEvent(
                    event="execute",
                    tool=tool,
                    execution_id=execution_id,
                    correlation_id=corr,
                    attempt=current_attempt,
                    latency_ms=latency_ms,
                    failure_class=failure_class.value,
                    recovery_trigger=metadata.recovery_trigger,
                    cancelled=failure_class == FailureClass.CANCELLED,
                )
            )
            metrics.record(
                ok=record.ok,
                latency_ms=latency_ms,
                retried=retried,
                cancelled=failure_class == FailureClass.CANCELLED,
            )

            result = ExecutionResult(
                execution_id=execution_id,
                tool=tool,
                envelope=envelope,
                latency_ms=latency_ms,
                attempt=current_attempt,
                correlation_id=corr,
                failure_class=failure_class.value,
                recovery_trigger=metadata.recovery_trigger,
                cancelled=failure_class == FailureClass.CANCELLED,
                record=record,
            )
            last_result = result

            if failure_class == FailureClass.NONE and envelope.get("ok"):
                if safe_registry.allows_auto_dedupe(tool):
                    idempotency_store.put(
                        idem_key,
                        IdempotencyEntry(
                            key=idem_key,
                            tool=tool,
                            envelope=dict(envelope),
                            execution_id=execution_id,
                        ),
                    )
                return result

            decision = evaluate_retry(
                tool=tool,
                failure_class=failure_class,
                attempt=current_attempt,
                policy=self._policies.retry,
                safe_registry=safe_registry,
                allow_repeat=allow_repeat,
            )
            if decision == RetryDecision.RETRY:
                trace.record(
                    ExecutionTraceEvent(
                        event="retry",
                        tool=tool,
                        execution_id=execution_id,
                        correlation_id=corr,
                        attempt=current_attempt,
                        failure_class=failure_class.value,
                        detail=decision.value,
                    )
                )
                if self._policies.retry.backoff_ms > 0:
                    await asyncio.sleep(self._policies.retry.backoff_ms / 1000.0)
                current_attempt += 1
                continue

            return result

        return last_result or self._cancelled_result(tool, corr, current_attempt, idem_key)

    def _cancelled_result(
        self,
        tool: str,
        correlation_id: str,
        attempt: int,
        idempotency_key: str,
    ) -> ExecutionResult:
        corr, trace, metrics = self._policies.ensure_observability()
        execution_id = _new_execution_id()
        envelope: dict[str, Any] = {
            "contract_version": "1.0",
            "tool": tool,
            "ok": False,
            "error": "execution cancelled",
            "data": {},
        }
        metadata = ExecutionMetadata(
            execution_id=execution_id,
            correlation_id=correlation_id,
            tool=tool,
            attempt=attempt,
            latency_ms=0,
            failure_class=FailureClass.CANCELLED.value,
            cancelled=True,
            idempotency_key=idempotency_key,
        )
        attach_execution_metadata(envelope, metadata)
        trace.record(
            ExecutionTraceEvent(
                event="cancelled",
                tool=tool,
                execution_id=execution_id,
                correlation_id=correlation_id,
                attempt=attempt,
                cancelled=True,
            )
        )
        metrics.record(ok=False, latency_ms=0, cancelled=True)
        record = ExecutionRecord(
            execution_id=execution_id,
            tool=tool,
            ok=False,
            latency_ms=0,
            correlation_id=correlation_id,
            error="execution cancelled",
            attempt=attempt,
            failure_class=FailureClass.CANCELLED.value,
            cancelled=True,
            idempotency_key=idempotency_key,
        )
        self._ledger.append(record)
        return ExecutionResult(
            execution_id=execution_id,
            tool=tool,
            envelope=envelope,
            latency_ms=0,
            attempt=attempt,
            correlation_id=correlation_id,
            failure_class=FailureClass.CANCELLED.value,
            cancelled=True,
            record=record,
        )

    async def execute(
        self,
        compiled_step: CompiledStep | dict[str, Any],
        *,
        allow_repeat: bool = False,
    ) -> CompiledExecutionResult:
        """Execute all tools in a coordinator CompiledStep sequentially."""
        cap_id, semantic, step_id, playbook_id, tools = _normalize_compiled_step(compiled_step)
        corr, _, _ = self._policies.ensure_observability()
        results: list[ExecutionResult] = []
        recovery_trigger: str | None = None

        for spec in tools:
            tool = spec.get("tool")
            if not tool:
                continue
            result = await self.execute_tool(
                tool,
                spec.get("arguments") or {},
                correlation_id=corr,
                allow_repeat=allow_repeat,
            )
            results.append(result)
            if result.recovery_trigger and result.recovery_trigger not in ("none", "cancelled"):
                recovery_trigger = result.recovery_trigger
            if not result.ok:
                break

        ok = bool(results) and all(r.ok for r in results)
        return CompiledExecutionResult(
            capability_id=cap_id,
            semantic_action=semantic,
            step_id=step_id,
            playbook_id=playbook_id,
            results=results,
            ok=ok,
            correlation_id=corr,
        )
