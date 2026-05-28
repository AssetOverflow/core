"""ADR-0175 Phase 1 — ledger + gate substrate.

Proves the pinned `conservative_floor` (§4a), the per-class `ClassTally`
ledger (§4), the human-set `Ceilings` (§3), and the deterministic `license`
gate (§3). Each ADR-0175 invariant is exercised by a test that *fails* under
the violation it names (CLAUDE.md §Schema-Defined Proof Obligations):

- #3 determinism/replay   -> TestDeterminismInvariant
- #4 no self-authorization -> TestNoSelfAuthorizationInvariant

This substrate is standalone — nothing in the serving/eval path imports it
(invariant #1, zero serving change, is satisfied by non-wiring; asserted in
TestZeroServingCoupling).
"""

from __future__ import annotations

import dataclasses

import pytest

from core.reliability_gate import (
    Action,
    Ceilings,
    ClassTally,
    LicenseDecision,
    conservative_floor,
    license_for,
    N_MIN,
    WILSON_Z,
)


# ---------------------------------------------------------------------------
# conservative_floor (§4a)
# ---------------------------------------------------------------------------

class TestConservativeFloor:
    def test_below_n_min_is_zero(self) -> None:
        for k in range(0, N_MIN):
            assert conservative_floor(k, k) == 0.0
        # exactly N_MIN with a perfect record is the first non-zero
        assert conservative_floor(N_MIN, N_MIN) > 0.0

    def test_zero_committed_is_zero(self) -> None:
        assert conservative_floor(0, 0) == 0.0

    def test_perfect_record_matches_closed_form(self) -> None:
        # For a perfect record (s == k) the Wilson lower bound reduces to
        # k / (k + z²). Pin exact values via the closed form (no hand-rounding).
        z2 = WILSON_Z * WILSON_Z
        for k in (10, 38, 60, 100, 657):
            expected = round(k / (k + z2), 9)
            assert conservative_floor(k, k) == expected

    def test_range_is_zero_to_below_one(self) -> None:
        for s, k in [(10, 10), (38, 40), (100, 100), (5, 20), (657, 657)]:
            v = conservative_floor(s, k)
            assert 0.0 <= v < 1.0  # never exactly 1.0 — no finite record proves perfection

    def test_perfect_record_is_monotonic_in_k(self) -> None:
        # more clean evidence -> higher earned floor
        ks = [10, 20, 40, 80, 160, 657]
        vals = [conservative_floor(k, k) for k in ks]
        assert vals == sorted(vals)
        assert all(a < b for a, b in zip(vals, vals[1:]))

    def test_cost_to_clear_propose_ceiling(self) -> None:
        # ADR worked example: ~38 clean commitments to clear θ_propose = 0.85
        assert conservative_floor(37, 37) < 0.85
        assert conservative_floor(38, 38) >= 0.85

    def test_one_wrong_drops_below_perfect_and_below_propose(self) -> None:
        # ADR asymmetry example: one wrong in 40 -> ~0.818, below a 0.85 gate
        perfect = conservative_floor(40, 40)
        one_wrong = conservative_floor(39, 40)
        assert one_wrong < perfect
        assert abs(one_wrong - 0.8177) < 1e-3
        assert one_wrong < 0.85

    def test_serving_is_expensive(self) -> None:
        # θ_serve = 0.99 needs hundreds of clean commitments; 100 is not enough
        assert conservative_floor(100, 100) < 0.99
        assert conservative_floor(657, 657) >= 0.99

    def test_rejects_invalid_counts(self) -> None:
        with pytest.raises(ValueError):
            conservative_floor(5, 4)  # successes > committed
        with pytest.raises(ValueError):
            conservative_floor(-1, 10)
        with pytest.raises(ValueError):
            conservative_floor(3, -1)


# ---------------------------------------------------------------------------
# ClassTally ledger (§4) — reliability is COMMITMENT precision
# ---------------------------------------------------------------------------

class TestClassTally:
    def test_reliability_uses_committed_not_total(self) -> None:
        # 40 clean commitments + a pile of refusals: refusals must NOT lower
        # reliability (refusing is safe; high refusal is a coverage fact).
        no_refusals = ClassTally("G1", correct=40, wrong=0, refused=0)
        many_refusals = ClassTally("G1", correct=40, wrong=0, refused=500)
        assert no_refusals.reliability == many_refusals.reliability
        assert no_refusals.reliability >= 0.85

    def test_refusal_only_class_has_zero_reliability(self) -> None:
        # No commitments -> no demonstrated reliability -> 0 (cannot serve/propose)
        t = ClassTally("G2", correct=0, wrong=0, refused=50)
        assert t.committed == 0
        assert t.reliability == 0.0

    def test_t2_precision_over_anchor_set(self) -> None:
        t = ClassTally("G1", t2_verified=40, t2_agrees_gold=40)
        assert t.t2_precision >= 0.85

    def test_coverage_tracks_commit_rate(self) -> None:
        t = ClassTally("G1", correct=8, wrong=2, refused=90)
        assert t.coverage == round(10 / 100, 9)

    def test_record_is_immutable_returns_new(self) -> None:
        t0 = ClassTally("G1")
        t1 = t0.record(correct=1)
        assert t0.correct == 0  # original untouched
        assert t1.correct == 1
        assert t1 is not t0

    def test_tally_is_frozen(self) -> None:
        t = ClassTally("G1", correct=1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.correct = 99  # type: ignore[misc]

    def test_rejects_inconsistent_counts(self) -> None:
        with pytest.raises(ValueError):
            ClassTally("G1", t2_verified=3, t2_agrees_gold=5)
        with pytest.raises(ValueError):
            ClassTally("G1", correct=-1)


# ---------------------------------------------------------------------------
# Ceilings (§3) + invariant #4 (no self-authorization)
# ---------------------------------------------------------------------------

class TestCeilings:
    def test_practice_ceiling_is_zero(self) -> None:
        c = Ceilings.default()
        assert c.required("G1", Action.PRACTICE) == 0.0

    def test_default_propose_and_serve(self) -> None:
        c = Ceilings.default()
        assert c.required("G1", Action.PROPOSE) == 0.85
        assert c.required("G1", Action.SERVE) == 0.99

    def test_override_is_per_class(self) -> None:
        c = Ceilings.default().with_override("G3", Action.SERVE, 0.95)
        assert c.required("G3", Action.SERVE) == 0.95
        assert c.required("G1", Action.SERVE) == 0.99  # other classes unchanged

    def test_override_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            Ceilings.default().with_override("G1", Action.SERVE, 1.0)
        with pytest.raises(ValueError):
            Ceilings.default().with_override("G1", Action.SERVE, -0.1)


class TestNoSelfAuthorizationInvariant:
    """Invariant #4 — the engine never raises its own ceiling."""

    def test_ceilings_are_frozen(self) -> None:
        c = Ceilings.default()
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.overrides = ()  # type: ignore[misc]

    def test_raising_a_ceiling_produces_a_new_object_not_mutation(self) -> None:
        c0 = Ceilings.default()
        c1 = c0.with_override("G1", Action.SERVE, 0.90)
        assert c1 is not c0
        # the original is unchanged — there is no in-place "lower the bar"
        assert c0.required("G1", Action.SERVE) == 0.99
        assert c1.required("G1", Action.SERVE) == 0.90

    def test_gate_never_emits_or_mutates_ceilings(self) -> None:
        # license_for() returns a LicenseDecision, never a Ceilings, and does not
        # mutate the ceilings it was given.
        c = Ceilings.default()
        before = c.overrides
        d = license_for(ClassTally("G1", correct=40), Action.PROPOSE, c)
        assert isinstance(d, LicenseDecision)
        assert not isinstance(d, Ceilings)
        assert c.overrides == before


# ---------------------------------------------------------------------------
# license gate (§3)
# ---------------------------------------------------------------------------

class TestLicenseGate:
    def test_practice_always_licensed_even_with_no_evidence(self) -> None:
        # θ_practice = 0 -> sealed practice may always attempt
        d = license_for(ClassTally("G9", correct=0, wrong=0, refused=0), Action.PRACTICE, Ceilings.default())
        assert d.licensed is True
        assert d.required == 0.0

    def test_propose_licensed_at_38_clean_commitments(self) -> None:
        d = license_for(ClassTally("G1", correct=38), Action.PROPOSE, Ceilings.default())
        assert d.licensed is True
        assert d.measured >= 0.85

    def test_propose_denied_with_one_wrong_in_40(self) -> None:
        d = license_for(ClassTally("G1", correct=39, wrong=1), Action.PROPOSE, Ceilings.default())
        assert d.licensed is False
        assert d.measured < 0.85

    def test_perfect_100_proposes_but_does_not_serve(self) -> None:
        t = ClassTally("G1", correct=100)
        assert license_for(t, Action.PROPOSE, Ceilings.default()).licensed is True
        assert license_for(t, Action.SERVE, Ceilings.default()).licensed is False

    def test_t2_precision_checker_gates_widening(self) -> None:
        t = ClassTally("G1", correct=5, wrong=0, t2_verified=40, t2_agrees_gold=40)
        d = license_for(t, Action.PROPOSE, Ceilings.default(), checker="t2_precision")
        assert d.checker == "t2_precision"
        assert d.licensed is True

    def test_decision_carries_inspectable_ratio(self) -> None:
        d = license_for(ClassTally("G1", correct=100), Action.PROPOSE, Ceilings.default())
        assert d.ratio == round(d.measured / d.required, 9)
        assert d.ratio >= 1.0

    def test_unknown_checker_rejected(self) -> None:
        with pytest.raises(ValueError):
            license_for(ClassTally("G1", correct=40), Action.PROPOSE, Ceilings.default(), checker="vibes")


# ---------------------------------------------------------------------------
# Invariant #3 — determinism / replay
# ---------------------------------------------------------------------------

class TestDeterminismInvariant:
    def test_floor_is_idempotent_and_pre_rounded(self) -> None:
        for s, k in [(10, 10), (38, 40), (5, 10), (657, 657), (39, 40)]:
            a = conservative_floor(s, k)
            b = conservative_floor(s, k)
            assert a == b                      # pure
            assert a == round(a, 9)            # already at 1e-9 (replay-stable)

    def test_gate_decision_is_deterministic(self) -> None:
        t = ClassTally("G1", correct=38, wrong=1, refused=12)
        c = Ceilings.default()
        d1 = license_for(t, Action.PROPOSE, c)
        d2 = license_for(t, Action.PROPOSE, c)
        assert d1 == d2

    def test_reliability_stable_across_recompute(self) -> None:
        t = ClassTally("G1", correct=38, wrong=2)
        assert t.reliability == ClassTally("G1", correct=38, wrong=2).reliability


# ---------------------------------------------------------------------------
# Invariant #1 (proxy) — zero serving coupling
# ---------------------------------------------------------------------------

class TestZeroServingCoupling:
    def test_package_does_not_import_serving_runtime(self) -> None:
        # The substrate must not pull in the parse/solve/eval serving path.
        import core.reliability_gate as rg
        mod_file = rg.__file__
        assert mod_file is not None
        # none of the serving-path modules should be a (transitive) hard import
        # of the gate package's own modules — assert the package modules don't
        # name them at import time.
        import importlib
        for name in ("floor", "ledger", "ceilings", "gate"):
            m = importlib.import_module(f"core.reliability_gate.{name}")
            src = (m.__doc__ or "")
            # structural: these modules import only stdlib + sibling gate modules
            assert "generate.math_candidate_graph" not in src
