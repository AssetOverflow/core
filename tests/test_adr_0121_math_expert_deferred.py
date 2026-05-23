"""ADR-0121 — first `expert` promotion attempt (mathematics_logic) deferred.

Pins five load-bearing invariants documented in
``docs/decisions/ADR-0121-mathematics-logic-expert-deferred.md``:

1. ``mathematics_logic`` ledger row stays at ``status="audit-passed"``;
   ``predicates.audit_passed == True``. No domain row carries the
   not-yet-implemented ``expert`` flag.

2. Lane runner against the sealed real GSM8K test produces
   ``correct_rate < 0.60`` (today: 0.0). The deferral's named blocker.

3. ``docs/reviewers.yaml`` carries NO ``expert_claims`` entry for
   ``mathematics_logic``.

4. The 10 ADR-0114a obligations all still pass for gsm8k_math; this
   deferral is on the contract-level correct_rate gate alone, not on
   any substrate regression. Indirectly verified by the existing
   Phase 5 test suite remaining green.

5. **Wrong-zero discipline holds against the sealed real GSM8K test.**
   The load-bearing positive claim of ADR-0121: even though the
   contract refuses, ``wrong == 0`` on the external benchmark.

Skip behavior: decryption-dependent invariants require
``CORE_HOLDOUT_KEY`` per ADR-0119.7's seal discipline. Tests skip
(do not fail) when the key is absent — CI runs do not need it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import yaml


_REPO_ROOT = Path(__file__).resolve().parent.parent
_REVIEWERS_PATH = _REPO_ROOT / "docs" / "reviewers.yaml"
_SEALED_PATH = (
    _REPO_ROOT / "evals" / "gsm8k_math" / "holdouts" / "v1" / "cases.jsonl.age"
)
_ADR_0120_CORRECT_RATE_FLOOR = 0.60


def _decrypt_or_skip() -> bytes:
    key_path_str = os.environ.get("CORE_HOLDOUT_KEY")
    if not key_path_str:
        pytest.skip("CORE_HOLDOUT_KEY not set; per ADR-0119.7 seal discipline")
    try:
        import pyrage
        from pyrage.x25519 import Identity
    except ImportError:
        pytest.skip("pyrage not installed")
    key_path = Path(key_path_str)
    if not key_path.exists():
        pytest.skip(f"CORE_HOLDOUT_KEY={key_path} does not exist")
    identity = Identity.from_str(key_path.read_text(encoding="utf-8").strip())
    return pyrage.decrypt(_SEALED_PATH.read_bytes(), [identity])


class TestMathRowStaysAtAuditPassed:
    """ADR-0121 invariant 1."""

    def test_ledger_reports_audit_passed_not_expert(self) -> None:
        from core.capability.reporting import ledger_report

        math_row = next(
            r
            for r in ledger_report()["domains"]
            if r["domain"] == "mathematics_logic"
        )
        assert math_row["status"] == "audit-passed", (
            f"mathematics_logic at {math_row['status']!r}; "
            f"ADR-0121 deferral requires it to remain at audit-passed"
        )
        assert math_row["predicates"]["audit_passed"] is True
        # `predicates.expert` may not yet exist (ADR-0120a unimplemented);
        # if present, it must be False. Either state is acceptable.
        expert_predicate = math_row["predicates"].get("expert")
        if expert_predicate is not None:
            assert expert_predicate is False


class TestSealedCorrectRateBelowFloor:
    """ADR-0121 invariant 2.

    The contract floor is documented in ADR-0120 as 0.60. The test
    pins ``correct_rate < 0.60`` rather than the literal current
    measurement (0.0) so a future parser-expansion ADR that lifts the
    rate doesn't break this test; the test fails (correctly) only
    when the gate would now pass — at which point ADR-0121 should be
    superseded by a successful promotion ADR.
    """

    def test_sealed_correct_rate_under_contract_floor(self) -> None:
        from evals.gsm8k_math.runner import run_lane

        plaintext = _decrypt_or_skip()
        cases = [
            json.loads(line)
            for line in plaintext.decode("utf-8").splitlines()
            if line.strip()
        ]
        report = run_lane(cases)
        rate = report.metrics["correct_rate"]
        assert rate < _ADR_0120_CORRECT_RATE_FLOOR, (
            f"sealed-holdout correct_rate = {rate}; ADR-0120 floor = "
            f"{_ADR_0120_CORRECT_RATE_FLOOR}. The contract would now ACCEPT "
            f"the promotion. Supersede ADR-0121 with a successful promotion "
            f"ADR (sign the claim, document the lift in correct_rate)."
        )


class TestNoSignedExpertClaimForMath:
    """ADR-0121 invariant 3."""

    def test_reviewers_yaml_has_no_expert_claims_entry_for_math(self) -> None:
        if not _REVIEWERS_PATH.exists():
            pytest.fail(f"reviewers.yaml missing at {_REVIEWERS_PATH}")
        data = yaml.safe_load(_REVIEWERS_PATH.read_text(encoding="utf-8"))
        # The expert_claims top-level key may not exist yet (ADR-0120a
        # has not landed the implementation); that's acceptable.
        expert_claims = data.get("expert_claims") or []
        domain_ids = {c.get("domain_id") for c in expert_claims if isinstance(c, dict)}
        assert "mathematics_logic" not in domain_ids, (
            f"reviewers.yaml carries an expert_claims entry for "
            f"mathematics_logic; ADR-0121 deferral requires no such entry "
            f"until the contract gate accepts."
        )


class TestObligationsStillDischarged:
    """ADR-0121 invariant 4.

    Roll-up assertion that the substrate is intact — the deferral is
    on the contract-level correct_rate gate, not on any ADR-0114a
    obligation regression. The Phase 5 test suite (74 cases) verifies
    each obligation individually; this test just confirms the suite
    is structurally present.
    """

    def test_phase_5_test_modules_exist(self) -> None:
        for name in (
            "test_gsm8k_math_runner.py",
            "test_adr_0119_4_frontier_baseline.py",
            "test_adr_0119_5_adversarial.py",
            "test_adr_0119_6_depth_curve.py",
            "test_adr_0119_7_sealed_gsm8k.py",
            "test_adr_0119_8_lane_gate.py",
        ):
            path = _REPO_ROOT / "tests" / name
            assert path.exists(), (
                f"Phase 5 substrate test {name} missing; substrate may "
                f"have regressed since ADR-0121 was written"
            )

    def test_three_audit_passed_domains_still_held(self) -> None:
        from core.capability.reporting import ledger_report

        promoted = {
            r["domain"]
            for r in ledger_report()["domains"]
            if r["predicates"]["audit_passed"]
        }
        # The three audit-passed domains established under ADR-0110,
        # ADR-0111, ADR-0124 must all still hold.
        assert {"mathematics_logic", "physics", "systems_software"} <= promoted, (
            f"audit-passed set is {sorted(promoted)}; expected all three "
            f"of mathematics_logic, physics, systems_software"
        )


class TestWrongZeroAgainstRealGSM8K:
    """ADR-0121 invariant 5 — the load-bearing positive claim.

    Even though the contract refuses the promotion, the runner
    produces ZERO wrong outcomes against the sealed real GSM8K test.
    CORE refuses what it cannot grammar-handle; it does not
    confabulate. ADR-0114a Obligation #4 holds against the external
    benchmark.
    """

    def test_wrong_count_zero_on_sealed_gsm8k(self) -> None:
        from evals.gsm8k_math.runner import run_lane

        plaintext = _decrypt_or_skip()
        cases = [
            json.loads(line)
            for line in plaintext.decode("utf-8").splitlines()
            if line.strip()
        ]
        report = run_lane(cases)
        assert report.metrics["wrong"] == 0, (
            f"runner produced {report.metrics['wrong']} wrong outcomes "
            f"on real GSM8K; CORE confabulated. ADR-0114a Obligation #4 "
            f"violated — this is a more serious regression than missing "
            f"the correct_rate floor."
        )
        assert report.metrics["wrong_count_is_zero"] is True
        # Accounting completeness (already enforced by gsm8k_capability_shape)
        assert (
            report.metrics["correct"] + report.metrics["refused"]
            == report.metrics["cases_total"]
        )
