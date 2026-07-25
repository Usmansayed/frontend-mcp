"""Decision Layer Lab — scenario pack runner."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from navigation.coordination_intelligence.lab.core import DecisionLayerLab
from navigation.coordination_intelligence.lab.expect import check_expectations


@dataclass
class StepResult:
    index: int
    op: str
    ok: bool
    failures: list[str] = field(default_factory=list)
    snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioResult:
    id: str
    passed: bool
    steps: list[StepResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    final_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "passed": self.passed,
            "failures": list(self.failures),
            "steps": [
                {
                    "index": s.index,
                    "op": s.op,
                    "ok": s.ok,
                    "failures": list(s.failures),
                }
                for s in self.steps
            ],
        }


@dataclass
class PackResult:
    results: list[ScenarioResult] = field(default_factory=list)
    pack_id: str = "pack"

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def scorecard(self) -> str:
        lines = [
            f"Decision Lab pack [{self.pack_id}]: "
            f"{self.pass_count}/{len(self.results)} passed"
        ]
        for r in self.results:
            mark = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{mark}] {r.id}")
            for f in r.failures:
                lines.append(f"         - {f}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "passed": self.passed,
            "pass_count": self.pass_count,
            "total": len(self.results),
            "scenarios": [r.to_dict() for r in self.results],
        }


def decision_lab_root() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[4]
    return root / "evals" / "decision_lab"


def default_scenarios_dir() -> Path:
    return decision_lab_root() / "scenarios"


def default_baseline_pack() -> Path:
    return decision_lab_root() / "packs" / "baseline.yaml"


def default_smoke_pack() -> Path:
    return decision_lab_root() / "packs" / "smoke.yaml"


def load_scenario(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"scenario must be a mapping: {p}")
    data.setdefault("id", p.stem)
    return data


def list_scenarios(directory: Path | str | None = None) -> list[Path]:
    d = Path(directory) if directory else default_scenarios_dir()
    return sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml"))


def load_pack_manifest(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"pack manifest must be a mapping: {p}")
    return data


def resolve_pack_scenario_paths(pack: Path | str | None = None) -> tuple[str, list[Path]]:
    """Resolve a pack name, manifest file, or scenarios directory → (pack_id, paths)."""
    root = decision_lab_root()
    if pack is None:
        pack_path = default_baseline_pack()
    else:
        raw = str(pack)
        pack_path = Path(pack)
        if raw in ("baseline", "smoke"):
            pack_path = root / "packs" / f"{raw}.yaml"
        elif not pack_path.is_absolute():
            as_named = root / "packs" / f"{raw}.yaml"
            as_under_root = root / raw
            if as_named.exists():
                pack_path = as_named
            elif as_under_root.exists():
                pack_path = as_under_root
            elif not pack_path.exists():
                pack_path = as_named

    if pack_path.is_dir():
        return pack_path.name, list_scenarios(pack_path)

    if pack_path.suffix in (".yaml", ".yml") and pack_path.exists():
        manifest = load_pack_manifest(pack_path)
        pack_id = str(manifest.get("id") or pack_path.stem)
        paths: list[Path] = []
        for rel in manifest.get("scenarios") or []:
            candidate = root / str(rel)
            if not candidate.exists():
                raise FileNotFoundError(f"pack {pack_id}: missing scenario {rel}")
            paths.append(candidate)
        return pack_id, paths

    raise FileNotFoundError(f"unknown pack: {pack}")


def write_scorecard(pack: PackResult, path: Path | str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack.to_dict(), indent=2, default=str), encoding="utf-8")
    return out


def _apply_feed(lab: DecisionLayerLab, feed: dict[str, Any]) -> dict[str, Any]:
    op = str(feed.get("op") or "feed")
    if op == "seed_ledger":
        return lab.seed_ledger(
            str(feed["capability_id"]),
            dict(feed.get("outcome") or {}),
        )
    if op == "set_retry":
        return lab.set_retry(str(feed["key"]), feed.get("value"))
    if op == "set_surface_type":
        return lab.set_surface_type(str(feed["surface_type"]))
    if op == "set_verification":
        eid = lab._require_episode()
        psm = lab.service.runtime.require(eid)
        psm.episode.verification_status = str(feed.get("status") or "pending")
        lab.service.runtime.save(psm)
        lab.service.briefing(eid)
        return lab.snapshot()
    if op == "seed_sections":
        return lab.seed_sections_from_regions(list(feed.get("regions") or []))
    if op == "complete_sections":
        return lab.complete_sections()
    if op == "run_ship":
        out = lab.run_ship(
            dict(feed.get("snapshot") or {}),
            dispositions=list(feed.get("dispositions") or []) or None,
            auto_dispose=feed.get("auto_dispose"),
            force=bool(feed.get("force", True)),
        )
        return out["snapshot"]
    return lab.feed(
        str(feed["tool"]),
        ok=bool(feed.get("ok", True)),
        data=dict(feed.get("data") or {}),
        error=feed.get("error"),
        arguments=dict(feed.get("arguments") or {}),
        capability_id=feed.get("capability_id"),
    )["snapshot"]


def run_scenario(
    scenario: dict[str, Any] | Path | str,
    *,
    lab: DecisionLayerLab | None = None,
) -> ScenarioResult:
    if isinstance(scenario, (str, Path)):
        scenario = load_scenario(scenario)
    sid = str(scenario.get("id") or "unnamed")
    lab = lab or DecisionLayerLab(session_id=f"lab_{sid}")
    lab.start(
        str(scenario.get("intent") or "lab scenario"),
        lifecycle_stage=str(scenario.get("lifecycle_stage") or "S03_design"),
        project_maturity=str(scenario.get("project_maturity") or "M1"),
        situation_class=str(scenario.get("situation_class") or "new_feature"),
    )

    result = ScenarioResult(id=sid, passed=True)
    start_expect = scenario.get("expect_after_start")
    if start_expect:
        snap = lab.snapshot()
        fails = check_expectations(snap, start_expect)
        step = StepResult(index=0, op="start", ok=not fails, failures=fails, snapshot=snap)
        result.steps.append(step)
        if fails:
            result.passed = False
            result.failures.extend(fails)

    for i, feed in enumerate(scenario.get("feeds") or [], start=1):
        snap = _apply_feed(lab, feed)
        fails = check_expectations(snap, feed.get("expect"))
        step = StepResult(
            index=i,
            op=str(feed.get("op") or feed.get("tool") or "feed"),
            ok=not fails,
            failures=fails,
            snapshot=snap,
        )
        result.steps.append(step)
        if fails:
            result.passed = False
            result.failures.extend([f"step {i}: {f}" for f in fails])

    final = lab.snapshot()
    result.final_snapshot = final
    final_fails = check_expectations(final, scenario.get("expect"))
    if final_fails:
        result.passed = False
        result.failures.extend([f"final: {f}" for f in final_fails])
    return result


def run_pack(
    directory: Path | str | None = None,
    *,
    pack: Path | str | None = None,
) -> PackResult:
    """Run a scenarios directory (legacy) or a pack manifest / name.

    Defaults to the baseline pack when both args are omitted.
    """
    result = PackResult()
    if directory is not None and pack is None:
        paths = list_scenarios(directory)
        result.pack_id = Path(directory).name
    else:
        pack_id, paths = resolve_pack_scenario_paths(pack)
        result.pack_id = pack_id
    for path in paths:
        result.results.append(run_scenario(path))
    return result
