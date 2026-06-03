"""ADR-0157 (W-023) — revision-mismatch warning on engine-state load.

ADR-0146 §Risks line 127:
  Compare written_at_revision in manifest.json with the current git SHA.
  If they mismatch, log a warning but continue startup (do not refuse to
  start, as a reboot is recovery, not control flow).
"""

from __future__ import annotations

import json
import warnings
from unittest.mock import patch

import pytest

from engine_state import EngineStateStore


def _write_manifest(path, revision: str, schema_version: int = 1, turn_count: int = 3) -> None:
    manifest = {
        "schema_version": schema_version,
        "turn_count": turn_count,
        "written_at_revision": revision,
    }
    (path / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8"
    )


def test_matching_revision_emits_no_warning(tmp_path) -> None:
    _write_manifest(tmp_path, revision="abc123def456")
    store = EngineStateStore(tmp_path)

    with patch("engine_state.get_git_revision", return_value="abc123def456"):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            manifest = store.load_manifest()

    assert manifest is not None
    assert manifest["written_at_revision"] == "abc123def456"


def test_mismatched_revision_emits_runtime_warning(tmp_path) -> None:
    _write_manifest(tmp_path, revision="oldrevisionabc")
    store = EngineStateStore(tmp_path)

    with patch("engine_state.get_git_revision", return_value="newrevisionxyz"):
        with pytest.warns(RuntimeWarning, match="oldrevisionabc"):
            manifest = store.load_manifest()

    assert manifest is not None


def test_warning_message_contains_both_revisions(tmp_path) -> None:
    _write_manifest(tmp_path, revision="stored000000")
    store = EngineStateStore(tmp_path)

    with patch("engine_state.get_git_revision", return_value="current11111"):
        with pytest.warns(RuntimeWarning) as record:
            store.load_manifest()

    assert len(record) == 1
    msg = str(record[0].message)
    assert "stored000000" in msg
    assert "current11111" in msg


def test_manifest_returned_intact_despite_mismatch(tmp_path) -> None:
    _write_manifest(tmp_path, revision="old", turn_count=42)
    store = EngineStateStore(tmp_path)

    with patch("engine_state.get_git_revision", return_value="new"):
        with pytest.warns(RuntimeWarning):
            manifest = store.load_manifest()

    assert manifest is not None
    assert manifest["turn_count"] == 42
    assert manifest["schema_version"] == 1
    assert manifest["written_at_revision"] == "old"


def test_stored_unknown_revision_suppresses_warning(tmp_path) -> None:
    _write_manifest(tmp_path, revision="unknown")
    store = EngineStateStore(tmp_path)

    with patch("engine_state.get_git_revision", return_value="abc123"):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            manifest = store.load_manifest()

    assert manifest is not None


def test_current_unknown_revision_suppresses_warning(tmp_path) -> None:
    _write_manifest(tmp_path, revision="abc123def456")
    store = EngineStateStore(tmp_path)

    with patch("engine_state.get_git_revision", return_value="unknown"):
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            manifest = store.load_manifest()

    assert manifest is not None


def test_missing_manifest_returns_none_no_warning(tmp_path) -> None:
    store = EngineStateStore(tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result = store.load_manifest()

    assert result is None


def test_empty_manifest_returns_none_no_warning(tmp_path) -> None:
    (tmp_path / "manifest.json").write_text("", encoding="utf-8")
    store = EngineStateStore(tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        result = store.load_manifest()

    assert result is None
