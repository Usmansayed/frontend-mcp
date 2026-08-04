# tests/test_inspiration_pulse_loop.py
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from navigation.coordination_intelligence.planning.inspiration_pulse_loop import (
	cancel_inspiration_pulse,
	clear_pulse_store,
	get_pulse_snapshot,
	mark_pulse_look_locked,
	pulse_enabled,
	schedule_inspiration_pulse,
	should_start_pulse,
)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
	monkeypatch.setenv("PERCEPTION_INSPIRATION_PULSE", "1")
	monkeypatch.setenv("PERCEPTION_INSPIRATION_PULSE_INTERVAL_S", "60")
	monkeypatch.setenv("PERCEPTION_INSPIRATION_PULSE_AFTER_LOCK", "0")
	clear_pulse_store()
	yield
	clear_pulse_store()


@pytest.mark.unit
def test_should_start_pulse_design_classes():
	assert should_start_pulse(face_class="greenfield", evidence_band="heavy")
	assert should_start_pulse(face_class="redesign", evidence_band="medium")
	assert not should_start_pulse(face_class="hotfix", evidence_band="heavy")
	assert not should_start_pulse(face_class="forms", evidence_band="medium")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_pulse_runs_wave_and_cancel(monkeypatch):
	async def _fake_discover(self, request):
		from types import SimpleNamespace

		cand = SimpleNamespace(
			candidate_id="web_og:maze.co:0",
			title="Maze UI",
			url="https://maze.co/example",
			preview_ref="https://cdn.example/maze.jpg",
			provider_id="web",
			external_id="0",
			discovery_score=0.9,
		)
		ranked = SimpleNamespace(candidate=cand, overall_score=0.9)
		plan = SimpleNamespace(provider_ids=["web"])
		return SimpleNamespace(candidates=[ranked], search_plan=plan, degraded=[])

	monkeypatch.setattr(
		"navigation.inspiration_intelligence.InspirationIntelligenceService.discover",
		_fake_discover,
	)

	def _fake_materialize(self, session_id, hits):
		for hit in hits:
			hit["inspiration_blob"] = f"/tmp/{hit.get('candidate_id')}.jpg"
		return {"materialized": len(hits), "failed": 0, "session_id": session_id}

	monkeypatch.setattr(
		"navigation.inspiration_intelligence.tools.blob_store.InspirationBlobStore.materialize_hits",
		_fake_materialize,
	)
	monkeypatch.setattr(
		"navigation.inspiration_intelligence.tools.blob_store.InspirationBlobStore.create_session",
		lambda self, purpose="": "insp_testpulse",
	)

	assert pulse_enabled()
	snap = schedule_inspiration_pulse(
		episode_id="ep_pulse",
		session_id="sess_pulse",
		query="modern AI chat workspace dark elegant",
		face_class="redesign",
		evidence_band="very_heavy",
	)
	assert snap is not None
	assert snap["status"] == "running"
	assert snap["http_parallel"] is True
	assert snap["browser_parallel"] is False

	# Let first wave finish
	for _ in range(40):
		await asyncio.sleep(0.05)
		done = get_pulse_snapshot("ep_pulse")
		if done and int(done.get("thumb_count") or 0) > 0:
			break
	done = get_pulse_snapshot("ep_pulse")
	assert done is not None
	assert int(done.get("thumb_count") or 0) >= 1
	assert done.get("discover_token")

	mark_pulse_look_locked(episode_id="ep_pulse", locked=True)
	# Loop should pause on next check; cancel for cleanup
	cancel_inspiration_pulse("ep_pulse")
	assert get_pulse_snapshot("ep_pulse") is None


@pytest.mark.unit
def test_face_card_surfaces_inspiration_pulse():
	from navigation.coordination_intelligence.planning.coordinator_card import (
		build_agent_face_card,
	)
	from navigation.coordination_intelligence.planning import inspiration_pulse_loop as loop

	# Seed a fake pulse row without async
	row = loop.InspirationPulseEpisode(
		episode_id="ep_card_pulse",
		session_id="sess_card",
		query="landing",
		face_class="greenfield",
		evidence_band="heavy",
		status="running",
		generation=1,
	)
	row.thumbs.append(
		loop.Thumb(
			ref_id="ref_1",
			title="Example",
			url="https://example.com",
			preview_url="https://cdn.example/a.jpg",
			blob_path="/tmp/a.jpg",
			provider_id="web",
			generation=1,
			added_at=0.0,
		)
	)
	with loop._LOCK:
		loop._STORE["ep_card_pulse"] = row

	face = build_agent_face_card(
		episode_id="ep_card_pulse",
		strategy={
			"task_scope": "design_driven",
			"influence_level": "structural",
			"implementation_gate": {"state": "blocked", "prohibited_actions": []},
			"episode_portfolio": {
				"paid": [],
				"unpaid": [{"family": "inspiration"}],
			},
			"recommended_resource": "perception://spine/greenfield",
		},
	)
	pulse = face.get("inspiration_pulse") or {}
	assert pulse.get("thumb_count") == 1
	assert "inspiration" in (face.get("can_parallel") or [])
