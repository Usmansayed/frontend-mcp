"""High-level audit service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from navigation.perception.verification import read_current_url

from .models import AuditCategory, AuditReport
from .parser import parse_lighthouse_report
from .runner import (
	LighthouseNotAvailableError,
	LighthouseRunError,
	lighthouse_available,
	run_lighthouse,
)


class AuditService:
	async def run_category(
		self,
		*,
		url: str,
		category: AuditCategory,
		artifacts_dir: Path,
		timeout_s: int = 120,
	) -> AuditReport:
		audits_dir = artifacts_dir / 'audits'
		tmp_dir = artifacts_dir / 'lighthouse-tmp'
		output_path = audits_dir / f'lighthouse-{category.value}.json'

		try:
			lhr = await run_lighthouse(
				url,
				category,
				output_path,
				tmp_dir=tmp_dir,
				timeout_s=timeout_s,
			)
		except LighthouseNotAvailableError:
			raise
		except LighthouseRunError as exc:
			if output_path.is_file():
				lhr = json.loads(output_path.read_text(encoding='utf-8'))
			else:
				raise

		report = parse_lighthouse_report(lhr, category)
		report.artifacts['lighthouse_json'] = str(output_path)
		return report


async def run_audit(
	browser_session: Any,
	*,
	category: AuditCategory,
	base_url: str,
	artifacts_dir: Path,
	url: str | None = None,
	timeout_s: int = 120,
) -> AuditReport:
	target = url or await read_current_url(browser_session)
	if not target.startswith('http'):
		target = f'{base_url.rstrip("/")}/{target.lstrip("/")}'

	if not lighthouse_available():
		raise LighthouseNotAvailableError(
			'Lighthouse not available. Install Node.js; audits use `npx lighthouse@12`.'
		)

	service = AuditService()
	return await service.run_category(
		url=target,
		category=category,
		artifacts_dir=artifacts_dir,
		timeout_s=timeout_s,
	)
