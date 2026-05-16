"""Holdout runner — scores sealed test sets without exposing item-level results.

The holdout set lives encrypted in ``evals/<lane>/holdouts/``.  The decryption
key is held by the human reviewer and supplied via environment variable.

Current implementation is a scaffold: it reads plaintext holdouts for initial
development.  The encryption layer (age or GPG) is wired in before any holdout
set is considered "sealed."

Trust boundary: this module reads encrypted files and writes only aggregate
scores.  It must never write item-level results, case details, or raw case
content to the working tree.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.framework import LaneInfo, load_lane_runner, load_cases


HOLDOUT_KEY_ENV = "CORE_HOLDOUT_KEY"


@dataclass(frozen=True, slots=True)
class HoldoutResult:
    lane: str
    metrics: dict[str, Any]
    sealed: bool


def _decrypt_holdout(encrypted_path: Path) -> list[dict[str, Any]]:
    """Decrypt a holdout file and return cases.

    Currently: reads plaintext fallback if no encryption key is set.
    Future: decrypt with age/GPG using CORE_HOLDOUT_KEY.
    """
    key = os.environ.get(HOLDOUT_KEY_ENV)

    plaintext_path = encrypted_path.parent / "cases_plaintext.jsonl"
    if key is None and plaintext_path.exists():
        return load_cases(plaintext_path)

    if key is None:
        raise EnvironmentError(
            f"Set {HOLDOUT_KEY_ENV} to decrypt holdout, or provide "
            f"cases_plaintext.jsonl for unsealed development."
        )

    # TODO: implement actual decryption (age -d -i <key> <encrypted_path>)
    raise NotImplementedError(
        "Encrypted holdout decryption not yet implemented. "
        "Use cases_plaintext.jsonl for development."
    )


def run_holdout(lane: LaneInfo, *, config: Any = None) -> HoldoutResult:
    """Score a lane's holdout set and return only aggregate metrics."""
    holdout_dir = lane.root / "holdouts"
    if not holdout_dir.exists():
        raise FileNotFoundError(f"No holdouts directory: {holdout_dir}")

    cases = _decrypt_holdout(holdout_dir / "cases.jsonl.age")

    runner_module = load_lane_runner(lane)
    report = runner_module.run_lane(cases, config=config)

    sealed = os.environ.get(HOLDOUT_KEY_ENV) is not None

    return HoldoutResult(
        lane=lane.name,
        metrics=report.metrics,
        sealed=sealed,
    )
