"""Shape B engine-state persistence (ADR-0146).

engine_state/ is the mutable checkpoint directory for per-session engine
state that must survive reboot. It is NOT append-only (unlike substrate-
state); each checkpoint overwrites the previous.

Layout:
  engine_state/recognizers.jsonl          -- one DerivedRecognizer per line
  engine_state/discovery_candidates.jsonl -- one DiscoveryCandidate per line
  engine_state/manifest.json              -- schema_version, git revision, turn_count
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Sequence

from recognition.anti_unifier import DerivedRecognizer
from teaching.discovery import DiscoveryCandidate

_SCHEMA_VERSION = 1
_DEFAULT_DIR = (
    Path(os.environ["CORE_ENGINE_STATE_DIR"])
    if os.environ.get("CORE_ENGINE_STATE_DIR")
    else Path(__file__).parents[1] / "engine_state"
)


def _git_revision() -> str:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "--short=12", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
            or "unknown"
        )
    except Exception:
        return "unknown"


class EngineStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _DEFAULT_DIR

    def save_recognizers(self, recognizers: Sequence[DerivedRecognizer]) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        lines = [r.to_json() for r in recognizers]
        (self.path / "recognizers.jsonl").write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )

    def load_recognizers(self) -> list[DerivedRecognizer]:
        p = self.path / "recognizers.jsonl"
        if not p.exists():
            return []
        return [
            DerivedRecognizer.from_json(line)
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def save_discovery_candidates(
        self,
        candidates: Sequence[DiscoveryCandidate],
    ) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(c.as_dict(), sort_keys=True, separators=(",", ":"))
            for c in candidates
        ]
        (self.path / "discovery_candidates.jsonl").write_text(
            "\n".join(lines) + ("\n" if lines else ""),
            encoding="utf-8",
        )

    def load_discovery_candidates(self) -> list[DiscoveryCandidate]:
        p = self.path / "discovery_candidates.jsonl"
        if not p.exists():
            return []
        return [
            DiscoveryCandidate.from_dict(json.loads(line))
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def save_manifest(self, turn_count: int) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": _SCHEMA_VERSION,
            "turn_count": turn_count,
            "written_at_revision": _git_revision(),
        }
        (self.path / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def load_manifest(self) -> dict | None:
        p = self.path / "manifest.json"
        if not p.exists():
            return None
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            return None
        return json.loads(content)

    def exists(self) -> bool:
        return (self.path / "manifest.json").exists()


__all__ = ["EngineStateStore"]
