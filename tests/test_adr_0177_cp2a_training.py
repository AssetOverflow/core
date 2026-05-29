"""ADR-0177 CP-2a — ledger training + the cue-precision measurement.

Covers the decoupled trainer (synthetic enumerators, so the obligations are proven
without relying on search internals) and an integration check that the real
measurement builds a non-empty, well-formed ledger over the sealed cases.
"""

from __future__ import annotations

from generate.cue_precision.ledger import CuePattern, CuePrecisionLedger
from generate.cue_precision.trainer import candidates_for, train_from_cases
from generate.derivation.model import GroundedDerivation, Quantity, Step


def _chain(start_val: float, start_unit: str, op: str, operand_val: float, operand_unit: str, cue: str) -> GroundedDerivation:
    return GroundedDerivation(
        start=Quantity(start_val, start_unit, str(start_val)),
        steps=(Step(op=op, operand=Quantity(operand_val, operand_unit, str(operand_val)), cue=cue),),
    )


class TestTrainFromCases:
    def test_matching_chain_credits_correct(self) -> None:
        # 6 boxes * 4 (apples) = 24 == gold -> pattern (each, multiply, cross_unit) +correct.
        chain = _chain(6.0, "boxes", "multiply", 4.0, "apples", "each")
        ledger = train_from_cases([("6 boxes 4 apples each", 24.0)], [lambda _t: [chain]])
        tally = ledger.tally_for(CuePattern(cue="each", op="multiply", unit_shape="cross_unit"))
        assert (tally.correct, tally.wrong) == (1, 0)

    def test_mismatching_chain_credits_wrong(self) -> None:
        # same chain, gold != 24 -> the pattern is credited wrong (the elimination signal).
        chain = _chain(6.0, "boxes", "multiply", 4.0, "apples", "each")
        ledger = train_from_cases([("6 boxes 4 apples each", 999.0)], [lambda _t: [chain]])
        tally = ledger.tally_for(CuePattern(cue="each", op="multiply", unit_shape="cross_unit"))
        assert (tally.correct, tally.wrong) == (0, 1)

    def test_same_chain_from_two_enumerators_counted_once(self) -> None:
        chain = _chain(2.0, "x", "add", 3.0, "x", "and")
        ledger = train_from_cases(
            [("2 x and 3 x", 5.0)],
            [lambda _t: [chain], lambda _t: [chain]],  # two enumerators, same reading
        )
        tally = ledger.tally_for(CuePattern(cue="and", op="add", unit_shape="same_unit"))
        assert tally.committed == 1  # deduped, not 2

    def test_deterministic(self) -> None:
        chain = _chain(6.0, "boxes", "multiply", 4.0, "apples", "each")
        cases = [("a", 24.0), ("b", 1.0)]
        enums = [lambda _t: [chain]]
        assert train_from_cases(cases, enums) == train_from_cases(cases, enums)

    def test_no_candidates_yields_empty_ledger(self) -> None:
        ledger = train_from_cases([("nothing here", 0.0)], [lambda _t: []])
        assert ledger == CuePrecisionLedger()

    def test_candidates_for_dedupes_preserving_order(self) -> None:
        a = _chain(1.0, "u", "add", 2.0, "u", "and")
        b = _chain(1.0, "u", "multiply", 2.0, "u", "each")
        got = candidates_for("t", [lambda _t: [a, b], lambda _t: [a]])
        assert got == (a, b)


class TestRealMeasurement:
    def test_ledger_builds_nonempty_and_well_formed(self) -> None:
        from evals.gsm8k_math.practice.v1.cue_precision_report import (
            build_cue_precision_ledger,
            format_reliability_table,
        )

        ledger = build_cue_precision_ledger()
        assert len(ledger.tallies) >= 1  # the search produces *some* labelled patterns
        for tally in ledger.tallies:
            assert 0.0 <= tally.reliability < 1.0  # conservative floor is in [0, 1)
            assert tally.committed == tally.correct + tally.wrong
        # deterministic render
        assert format_reliability_table(ledger) == format_reliability_table(
            build_cue_precision_ledger()
        )


class TestSearchChainParity:
    """The candidate_chains refactor must not change search_chain behaviour."""

    def test_decimal_product_still_resolves(self) -> None:
        from generate.derivation.multistep import search_chain

        text = (
            "There are 48 boxes with 24 erasers in each box. "
            "They sell the erasers for $0.75 each. How much money will they make?"
        )
        res = search_chain(text)
        assert res is not None and res.answer == 864.0

    def test_candidate_chains_is_enumeration_only(self) -> None:
        from generate.derivation.multistep import candidate_chains, search_chain

        # too-few quantities -> no candidates -> search refuses
        assert candidate_chains("She has 6 apples.") == []
        assert search_chain("She has 6 apples.") is None
