"""Gemini client via Application Default Credentials (Vertex)."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from google import genai
from google.genai import types


# gemini-3.1-pro-preview is available on Vertex location=global for this project.
DEFAULT_MODEL = os.environ.get("FOROPENCODE_GEMINI_MODEL", "gemini-3.1-pro-preview")
DEFAULT_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")


def _project() -> str:
	project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
	if not project:
		import google.auth

		_, project = google.auth.default()
	if not project:
		raise RuntimeError(
			"GOOGLE_CLOUD_PROJECT not set and ADC has no project. "
			"Run: gcloud auth application-default login && set GOOGLE_CLOUD_PROJECT"
		)
	return project


def _location_for_model(model: str) -> str:
	"""3.1 preview models require global; allow env override."""
	if os.environ.get("GOOGLE_CLOUD_LOCATION"):
		return os.environ["GOOGLE_CLOUD_LOCATION"]
	if "3.1" in model or model.startswith("gemini-3"):
		return "global"
	return DEFAULT_LOCATION


def make_client(model: str | None = None) -> genai.Client:
	os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
	project = _project()
	model = model or DEFAULT_MODEL
	location = _location_for_model(model)
	return genai.Client(vertexai=True, project=project, location=location)


def smoke_test(client: genai.Client | None = None, model: str | None = None) -> str:
	model = model or DEFAULT_MODEL
	client = client or make_client(model=model)
	# Thinking models may spend tokens internally; keep budget generous for smoke.
	resp = client.models.generate_content(
		model=model,
		contents="Reply with exactly the two letters: OK",
		config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=256),
	)
	text = (resp.text or "").strip()
	if not text:
		# Fallback: inspect candidates if .text is empty
		cands = getattr(resp, "candidates", None) or []
		parts = []
		for c in cands:
			content = getattr(c, "content", None)
			for p in getattr(content, "parts", None) or []:
				if getattr(p, "text", None):
					parts.append(p.text)
		text = "".join(parts).strip()
	if "OK" not in text.upper():
		raise RuntimeError(f"Gemini smoke unexpected response: {text!r}")
	return text


def generate_json(
	*,
	prompt: str,
	model: str | None = None,
	temperature: float = 0.1,
	client: genai.Client | None = None,
) -> dict[str, Any]:
	"""Ask Gemini for a JSON object; parse and return."""
	model = model or DEFAULT_MODEL
	client = client or make_client(model=model)
	full = (
		prompt
		+ "\n\nReturn ONLY a single valid JSON object. No markdown fences. No commentary."
		+ "\nEscape all quotes inside strings. No trailing commas."
	)
	last_err: Exception | None = None
	raw = ""
	for attempt in range(2):
		resp = client.models.generate_content(
			model=model,
			contents=full if attempt == 0 else (
				full
				+ f"\n\nPREVIOUS OUTPUT WAS INVALID JSON ({last_err}). "
				+ "Return corrected JSON only.\n\nBAD OUTPUT:\n"
				+ raw[:4000]
			),
			config=types.GenerateContentConfig(
				temperature=temperature if attempt == 0 else 0.05,
				response_mime_type="application/json",
				max_output_tokens=16384,
			),
		)
		raw = (resp.text or "").strip()
		if not raw:
			# pull from candidates
			parts = []
			for c in getattr(resp, "candidates", None) or []:
				content = getattr(c, "content", None)
				for p in getattr(content, "parts", None) or []:
					if getattr(p, "text", None):
						parts.append(p.text)
			raw = "".join(parts).strip()
		try:
			return parse_json_object(raw)
		except Exception as exc:  # noqa: BLE001
			last_err = exc
			continue
	raise RuntimeError(f"Gemini JSON parse failed after retry: {last_err}\nRAW={raw[:500]!r}")


def parse_json_object(raw: str) -> dict[str, Any]:
	text = raw.strip()
	if text.startswith("```"):
		text = re.sub(r"^```(?:json)?\s*", "", text)
		text = re.sub(r"\s*```$", "", text)
	# common repairs
	text = re.sub(r",\s*}", "}", text)
	text = re.sub(r",\s*]", "]", text)
	try:
		data = json.loads(text)
	except json.JSONDecodeError:
		m = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)
		if not m:
			raise
		frag = m.group(0)
		frag = re.sub(r",\s*}", "}", frag)
		frag = re.sub(r",\s*]", "]", frag)
		data = json.loads(frag)
	if isinstance(data, list):
		objs = [x for x in data if isinstance(x, dict)]
		if len(objs) == 1:
			data = objs[0]
		elif objs:
			for x in objs:
				if "id" in x or "claim_id" in x or "definition" in x:
					data = x
					break
			else:
				data = objs[0]
		else:
			raise ValueError(f"Expected JSON object, got list without objects: {data!r}")
	if not isinstance(data, dict):
		raise ValueError(f"Expected JSON object, got {type(data)}")
	return data
