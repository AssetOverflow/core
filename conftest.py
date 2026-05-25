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
