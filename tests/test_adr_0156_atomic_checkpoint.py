"""ADR-0156 (W-022) — atomic engine-state checkpoint writes.

ADR-0146 §"File Operations and Invariants" specified:

  "Checkpointing must be atomic (e.g., write to temporary file and
   rename) to prevent corruption if the process is terminated
   mid-write."

Pre-W-022 the three save_* methods on ``EngineStateStore`` used
``Path.write_text`` directly, which truncated the target before
writing.  A SIGINT/SIGKILL between truncate and full-write left a
partial / empty file on disk, breaking the next process's load.

This test suite pins:

  1. Round-trip equality survives atomic write (no semantic drift).
  2. Failed replace leaves the prior target file intact.
  3. Failed replace cleans up the temp file.
  4. The temp file lives in the same directory as the target
     (required for ``os.replace`` to be atomic on POSIX).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from engine_state import EngineStateStore, _atomic_write_text


# ---------------------------------------------------------------------------
# Direct helper-level tests
# ---------------------------------------------------------------------------


def test_atomic_write_creates_target(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"
    _atomic_write_text(target, '{"k":1}')
    assert target.read_text() == '{"k":1}'


def test_atomic_write_overwrites_existing(tmp_path: Path) -> None:
    target = tmp_path / "recognizers.jsonl"
    target.write_text("old")
    _atomic_write_text(target, "new")
    assert target.read_text() == "new"


def test_atomic_write_creates_parent_dir(tmp_path: Path) -> None:
    target = tmp_path / "engine_state" / "manifest.json"
    _atomic_write_text(target, "{}")
    assert target.exists()


def test_failed_replace_preserves_prior_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If ``os.replace`` raises, the prior target file must be intact
    and the partial new content must not be visible to readers."""
    target = tmp_path / "manifest.json"
    target.write_text("PRIOR")

    def _boom(src, dst):  # noqa: ANN001
        raise OSError("simulated crash between write+rename")

    monkeypatch.setattr("engine_state.os.replace", _boom)
    with pytest.raises(OSError, match="simulated"):
        _atomic_write_text(target, "NEW")

    assert target.read_text() == "PRIOR", (
        "atomic write must leave prior target intact on rename failure"
    )


def test_failed_replace_cleans_up_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "manifest.json"
    target.write_text("PRIOR")

    def _boom(src, dst):  # noqa: ANN001
        raise OSError("simulated")

    monkeypatch.setattr("engine_state.os.replace", _boom)
    with pytest.raises(OSError):
        _atomic_write_text(target, "NEW")

    # No orphan temp files in the directory (target dir is otherwise empty).
    leftover = [
        p
        for p in tmp_path.iterdir()
        if p.name.startswith(".manifest.json") and p.name.endswith(".tmp")
    ]
    assert leftover == [], (
        f"failed atomic write must clean up temp file; found {leftover}"
    )


def test_temp_file_lives_in_target_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Required for ``os.replace`` to be atomic on POSIX — cross-
    filesystem renames are not atomic."""
    target = tmp_path / "subdir" / "manifest.json"
    target.parent.mkdir()
    captured: list[Path] = []

    real_replace = os.replace

    def _capture(src, dst):  # noqa: ANN001
        captured.append(Path(src))
        return real_replace(src, dst)

    monkeypatch.setattr("engine_state.os.replace", _capture)
    _atomic_write_text(target, "ok")
    assert captured, "os.replace must be called"
    assert captured[0].parent == target.parent, (
        f"temp file must be in target's directory; "
        f"got {captured[0].parent} vs {target.parent}"
    )


# ---------------------------------------------------------------------------
# Store-level tests (recognizers, candidates, manifest)
# ---------------------------------------------------------------------------


def test_save_manifest_failure_preserves_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = EngineStateStore(tmp_path)
    store.save_manifest(1)
    prior = (tmp_path / "manifest.json").read_text()

    monkeypatch.setattr(
        "engine_state.os.replace",
        lambda *a, **k: (_ for _ in ()).throw(OSError("boom")),
    )
    with pytest.raises(OSError):
        store.save_manifest(2)

    assert (tmp_path / "manifest.json").read_text() == prior


def test_save_recognizers_failure_preserves_prior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from recognition.anti_unifier import Constant, DerivedRecognizer, TypedSlot

    store = EngineStateStore(tmp_path)
    seed = DerivedRecognizer(
        pattern=(
            Constant("light"),
            TypedSlot(
                feature_name="object",
                slot_type="noun",
                min_width=1,
                max_width=2,
                ignored_prefix_tokens=("the",),
            ),
        ),
        teaching_set_id="set-1",
        constant_features={"intent": "definition"},
        absent_features={"negated": 0},
    )
    store.save_recognizers([seed])
    prior = (tmp_path / "recognizers.jsonl").read_text()

    monkeypatch.setattr(
        "engine_state.os.replace",
        lambda *a, **k: (_ for _ in ()).throw(OSError("boom")),
    )
    with pytest.raises(OSError):
        store.save_recognizers([])

    assert (tmp_path / "recognizers.jsonl").read_text() == prior


def test_round_trip_unchanged_after_atomic_refactor(tmp_path: Path) -> None:
    """Regression guard — the atomic refactor must not change content."""
    store = EngineStateStore(tmp_path)
    store.save_manifest(42)
    store.save_recognizers([])
    store.save_discovery_candidates([])

    manifest = store.load_manifest()
    assert manifest is not None
    assert manifest == {
        "schema_version": 1,
        "turn_count": 42,
        "written_at_revision": manifest["written_at_revision"],
    }
    assert store.load_recognizers() == []
    assert store.load_discovery_candidates() == []
