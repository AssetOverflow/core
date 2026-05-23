"""Pin scripts/verify_lane_shas.py's pin-block shape.

The full verify-all suite (which re-runs every lane) is expensive
(~30s). It is exercised in CI by the lane-shas workflow. Locally
``pytest`` covers two cheaper guarantees:

1. Every shipped ADR lane has a pin in ``PINNED_SHAS``.
2. Every ``LaneSpec.runner_module`` actually exists on disk and is
   marked as a Python file.

These two together mean no lane silently drops out of CI coverage.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_verifier_module():
    """Load scripts/verify_lane_shas.py as a module.

    The scripts directory is not on the default import path; load
    directly so the pins/specs remain authoritative without forcing a
    package reshuffle.
    """
    path = REPO_ROOT / "scripts" / "verify_lane_shas.py"
    spec = importlib.util.spec_from_file_location("_verify_lane_shas", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_verify_lane_shas"] = module
    spec.loader.exec_module(module)
    return module


verifier = _load_verifier_module()


class TestPinBlockShape:
    def test_every_lane_spec_has_a_pin(self) -> None:
        lane_ids = {spec.lane_id for spec in verifier.LANE_SPECS}
        pinned = set(verifier.PINNED_SHAS.keys())
        missing = lane_ids - pinned
        assert not missing, f"lanes without pinned SHA: {missing}"

    def test_no_orphan_pins(self) -> None:
        """A pin without a matching LaneSpec is dead code."""
        lane_ids = {spec.lane_id for spec in verifier.LANE_SPECS}
        pinned = set(verifier.PINNED_SHAS.keys())
        orphans = pinned - lane_ids
        assert not orphans, f"orphan pins (no matching LaneSpec): {orphans}"

    def test_every_pin_is_64_hex_chars(self) -> None:
        for lane_id, sha in verifier.PINNED_SHAS.items():
            assert re.fullmatch(r"[0-9a-f]{64}", sha), (
                f"pin for {lane_id!r} is not a 64-char hex SHA-256: {sha!r}"
            )

    def test_every_lane_spec_runner_exists(self) -> None:
        for spec in verifier.LANE_SPECS:
            assert spec.runner_path.exists(), (
                f"lane {spec.lane_id!r} runner not found at {spec.runner_path}"
            )
            assert spec.runner_path.suffix == ".py"

    def test_every_lane_spec_canonical_report_path_under_repo(self) -> None:
        for spec in verifier.LANE_SPECS:
            assert spec.canonical_report.is_relative_to(REPO_ROOT)


class TestExpectedLaneCoverage:
    """The verifier MUST cover all six ADR-0092..0099 lanes.

    Hard-code the canonical lane ids so silently dropping any one
    fails this test. ADR-0094 and ADR-0097 are schema/ratification
    only — no eval lane — and intentionally absent.
    """

    EXPECTED_LANES = frozenset(
        {
            "reviewer_registry",  # ADR-0092
            "miner_loop_closure",  # ADR-0095
            "domain_contract_validation",  # ADR-0093
            "fabrication_control_summary",  # ADR-0096
            "demo_composition",  # ADR-0098
            "public_demo",  # ADR-0099
            "curriculum_loop_closure",
        }
    )

    def test_all_expected_lanes_covered(self) -> None:
        actual = {spec.lane_id for spec in verifier.LANE_SPECS}
        missing = self.EXPECTED_LANES - actual
        extra = actual - self.EXPECTED_LANES
        assert not missing, f"missing expected lanes: {missing}"
        assert not extra, (
            f"unexpected extra lanes: {extra} (add to EXPECTED_LANES in test "
            "if intentional)"
        )
