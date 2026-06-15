"""Generation-dir checkpoint persistence (ADR-0146 / ADR-0156 / ADR-0219).

engine_state/ is the mutable checkpoint directory for per-session engine
state that must survive reboot.  Each checkpoint is now an atomic committed
**generation**: a complete, fsync-ed ``gen-NNNN/`` directory pointed to by a
single ``current`` file whose atomic replacement is the commit boundary.

Layout (ADR-0219 generation-dir model):
  engine_state/
    gen-0041/
      recognizers.jsonl          -- one DerivedRecognizer per line
      discovery_candidates.jsonl -- one DiscoveryCandidate per line
      session_state.json         -- bit-exact field/vault/anchor/graph snapshot
      manifest.json              -- schema_version, git revision, turn_count
    current                      -- one line: "gen-0041"; pointer swap = commit

Commit is the single atomic ``os.replace`` of ``current``.  A kill before the
swap leaves the prior ``current`` intact (the prior generation is the committed
state).  A kill after the swap commits the new generation.  Incomplete
``gen-NNNN/`` directories without a ``current`` entry are garbage, ignored.

**Legacy (flat) layout — read-only fallback and migration:**
A pre-0219 flat ``engine_state/`` (manifest.json at root, no ``current``)
is read transparently by all ``load_*`` methods.  On the first
``begin_generation()`` call, flat files are copied into ``gen-0000/`` and
``current`` is written; subsequent checkpoints use the generation model.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
import subprocess
import tempfile
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from recognition.anti_unifier import DerivedRecognizer
from teaching.discovery import DiscoveryCandidate

_logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 2  # v2 adds session_state.json (Shape B+ lived-state persistence)
_GEN_PREFIX = "gen-"
_CURRENT_FILE = "current"

_DEFAULT_DIR = (
    Path(os.environ["CORE_ENGINE_STATE_DIR"])
    if os.environ.get("CORE_ENGINE_STATE_DIR")
    else Path(__file__).parents[1] / "engine_state"
)


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


def _fsync_dir(dir_path: Path) -> None:
    """Fsync a directory file descriptor.

    Required for POSIX crash-safety: fsyncing directory metadata makes
    rename/create operations inside it durable.  Called after all files in a
    generation directory are written (before pointer swap) and after the
    pointer swap itself (to make the new ``current`` durable).
    """
    fd = os.open(str(dir_path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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
    """Manages the engine-state checkpoint directory.

    Two layouts are supported:

    - **Generation-dir** (ADR-0219): ``gen-NNNN/`` dirs pointed to by
      ``current``.  ``begin_generation`` + ``commit_generation`` form the
      two-phase commit.  This is the active layout for all new writes.

    - **Flat** (legacy pre-0219): files at the store root.  ``load_*``
      methods fall back to this when no ``current`` file exists, so old
      checkpoints are readable without migration.  The first
      ``begin_generation`` call migrates flat state into ``gen-0000/`` and
      writes ``current``.

    The ``save_*`` / ``load_*`` methods write/read relative to ``self.path``
    directly.  In the generation-dir model, callers pass a temporary
    ``EngineStateStore(gen_dir)`` instance so ``save_*`` naturally writes
    into the pending generation directory.  Load methods resolve the active
    generation via ``_resolve_dir()`` (or ``self.path`` for flat layout).
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _DEFAULT_DIR

    # ------------------------------------------------------------------
    # Generation-dir protocol (ADR-0219)
    # ------------------------------------------------------------------

    def _current_gen_dir(self) -> Path | None:
        """Return the currently committed generation directory, or None.

        Returns None when no ``current`` file exists (flat layout or fresh
        store) or when the pointed-to directory does not exist.
        """
        current_file = self.path / _CURRENT_FILE
        if not current_file.exists():
            return None
        gen_name = current_file.read_text(encoding="utf-8").strip()
        gen_dir = self.path / gen_name
        return gen_dir if gen_dir.is_dir() else None

    def _resolve_dir(self) -> Path:
        """Return the directory to read checkpoint files from.

        Generation-dir layout: the committed gen dir (resolved via ``current``).
        Flat / fresh layout: ``self.path`` directly.
        """
        gen_dir = self._current_gen_dir()
        return gen_dir if gen_dir is not None else self.path

    def begin_generation(self) -> tuple[int, Path]:
        """Allocate the next pending generation directory and return (gen_num, gen_dir).

        If a flat-layout checkpoint exists at the store root (pre-0219 migration),
        it is atomically wrapped into ``gen-0000/`` and ``current`` is written
        before the new generation is allocated.  This migration happens at most
        once per store.

        The returned ``gen_dir`` is an empty (or freshly created) directory.
        Write all checkpoint files into it, then call ``commit_generation``.
        An exception before ``commit_generation`` leaves the prior committed
        generation intact — the incomplete ``gen-NNNN/`` is treated as garbage
        on the next load (no ``current`` update occurred).
        """
        current_file = self.path / _CURRENT_FILE
        if not current_file.exists():
            flat_manifest = self.path / "manifest.json"
            if flat_manifest.exists():
                # Migrate flat layout into gen-0000 before proceeding.
                gen0 = self.path / f"{_GEN_PREFIX}0000"
                gen0.mkdir(parents=True, exist_ok=True)
                for fname in (
                    "manifest.json",
                    "recognizers.jsonl",
                    "discovery_candidates.jsonl",
                    "session_state.json",
                ):
                    src = self.path / fname
                    if src.exists():
                        shutil.copy2(src, gen0 / fname)
                _fsync_dir(gen0)
                _atomic_write_text(current_file, f"{_GEN_PREFIX}0000")
                _fsync_dir(self.path)
                _logger.info("engine_state: migrated flat layout to gen-0000")
                next_num = 1
            else:
                # Fresh store — first generation.
                next_num = 0
        else:
            current_name = current_file.read_text(encoding="utf-8").strip()
            current_num = int(current_name[len(_GEN_PREFIX):])
            next_num = current_num + 1

        gen_name = f"{_GEN_PREFIX}{next_num:04d}"
        gen_dir = self.path / gen_name
        gen_dir.mkdir(parents=True, exist_ok=True)
        return next_num, gen_dir

    def commit_generation(self, gen_num: int, *, keep: int = 2) -> None:
        """Atomically commit a completed generation as the new checkpoint.

        Sequence (all steps needed for POSIX crash-safety):
        1. Fsync the generation directory (content durability).
        2. Atomic ``os.replace`` of ``current`` pointer (the commit).
        3. Fsync the parent directory (pointer-rename metadata durability).
        4. GC old generations, retaining the last ``keep`` committed ones.

        A SIGKILL before step 2 leaves the prior ``current`` intact.
        A SIGKILL between steps 2 and 3 may lose the pointer on a hard
        crash, but ``os.replace`` is atomic at the kernel level so the
        pointer is either the old or the new value — never torn.
        """
        gen_name = f"{_GEN_PREFIX}{gen_num:04d}"
        gen_dir = self.path / gen_name
        _fsync_dir(gen_dir)
        _atomic_write_text(self.path / _CURRENT_FILE, gen_name)
        _fsync_dir(self.path)
        pruned = self._gc_old_generations(committed_num=gen_num, keep=keep)
        if pruned:
            _logger.debug("engine_state GC: pruned old generations %s", pruned)

    def _gc_old_generations(self, *, committed_num: int, keep: int = 2) -> list[str]:
        """Prune generation directories older than the retention window.

        Retains the ``keep`` most-recent committed generations (including
        the just-committed one).  Unreferenced gen dirs from an in-progress
        write (gen_num > committed_num) are left alone — they are garbage
        by definition but harmless, and pruning them here would require
        knowing which one is in-progress, which we do not.
        """
        cutoff = committed_num - keep + 1  # prune gen_num < cutoff
        pruned: list[str] = []
        try:
            for item in self.path.iterdir():
                if not item.is_dir() or not item.name.startswith(_GEN_PREFIX):
                    continue
                try:
                    num = int(item.name[len(_GEN_PREFIX):])
                except ValueError:
                    continue
                if num < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    pruned.append(item.name)
        except OSError:
            pass  # best-effort; GC failure never blocks a checkpoint
        return sorted(pruned)

    # ------------------------------------------------------------------
    # Save methods — write to self.path (used both for flat layout and,
    # via EngineStateStore(gen_dir), to write into a pending generation).
    # ------------------------------------------------------------------

    def save_recognizers(self, recognizers: Sequence[DerivedRecognizer]) -> None:
        lines = [r.to_json() for r in recognizers]
        _atomic_write_text(
            self.path / "recognizers.jsonl",
            "\n".join(lines) + ("\n" if lines else ""),
        )

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

    def save_manifest(
        self,
        turn_count: int,
        *,
        engine_identity: str = "",
        parent_engine_identity: str = "",
        identity_scheme: int = 2,
    ) -> None:
        """Write the checkpoint manifest.

        In the generation-dir model, the manifest is the last file written
        into the pending gen dir; ``commit_generation`` then swaps the
        ``current`` pointer.  The manifest is no longer the commit boundary —
        the pointer swap is.

        ``engine_identity`` (L11) stamps the content-derived identity the
        engine was running under when this checkpoint was written.
        ``parent_engine_identity`` links it to the identity of the prior
        checkpoint, forming a lineage chain.  Both are additive-optional.

        ``identity_scheme`` (ADR-0220) records WHICH formula produced
        ``engine_identity``: ``2`` = packs-only (current);
        absent / ``< 2`` on an old manifest = the legacy packs+code_revision
        hash, recognised by the load guard for a verifying migration. Stamped
        only when ``engine_identity`` is. Additive-optional — does NOT bump
        ``schema_version`` (``core.engine_identity.ENGINE_IDENTITY_SCHEME`` is
        the canonical value; the literal default mirrors it to avoid an import
        cycle).
        """
        manifest: dict = {
            "schema_version": _SCHEMA_VERSION,
            "turn_count": turn_count,
            "written_at_revision": get_git_revision(),
        }
        if engine_identity:
            manifest["engine_identity"] = engine_identity
            manifest["identity_scheme"] = identity_scheme
        if parent_engine_identity:
            manifest["parent_engine_identity"] = parent_engine_identity
        _atomic_write_text(
            self.path / "manifest.json",
            json.dumps(manifest, sort_keys=True, indent=2),
        )

    def save_session_state(self, snapshot: dict) -> None:
        """Persist the lived session state (Shape B+ / schema v2).

        ``snapshot`` is ``SessionContext.snapshot()`` — a bit-exact, JSON-safe
        dict of the field, vault, anchor, graph, referents, and dialogue.
        In the generation-dir model, written before ``save_manifest`` inside
        the pending gen dir.
        """
        _atomic_write_text(
            self.path / "session_state.json",
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")),
        )

    # ------------------------------------------------------------------
    # Load methods — resolve via _resolve_dir() (gen dir or flat root).
    # ------------------------------------------------------------------

    def load_recognizers(self) -> list[DerivedRecognizer]:
        p = self._resolve_dir() / "recognizers.jsonl"
        if not p.exists():
            return []
        return [
            DerivedRecognizer.from_json(line)
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def load_discovery_candidates(self) -> list[DiscoveryCandidate]:
        p = self._resolve_dir() / "discovery_candidates.jsonl"
        if not p.exists():
            return []
        return [
            DiscoveryCandidate.from_dict(json.loads(line))
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def load_manifest(self) -> dict | None:
        p = self._resolve_dir() / "manifest.json"
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
        if (
            stored_rev not in ("unknown", "")
            and current_rev not in ("unknown", "")
            and stored_rev != current_rev
        ):
            warnings.warn(
                f"engine_state checkpoint was written at revision {stored_rev!r} "
                f"but the current revision is {current_rev!r}. "
                "State may be stale after a code change. "
                "Clear engine_state/ if you observe unexpected behaviour.",
                RuntimeWarning,
                stacklevel=2,
            )
        return manifest

    def load_session_state(self) -> dict | None:
        """Load the lived session state, or None when absent (v1 checkpoint).

        A v1 checkpoint has no ``session_state.json`` — returning None lets the
        caller fall back to a fresh session (the historical Shape B behavior).
        """
        p = self._resolve_dir() / "session_state.json"
        if not p.exists():
            return None
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            return None
        return json.loads(content)

    def exists(self) -> bool:
        """True if a committed checkpoint exists (generation-dir or flat layout)."""
        # Generation-dir layout: current pointer exists and points to a gen dir.
        if (self.path / _CURRENT_FILE).exists():
            return self._current_gen_dir() is not None
        # Flat legacy layout: manifest at root.
        return (self.path / "manifest.json").exists()


__all__ = ["EngineStateStore", "IncompatibleEngineStateError", "get_git_revision"]
