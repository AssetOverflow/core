"""ADR-0177 CP-1 — cue-precision ledger + credit assignment.

Proves the ``(cue, op, unit_shape)`` pattern key, the per-pattern counted
:class:`PatternTally` (reusing the ADR-0175 conservative floor), and the
credit-assignment mechanism (gold-labelled candidate chains -> per-pattern
counts). Each property is exercised by a test that *fails* under the violation it
names (CLAUDE.md §Schema-Defined Proof Obligations):

- cold ledger ⇒ no trust            -> TestColdLedger
- counts-only, refusals excluded    -> TestCreditAssignment / TestRefusalsNotCounted
- reliability earned by volume      -> TestReliabilityEarnedByVolume
- determinism / replay              -> TestDeterminism
- immutability                      -> TestImmutability

This substrate is **inert** — nothing outside this test imports it (ADR-0177 CP-1,
"imported by nothing outside its own tests"); asserted in TestInertSubstrate.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.reliability_gate.floor import N_MIN, conservative_floor
from generate.cue_precision import (
    CROSS_UNIT,
    SAME_UNIT,
    UNIT_SHAPES,
    CuePattern,
    CuePrecisionLedger,
    PatternTally,
    pattern_for_step,
    patterns_in_chain,
)
from generate.derivation.model import GroundedDerivation, Quantity, Step


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(value: float, unit: str, token: str | None = None) -> Quantity:
    return Quantity(value=value, unit=unit, source_token=token or str(value))


def _chain(start: Quantity, *steps: Step) -> GroundedDerivation:
    return GroundedDerivation(start=start, steps=tuple(steps))


# ---------------------------------------------------------------------------
# CuePattern (the key)
# ---------------------------------------------------------------------------

class TestCuePattern:
    def test_valid_pattern(self) -> None:
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        assert (p.cue, p.op, p.unit_shape) == ("per", "multiply", CROSS_UNIT)

    def test_empty_cue_rejected(self) -> None:
        with pytest.raises(ValueError):
            CuePattern(cue="", op="multiply", unit_shape=SAME_UNIT)

    def test_invalid_op_rejected(self) -> None:
        with pytest.raises(ValueError):
            CuePattern(cue="per", op="exponentiate", unit_shape=SAME_UNIT)

    def test_invalid_unit_shape_rejected(self) -> None:
        with pytest.raises(ValueError):
            CuePattern(cue="per", op="multiply", unit_shape="mixed")

    def test_unit_shapes_closed_set(self) -> None:
        assert UNIT_SHAPES == frozenset({CROSS_UNIT, SAME_UNIT})


# ---------------------------------------------------------------------------
# Pattern extraction (unit_shape classification)
# ---------------------------------------------------------------------------

class TestPatternExtraction:
    def test_cross_unit_when_operand_differs_from_primary(self) -> None:
        # 6 boxes x 50 apples -> running unit stays "boxes", operand "apples".
        d = _chain(
            _q(6, "boxes"),
            Step(op="multiply", operand=_q(50, "apples"), cue="per"),
        )
        assert pattern_for_step(d, d.steps[0]) == CuePattern(
            cue="per", op="multiply", unit_shape=CROSS_UNIT
        )

    def test_same_unit_when_operand_matches_primary(self) -> None:
        # 6 apples + 4 apples -> same unit.
        d = _chain(
            _q(6, "apples"),
            Step(op="add", operand=_q(4, "apples"), cue="and"),
        )
        assert pattern_for_step(d, d.steps[0]) == CuePattern(
            cue="and", op="add", unit_shape=SAME_UNIT
        )

    def test_dimensionless_scalar_is_same_unit(self) -> None:
        # A comparative scalar (twice -> x2) carries unit "" and scales within the
        # current dimension; it is NOT a cross-unit aggregate.
        d = _chain(
            _q(5, "apples"),
            Step(op="multiply", operand=_q(2, "", "twice"), cue="twice", comparative=True),
        )
        assert pattern_for_step(d, d.steps[0]).unit_shape == SAME_UNIT

    def test_patterns_in_chain_preserves_step_order_and_occurrences(self) -> None:
        d = _chain(
            _q(2, "boxes"),
            Step(op="multiply", operand=_q(3, "apples"), cue="per"),
            Step(op="multiply", operand=_q(4, "apples"), cue="per"),
        )
        patterns = patterns_in_chain(d)
        # Both steps share the same pattern -> two occurrences (per-step credit).
        assert len(patterns) == 2
        assert patterns[0] == patterns[1] == CuePattern(
            cue="per", op="multiply", unit_shape=CROSS_UNIT
        )


# ---------------------------------------------------------------------------
# PatternTally (counts-only, conservative floor)
# ---------------------------------------------------------------------------

class TestPatternTally:
    def _pat(self) -> CuePattern:
        return CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)

    def test_negative_counts_rejected(self) -> None:
        with pytest.raises(ValueError):
            PatternTally(pattern=self._pat(), correct=-1)

    def test_committed_excludes_nothing_but_correct_and_wrong(self) -> None:
        t = PatternTally(pattern=self._pat(), correct=7, wrong=3)
        assert t.committed == 10

    def test_no_refused_axis(self) -> None:
        # A tally is purely correct/wrong: there is no refusal field to count.
        assert set(PatternTally.__dataclass_fields__) == {"pattern", "correct", "wrong"}

    def test_reliability_matches_conservative_floor(self) -> None:
        t = PatternTally(pattern=self._pat(), correct=10, wrong=0)
        assert t.reliability == conservative_floor(10, 10)

    def test_record_is_immutable(self) -> None:
        t0 = PatternTally(pattern=self._pat())
        t1 = t0.record(correct=1)
        assert t0.correct == 0 and t1.correct == 1


# ---------------------------------------------------------------------------
# Cold ledger ⇒ no trust (the wrong=0 safety property CP-2 relies on)
# ---------------------------------------------------------------------------

class TestColdLedger:
    def test_empty_ledger_reliability_is_zero(self) -> None:
        ledger = CuePrecisionLedger()
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        assert ledger.reliability(p) == 0.0
        assert ledger.tally_for(p).committed == 0

    def test_below_n_min_reliability_is_zero(self) -> None:
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        d = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(3, "apples"), cue="per"))
        ledger = CuePrecisionLedger()
        for _ in range(N_MIN - 1):  # all correct but still under N_MIN
            ledger = ledger.record_chain(d, matched_gold=True)
        assert ledger.tally_for(p).committed == N_MIN - 1
        assert ledger.reliability(p) == 0.0  # earned by volume, not a streak


# ---------------------------------------------------------------------------
# Credit assignment (gold-labelled candidate chains)
# ---------------------------------------------------------------------------

class TestCreditAssignment:
    def test_matched_chain_credits_correct_per_step(self) -> None:
        d = _chain(
            _q(2, "boxes"),
            Step(op="multiply", operand=_q(3, "apples"), cue="per"),
            Step(op="multiply", operand=_q(4, "apples"), cue="per"),
        )
        ledger = CuePrecisionLedger().record_chain(d, matched_gold=True)
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        assert ledger.tally_for(p).correct == 2
        assert ledger.tally_for(p).wrong == 0

    def test_unmatched_chain_credits_wrong_per_step(self) -> None:
        d = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(3, "apples"), cue="per"))
        ledger = CuePrecisionLedger().record_chain(d, matched_gold=False)
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        assert ledger.tally_for(p).correct == 0
        assert ledger.tally_for(p).wrong == 1

    def test_record_case_labels_candidates_by_gold(self) -> None:
        # gold = 12. A correct product chain (2 x 6) and a wrong sum chain (2 + 6 = 8).
        good = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(6, "apples"), cue="per"))
        bad = _chain(_q(2, "apples"), Step(op="add", operand=_q(6, "apples"), cue="and"))
        ledger = CuePrecisionLedger().record_case([good, bad], gold_answer=12.0)
        mult = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        add = CuePattern(cue="and", op="add", unit_shape=SAME_UNIT)
        assert ledger.tally_for(mult).correct == 1
        assert ledger.tally_for(mult).wrong == 0
        assert ledger.tally_for(add).correct == 0
        assert ledger.tally_for(add).wrong == 1

    def test_divide_by_zero_chain_is_skipped(self) -> None:
        # A non-computable chain is not a labelable reading -> contributes nothing.
        bad = _chain(_q(6, "apples"), Step(op="divide", operand=_q(0, "apples"), cue="per"))
        ledger = CuePrecisionLedger().record_case([bad], gold_answer=0.0)
        assert ledger.tallies == ()


# ---------------------------------------------------------------------------
# Refusals are never counted (independent of resolve/refuse)
# ---------------------------------------------------------------------------

class TestRefusalsNotCounted:
    def test_recording_independent_of_resolution(self) -> None:
        # Two disagreeing self-verifiable chains -> the search would REFUSE this
        # case, yet the ledger still records exactly the candidates' gold labels,
        # with no separate refusal penalty. committed == number of step occurrences.
        a = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(6, "apples"), cue="per"))
        b = _chain(_q(2, "apples"), Step(op="add", operand=_q(6, "apples"), cue="and"))
        ledger = CuePrecisionLedger().record_case([a, b], gold_answer=12.0)
        total_committed = sum(t.committed for t in ledger.tallies)
        assert total_committed == 2  # one step each; no phantom refusal count


# ---------------------------------------------------------------------------
# Reliability earned by volume
# ---------------------------------------------------------------------------

class TestReliabilityEarnedByVolume:
    def test_clean_record_below_then_at_n_min(self) -> None:
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        d = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(3, "apples"), cue="per"))
        ledger = CuePrecisionLedger()
        for _ in range(N_MIN):
            ledger = ledger.record_chain(d, matched_gold=True)
        assert ledger.tally_for(p).committed == N_MIN
        assert ledger.reliability(p) > 0.0
        assert ledger.reliability(p) == conservative_floor(N_MIN, N_MIN)


# ---------------------------------------------------------------------------
# Determinism / replay
# ---------------------------------------------------------------------------

class TestDeterminism:
    def _cases(self) -> list[tuple[list[GroundedDerivation], float]]:
        c1 = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(6, "apples"), cue="per"))
        c2 = _chain(_q(2, "apples"), Step(op="add", operand=_q(6, "apples"), cue="and"))
        c3 = _chain(_q(4, "apples"), Step(op="add", operand=_q(4, "apples"), cue="and"))
        return [([c1, c2], 12.0), ([c3], 8.0)]

    def test_same_cases_same_order_byte_stable(self) -> None:
        def run() -> CuePrecisionLedger:
            ledger = CuePrecisionLedger()
            for chains, gold in self._cases():
                ledger = ledger.record_case(chains, gold)
            return ledger

        assert run().tallies == run().tallies

    def test_tallies_sorted_canonically(self) -> None:
        ledger = CuePrecisionLedger()
        for chains, gold in self._cases():
            ledger = ledger.record_case(chains, gold)
        keys = [(t.pattern.cue, t.pattern.op, t.pattern.unit_shape) for t in ledger.tallies]
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_record_chain_returns_new_ledger(self) -> None:
        d = _chain(_q(2, "boxes"), Step(op="multiply", operand=_q(3, "apples"), cue="per"))
        ledger0 = CuePrecisionLedger()
        ledger1 = ledger0.record_chain(d, matched_gold=True)
        assert ledger0.tallies == ()
        assert ledger1.tallies != ()

    def test_duplicate_pattern_rejected(self) -> None:
        p = CuePattern(cue="per", op="multiply", unit_shape=CROSS_UNIT)
        with pytest.raises(ValueError):
            CuePrecisionLedger(
                tallies=(PatternTally(pattern=p), PatternTally(pattern=p))
            )


# ---------------------------------------------------------------------------
# Inert substrate — imported by nothing outside its own tests (ADR-0177 CP-1)
# ---------------------------------------------------------------------------

class TestInertSubstrate:
    def test_not_imported_outside_package_or_tests(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        # Mirror CLAUDE.md §Architectural Scan Exclusions.
        excluded = {
            ".git", ".venv", "__pycache__", ".pytest_cache", ".hypothesis",
            ".claude", "tests", "core-rs", "docs", "evals", "benchmarks",
            "scripts",
        }
        offenders: list[str] = []
        for dirpath, dirnames, filenames in os.walk(repo_root):
            dirnames[:] = [d for d in dirnames if d not in excluded]
            # Don't flag the package's own modules.
            if "cue_precision" in Path(dirpath).parts:
                continue
            for name in filenames:
                if not name.endswith(".py"):
                    continue
                src = Path(dirpath, name).read_text(encoding="utf-8")
                if "cue_precision" in src:
                    offenders.append(str(Path(dirpath, name).relative_to(repo_root)))
        assert offenders == [], f"cue_precision imported by serving/runtime: {offenders}"
