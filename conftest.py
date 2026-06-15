"""Project-root conftest — quarantine registry for known-failing tests.

The QUARANTINE set lists test IDs that are pre-existing failures
predating the substrate-liveness audit work (verified via bisect
against c1a1b7a, the commit immediately before the first W-* PR
of 2026-05-24). The CI gate at .github/workflows/full-pytest.yml
runs ``pytest -m "not quarantine"`` so these failures do not block
PRs, but the suite is a ratchet: a quarantined test removed from
this set must pass on its own merits.

See docs/test-debt-quarantine.md for cluster diagnoses, removal
policy, and the per-test rationale.

To remove a test from quarantine:
  1. Land a PR that makes the test pass.
  2. Delete its entry from QUARANTINE in the same PR.
  3. The full-pytest CI gate will now require it to keep passing.

Adding a test to QUARANTINE is strongly discouraged. If a new
failure surfaces, the right default is to fix it in the PR that
caused it — not to quarantine. The set should only shrink.
"""

from __future__ import annotations

import pytest

import engine_state


_USES_DEFAULT_ENGINE_STATE_MARKER = "uses_default_engine_state"


@pytest.fixture(autouse=True)
def _isolate_engine_state_default(request, tmp_path_factory, monkeypatch):
    """Isolate the default engine-state checkpoint dir per test.

    A bare ``ChatRuntime()`` (no ``engine_state_path``) falls back to
    ``engine_state._DEFAULT_DIR`` — the shared repo ``engine_state/`` directory.
    Tests must not share that mutable dir: one test's checkpoint (recognizers,
    candidates, the stamped engine-identity, and — under resume mode — the lived
    session_state) leaks into another test's fresh-state assumptions (and, since
    L11, raises spurious identity-continuity-break warnings when a later test
    boots under a different identity over the same dir). Point the default at a
    fresh per-test temp dir. Tests passing an explicit ``engine_state_path`` are
    unaffected; within one test, repeated ``ChatRuntime()`` share this dir.

    Two redirections, both pointed at the same per-test dir:

    1. ``engine_state._DEFAULT_DIR`` is monkeypatched directly. It is bound at
       import (``engine_state/__init__.py``), so an env var alone would NOT
       redirect an already-imported in-process runtime.
    2. ``CORE_ENGINE_STATE_DIR`` is set in the environment so subprocess / CLI
       tests that re-import ``engine_state`` in a child process inherit the same
       isolation. A child that sets its own ``CORE_ENGINE_STATE_DIR`` (e.g.
       ``tests/test_l10_always_on_daemon.py::test_real_sigterm_stops_the_daemon_cleanly``)
       still overrides this and wins.

    A test that intentionally exercises the real process-default dir (default-dir
    semantics, CLI fallback, legacy-flat migration) can opt out with
    ``@pytest.mark.uses_default_engine_state``; it then sees neither redirection.
    """
    if request.node.get_closest_marker(_USES_DEFAULT_ENGINE_STATE_MARKER):
        return
    isolated = tmp_path_factory.mktemp("engine_state_default")
    monkeypatch.setattr(engine_state, "_DEFAULT_DIR", isolated)
    monkeypatch.setenv("CORE_ENGINE_STATE_DIR", str(isolated))


QUARANTINE: frozenset[str] = frozenset()


def pytest_collection_modifyitems(config, items):
    """Stamp the quarantine marker on any test whose nodeid is listed
    in QUARANTINE.  Tests not in the set are unaffected.

    The CI gate runs ``pytest -m "not quarantine"`` so quarantined
    tests are silently skipped in CI.  Local ``pytest`` runs include
    them by default (still useful for debugging individual fixes).
    """
    _ = config  # pluggy hook signature requires the name `config`; not used here
    quarantine_marker = pytest.mark.quarantine
    for item in items:
        if item.nodeid in QUARANTINE:
            item.add_marker(quarantine_marker)
