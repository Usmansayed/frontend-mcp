"""Shared HTTP helpers for resource provider adapters."""
from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Any


def fetch_json_sync(url: str, *, headers: dict[str, str] | None = None, timeout: float = 30) -> Any:
	req_headers = {'User-Agent': 'frontend-perception-engine/1.0'}
	if headers:
		req_headers.update(headers)
	req = urllib.request.Request(url, headers=req_headers)
	with urllib.request.urlopen(req, timeout=timeout) as resp:
		return json.loads(resp.read().decode('utf-8'))


async def fetch_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = 30) -> Any:
	return await asyncio.to_thread(fetch_json_sync, url, headers=headers, timeout=timeout)
