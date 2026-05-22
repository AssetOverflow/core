"""Generic eval framework — discovers lanes, loads contracts, runs versioned scoring.

Every eval lane lives in ``evals/<lane>/`` and must contain at minimum:
- ``contract.md``  — human-readable contract (presence required, not parsed at runtime)
- ``runner.py``    — module that exposes ``run_lane(cases, **kwargs) -> LaneReport``
- ``dev/cases.jsonl``          — dev set
- ``public/v1/cases.jsonl``    — public test set v1

Optional:
- ``holdouts/``    — encrypted sealed test set (scored by holdout_runner)
- ``baselines/``   — frontier model scores
- ``results/``     — CORE scores per version per run
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVALS_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class LaneInfo:
    name: str
    root: Path
    versions: tuple[str, ...]

    @property
    def contract_path(self) -> Path:
        return self.root / "contract.md"

    @property
    def runner_path(self) -> Path:
        return self.root / "runner.py"

    def dev_cases_path(self) -> Path:
        return self.root / "dev" / "cases.jsonl"

    def public_cases_path(self, version: str = "v1") -> Path:
        return self.root / "public" / version / "cases.jsonl"

    def holdout_cases_path(self, version: str = "v1") -> Path:
        holdouts = self.root / "holdouts"
        candidates = (
            holdouts / "cases.jsonl",
            holdouts / "cases_plaintext.jsonl",
            holdouts / version / "cases.jsonl",
        )
        for path in candidates:
            if path.exists():
                return path
        return candidates[-1]

    def holdout_cases_path_sealed(self, version: str = "v1") -> Path:
        """Return the resolved sealed holdout path for this lane.

        Resolution order (first existing wins):
          1. ``holdouts/cases.jsonl.age``
          2. ``holdouts/<version>/cases.jsonl.age``

        Returns the versioned candidate if none exist so callers receive
        coherent fail-closed FileNotFoundError semantics.
        """
        holdouts = self.root / "holdouts"
        candidates = (
            holdouts / "cases.jsonl.age",
            holdouts / version / "cases.jsonl.age",
        )
        for path in candidates:
            if path.exists():
                return path
        return candidates[-1]

    def results_dir(self) -> Path:
        return self.root / "results"


@dataclass(slots=True)
class LaneResult:
    lane: str
    version: str
    split: str
    metrics: dict[str, Any]
    case_details: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "version": self.version,
            "split": self.split,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
            "cases": self.case_details,
        }


def discover_lanes(root: Path | None = None) -> list[LaneInfo]:
    base = root or EVALS_ROOT
    lanes: list[LaneInfo] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        contract = child / "contract.md"
        runner = child / "runner.py"
        if contract.exists() and runner.exists():
            versions = _discover_versions(child)
            lanes.append(LaneInfo(name=child.name, root=child, versions=versions))
    return lanes


def _discover_versions(lane_root: Path) -> tuple[str, ...]:
    public = lane_root / "public"
    if not public.is_dir():
        return ()
    versions = sorted(
        d.name for d in public.iterdir()
        if d.is_dir() and (d / "cases.jsonl").exists()
    )
    return tuple(versions)


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def load_lane_runner(lane: LaneInfo) -> Any:
    runner_path = lane.runner_path
    if not runner_path.exists():
        raise FileNotFoundError(f"Runner not found: {runner_path}")

    module_name = f"evals.{lane.name}.runner"
    spec = importlib.util.spec_from_file_location(module_name, runner_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load runner: {runner_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_lane(
    lane: LaneInfo,
    *,
    version: str = "v1",
    split: str = "public",
    config: Any = None,
    workers: int | None = None,
) -> LaneResult:
    if split == "dev":
        cases_path = lane.dev_cases_path()
    elif split == "public":
        cases_path = lane.public_cases_path(version)
    elif split == "holdout":
        cases_path = lane.holdout_cases_path(version)
    else:
        raise ValueError(
            f"Unsupported split: {split!r}. Use 'dev', 'public', or 'holdout'."
        )

    if not cases_path.exists():
        raise FileNotFoundError(f"Cases not found: {cases_path}")

    cases = load_cases(cases_path)
    runner_module = load_lane_runner(lane)

    runner_params = inspect.signature(runner_module.run_lane).parameters
    if "workers" in runner_params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in runner_params.values()
    ):
        report = runner_module.run_lane(cases, config=config, workers=workers)
    else:
        report = runner_module.run_lane(cases, config=config)

    return LaneResult(
        lane=lane.name,
        version=version,
        split=split,
        metrics=report.metrics,
        case_details=report.case_details,
    )


def write_result(lane: LaneInfo, result: LaneResult) -> Path:
    results_dir = lane.results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{result.version}_{result.split}_{ts}.json"
    path = results_dir / filename
    path.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    return path


def get_lane(name: str, root: Path | None = None) -> LaneInfo:
    base = root or EVALS_ROOT
    lane_root = base / name
    contract = lane_root / "contract.md"
    runner = lane_root / "runner.py"
    if not contract.exists():
        raise FileNotFoundError(f"Lane '{name}' has no contract.md at {contract}")
    if not runner.exists():
        raise FileNotFoundError(f"Lane '{name}' has no runner.py at {runner}")
    versions = _discover_versions(lane_root)
    return LaneInfo(name=name, root=lane_root, versions=versions)
