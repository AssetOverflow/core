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
import stat
import subprocess
import tempfile
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from recognition.anti_unifier import DerivedRecognizer
from teaching.discovery import DiscoveryCandidate


def _atomic_write_text(target: Path, content: str, *, encoding: str = "utf-8") -> None:
    """ADR-0156 (W-022) — atomic checkpoint write.

    Write ``content`` to a temp file in the same directory as ``target``,
    fsync it, then ``os.replace`` it into place. Same-directory rename is
    atomic on POSIX (and on Windows since Python 3.3 via ``os.replace``).
    A SIGINT/SIGKILL between ``write`` and ``replace`` leaves the prior
    target file fully intact.

    Existing file mode bits are preserved when replacing a prior checkpoint
    file so engine-state readers do not silently lose access after a save.
    """
    target.parent.mkdir(parents=True, exist_ok=True)

    existing_mode: int | None = None
    if target.exists():
        existing_mode = stat.S_IMODE(target.stat().st_mode)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            tmp_path = Path(fh.name)
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())

        if existing_mode is not None and tmp_path is not None:
            os.chmod(tmp_path, existing_mode)

        os.replace(tmp_path, target)
    except BaseException:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        raise

_SCHEMA_VERSION = 1
_DEFAULT_DIR = (
    Path(os.environ["CORE_ENGINE_STATE_DIR"])
    if os.environ.get("CORE_ENGINE_STATE_DIR")
    else Path(__file__).parents[1] / "engine_state"
)


@lru_cache(maxsize=1)
def get_git_revision() -> str:
    """Return the current short git revision once per process.

    Public helper for runtime audit surfaces that need the same revision
    value used by engine-state manifests and revision-mismatch warnings.
    Cached to avoid duplicate subprocess calls during startup.
    """
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


def _git_revision() -> str:
    """Backward-compatible private alias; use get_git_revision() in new code."""
    return get_git_revision()


class IncompatibleEngineStateError(RuntimeError):
    """Raised when an engine-state checkpoint was written by a NEWER schema than
    this build supports (L10 step-2 migration discipline).  Older/equal versions
    are tolerated via additive-optional defaults; a newer checkpoint is refused
    rather than silently mis-loaded.
    """


class EngineStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _DEFAULT_DIR

    def save_recognizers(self, recognizers: Sequence[DerivedRecognizer]) -> None:
        lines = [r.to_json() for r in recognizers]
        _atomic_write_text(
            self.path / "recognizers.jsonl",
            "\n".join(lines) + ("\n" if lines else ""),
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
        lines = [
            json.dumps(c.as_dict(), sort_keys=True, separators=(",", ":"))
            for c in candidates
        ]
        _atomic_write_text(
            self.path / "discovery_candidates.jsonl",
            "\n".join(lines) + ("\n" if lines else ""),
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
        manifest = {
            "schema_version": _SCHEMA_VERSION,
            "turn_count": turn_count,
            "written_at_revision": get_git_revision(),
        }
        _atomic_write_text(
            self.path / "manifest.json",
            json.dumps(manifest, sort_keys=True, indent=2),
        )

    def load_manifest(self) -> dict | None:
        p = self.path / "manifest.json"
        if not p.exists():
            return None
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            return None
        manifest = json.loads(content)
        # L10 step-2 migration discipline: tolerate schema_version <= current
        # (additive-optional fields read via defaults); REFUSE a newer checkpoint
        # rather than silently mis-load state written by code we don't understand.
        stored_version = manifest.get("schema_version", 0)
        if not isinstance(stored_version, int) or stored_version > _SCHEMA_VERSION:
            raise IncompatibleEngineStateError(
                f"engine_state manifest schema_version {stored_version!r} is newer "
                f"than this build supports ({_SCHEMA_VERSION}). Refusing to load: a "
                "newer checkpoint cannot be safely read by older code. Run the "
                "matching build, or clear engine_state/ explicitly."
            )
        # W-023 / ADR-0157 — revision-mismatch warning per ADR-0146 §Risks line 127.
        # Never refuse to load; reboot is recovery, not control flow.
        stored_rev = manifest.get("written_at_revision", "unknown")
        current_rev = get_git_revision()
        if stored_rev not in ("unknown", "") and current_rev not in ("unknown", "") and stored_rev != current_rev:
            warnings.warn(
                f"engine_state checkpoint was written at revision {stored_rev!r} "
                f"but the current revision is {current_rev!r}. "
                "State may be stale after a code change. "
                "Clear engine_state/ if you observe unexpected behaviour.",
                RuntimeWarning,
                stacklevel=2,
            )
        return manifest

    def exists(self) -> bool:
        return (self.path / "manifest.json").exists()


__all__ = ["EngineStateStore", "IncompatibleEngineStateError", "get_git_revision"]
