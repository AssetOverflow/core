"""Baseline runner — scores frontier models on eval lane public test sets.

Queries a frontier model API on the same public test set that CORE is scored on,
using the eval task as the prompt (no prompt engineering, no tuning).

Current implementation is a scaffold with a pluggable model interface.  Actual
API calls are deferred until API keys are configured.

Trust boundary: this module calls external APIs.  It sends only eval prompts
(which are not sensitive) and writes scores to ``evals/<lane>/baselines/``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol


class BaselineModel(Protocol):
    """Interface for a frontier model baseline."""

    @property
    def model_id(self) -> str: ...

    def score_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Score a single case. Returns a dict with at minimum 'passed': bool."""
        ...


@dataclass(frozen=True, slots=True)
class BaselineResult:
    lane: str
    version: str
    model_id: str
    metrics: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return {
            "lane": self.lane,
            "version": self.version,
            "model_id": self.model_id,
            "timestamp": self.timestamp,
            "metrics": self.metrics,
        }


class StubBaseline:
    """Placeholder baseline that records 'not scored' for all cases."""

    @property
    def model_id(self) -> str:
        return "stub-not-configured"

    def score_case(self, case: dict[str, Any]) -> dict[str, Any]:
        return {"passed": False, "reason": "baseline model not configured"}


def write_baseline(
    lane_root: Path,
    result: BaselineResult,
) -> Path:
    """Write a baseline result to the lane's baselines directory."""
    baselines_dir = lane_root / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{result.version}_{result.model_id}_{ts}.json"
    path = baselines_dir / filename
    path.write_text(
        json.dumps(result.as_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    return path
