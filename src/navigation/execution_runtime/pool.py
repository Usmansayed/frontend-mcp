"""Shared thread pool for SYNC_OFFLOAD handlers."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

_executor: ThreadPoolExecutor | None = None


def get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        workers = int(os.environ.get("PERCEPTION_EXECUTOR_WORKERS", "4"))
        _executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="perception-exec")
    return _executor


def shutdown_executor() -> None:
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False, cancel_futures=True)
        _executor = None
