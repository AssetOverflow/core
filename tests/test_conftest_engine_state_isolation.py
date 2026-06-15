"""Proof tests for the root-conftest engine-state isolation fixture.

Covers ``conftest.py::_isolate_engine_state_default`` and the recommended fix in
``docs/issues/default-engine-state-test-hygiene.md``.  Each assertion fails if the
corresponding half of the fixture is removed, so these are load-bearing, not
decoration (CLAUDE.md "Schema-Defined Proof Obligations"):

- drop the ``monkeypatch.setattr`` → ``test_default_dir_is_redirected_*`` fails,
- drop the ``monkeypatch.setenv`` → ``test_env_var_matches_*`` fails,
- drop the marker opt-out check → ``test_opt_out_marker_*`` fails.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import engine_state


def test_default_dir_is_redirected_to_isolated_tmp() -> None:
    """(req #1) the import-time-bound module attribute is redirected per test."""
    default_dir = Path(engine_state._DEFAULT_DIR)
    assert "engine_state_default" in str(default_dir), (
        "fixture did not monkeypatch engine_state._DEFAULT_DIR to an isolated dir"
    )
    repo_default = Path(engine_state.__file__).resolve().parents[1] / "engine_state"
    assert default_dir.resolve() != repo_default.resolve(), (
        "isolated default dir must not be the in-repo engine_state/ dir"
    )


def test_env_var_matches_the_isolated_default_dir() -> None:
    """(req #2) CORE_ENGINE_STATE_DIR is set for child processes, to the SAME dir."""
    env_dir = os.environ.get("CORE_ENGINE_STATE_DIR")
    assert env_dir is not None, "fixture did not set CORE_ENGINE_STATE_DIR"
    assert env_dir == str(engine_state._DEFAULT_DIR), (
        "CORE_ENGINE_STATE_DIR and engine_state._DEFAULT_DIR must agree so an "
        "in-process runtime and a subprocess child resolve the same isolated dir"
    )


@pytest.mark.uses_default_engine_state
def test_opt_out_marker_skips_isolation() -> None:
    """(req #3) the marker opts a test out of both redirections.

    Asserted as a contrast (not an absolute path) so it is robust whether or not
    CORE_ENGINE_STATE_DIR is set in the ambient environment: an opted-out test must
    NOT receive the per-test ``mktemp("engine_state_default")`` dir.
    """
    assert "engine_state_default" not in str(engine_state._DEFAULT_DIR), (
        "uses_default_engine_state marker did not opt out of the isolation fixture"
    )
