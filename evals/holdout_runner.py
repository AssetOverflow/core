"""Holdout runner — scores sealed test sets without exposing item-level results.

Trust boundary:
- Reads sealed encrypted holdouts.
- Emits aggregate metrics only.
- Must never persist decrypted case content to disk.
- Must fail closed when a decryption identity is explicitly supplied but
  decryption cannot complete.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyrage import decrypt
from pyrage import x25519

from evals.framework import LaneInfo, load_lane_runner, load_cases

HOLDOUT_KEY_ENV = "CORE_HOLDOUT_KEY"


@dataclass(frozen=True, slots=True)
class HoldoutResult:
    lane: str
    metrics: dict[str, Any]
    sealed: bool


def _parse_cases(raw: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def _decrypt_holdout(encrypted_path: Path) -> list[dict[str, Any]]:
    """Decrypt a sealed holdout file.

    Development fallback semantics:
    - If CORE_HOLDOUT_KEY is unset and plaintext fallback exists,
      plaintext is allowed for local eval iteration.

    Fail-closed semantics:
    - If CORE_HOLDOUT_KEY is set, decryption MUST succeed.
    - No plaintext fallback is permitted once an identity is supplied.
    """
    key_path = os.environ.get(HOLDOUT_KEY_ENV)

    plaintext_path = encrypted_path.parent / "cases_plaintext.jsonl"
    if key_path is None:
        if plaintext_path.exists():
            return load_cases(plaintext_path)
        raise EnvironmentError(
            f"Set {HOLDOUT_KEY_ENV} or provide cases_plaintext.jsonl "
            "for local development fallback."
        )

    if not encrypted_path.exists():
        raise FileNotFoundError(
            f"Encrypted holdout not found: {encrypted_path}"
        )

    identity_path = Path(key_path)
    if not identity_path.exists():
        raise FileNotFoundError(
            f"Holdout identity not found: {identity_path}"
        )

    try:
        identity_text = identity_path.read_text(encoding="utf-8")
        identities = [
            x25519.Identity.from_str(line.strip())
            for line in identity_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not identities:
            raise ValueError("no age identity entries found in identity file")
        encrypted_bytes = encrypted_path.read_bytes()
        decrypted = decrypt(encrypted_bytes, identities)
        return _parse_cases(decrypted.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to decrypt sealed holdout: {encrypted_path}"
        ) from exc


def run_holdout(
    lane: LaneInfo,
    *,
    version: str = "v1",
    config: Any = None,
) -> HoldoutResult:
    holdout_dir = lane.root / "holdouts"
    if not holdout_dir.exists():
        raise FileNotFoundError(f"No holdouts directory: {holdout_dir}")

    encrypted_path = lane.holdout_cases_path_sealed(version)
    cases = _decrypt_holdout(encrypted_path)

    runner_module = load_lane_runner(lane)
    report = runner_module.run_lane(cases, config=config)

    return HoldoutResult(
        lane=lane.name,
        metrics=report.metrics,
        sealed=os.environ.get(HOLDOUT_KEY_ENV) is not None,
    )
