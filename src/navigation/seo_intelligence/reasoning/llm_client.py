"""Optional Bedrock LLM client for SEO AI reasoning (Sprint 3)."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from navigation.seo_intelligence.reasoning.prompt import SYSTEM_PROMPT, build_ai_user_message


class SeoLlmClient(Protocol):
	def is_available(self) -> bool: ...

	def complete_json(self, *, system: str, user: str) -> dict[str, Any]: ...


_JSON_BLOCK_RE = re.compile(r'\{[\s\S]*\}')


def ai_reasoning_enabled(request_flag: bool | None = None) -> bool:
	"""Auto-enable when credentials exist unless explicitly disabled."""
	env = os.environ.get('SEO_AI_REASONING', '').strip().lower()
	if env in {'0', 'false', 'no', 'off'}:
		return False
	if env in {'1', 'true', 'yes', 'on'}:
		return True
	if request_flag is False:
		return False
	if request_flag is True:
		return True
	return BedrockSeoLlmClient().is_available()


class BedrockSeoLlmClient:
	def __init__(
		self,
		*,
		model: str | None = None,
		region: str | None = None,
		temperature: float = 0.2,
	) -> None:
		self._model = (
			model
			or os.environ.get('SEO_BEDROCK_MODEL')
			or os.environ.get('BEDROCK_MODEL')
			or 'amazon.nova-lite-v1:0'
		)
		self._region = (
			region
			or os.environ.get('SEO_BEDROCK_REGION')
			or os.environ.get('AWS_REGION')
			or os.environ.get('AWS_DEFAULT_REGION')
			or 'us-east-1'
		)
		self._temperature = temperature

	def is_available(self) -> bool:
		if os.environ.get('SEO_SKIP_AI_REASONING', '').strip().lower() in {'1', 'true', 'yes'}:
			return False
		try:
			import boto3

			return boto3.Session(region_name=self._region).get_credentials() is not None
		except Exception:
			return False

	def complete_json(self, *, system: str, user: str) -> dict[str, Any]:
		try:
			import boto3
		except ImportError as exc:
			raise RuntimeError('boto3 required for SEO AI reasoning (pip install frontend-perception-engine[aws])') from exc

		client = boto3.client('bedrock-runtime', region_name=self._region)
		response = client.converse(
			modelId=self._model,
			system=[{'text': system}],
			messages=[{'role': 'user', 'content': [{'text': user}]}],
			inferenceConfig={
				'temperature': self._temperature,
				'maxTokens': 4096,
			},
		)
		text = ''
		for block in response.get('output', {}).get('message', {}).get('content', []):
			if isinstance(block, dict) and block.get('text'):
				text += block['text']
		return _parse_json_response(text)


def draft_recommendations_with_llm(
	payload: dict[str, Any],
	*,
	client: SeoLlmClient | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
	"""Call host LLM and return raw recommendation drafts."""
	llm = client or BedrockSeoLlmClient()
	degraded: list[str] = []
	if not llm.is_available():
		return [], ['ai_reasoning_unavailable']

	try:
		raw = llm.complete_json(
			system=SYSTEM_PROMPT,
			user=build_ai_user_message(payload),
		)
	except Exception as exc:
		return [], [f'ai_reasoning_error:{exc}']

	recs = raw.get('recommendations') if isinstance(raw, dict) else None
	if not isinstance(recs, list):
		return [], ['ai_reasoning_invalid_response']
	return [r for r in recs if isinstance(r, dict)], degraded


def _parse_json_response(text: str) -> dict[str, Any]:
	text = text.strip()
	if text.startswith('```'):
		text = re.sub(r'^```(?:json)?\s*', '', text)
		text = re.sub(r'\s*```$', '', text)
	try:
		parsed = json.loads(text)
		if isinstance(parsed, dict):
			return parsed
	except json.JSONDecodeError:
		pass
	match = _JSON_BLOCK_RE.search(text)
	if match:
		parsed = json.loads(match.group(0))
		if isinstance(parsed, dict):
			return parsed
	raise ValueError('LLM response is not valid JSON object')
