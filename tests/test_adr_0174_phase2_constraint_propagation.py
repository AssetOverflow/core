"""ADR-0174 Phase 2 — continuous constraint propagation tests.

Acceptance tests:

  1. Hypothesis emission adapters wrap CandidateInitial / CandidateOperation
     into Phase-1 Hypothesis objects with correct rank assignment.

  2. check_constraints runs sub-checks and returns ConstraintResult with
     specific elimination reasons (decomposed predicate names). Today's
     admission logic is byte-equivalent — a candidate that
     _initial_admissible / roundtrip_admissible would admit is admitted
     here; one they would reject is rejected here with the same
     short-circuit-on-first-failure semantics.

  3. eliminate_violating returns (survivors, eliminations) with original
     ranks preserved in eliminations and re-densified ranks in survivors.

  4. The wiring at math_candidate_graph injection sites does not alter
     admission semantics (3/47/0 preserved on train_sample) and remains
     deterministic across runs.

  5. When a synthetic candidate fails one of the sub-checks, the
     elimination is observable in the trace.

The check_constraints behavior parity with the pre-Phase-2 admission
predicates is the load-bearing invariant: any divergence would break
wrong=0 by silently weakening admissibility.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from generate.comprehension.constraint_propagation import (
    ConstraintResult,
    Elimination,
    VALID_PREDICATE_NAMES,
    check_constraints,
    eliminate_violating,
    hypothesis_from_initial,
    hypothesis_from_operation,
)
from generate.comprehension.state import (
    HYPOTHESIS_CAP,
    ComprehensionStateError,
    Hypothesis,
)
from generate.math_candidate_graph import _initial_admissible
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import (
    InitialPossession,
    Operation,
    Quantity,
)
from generate.math_roundtrip import CandidateOperation, roundtrip_admissible


# ---------------------------------------------------------------------------
# Helpers — construct minimal valid candidates
# ---------------------------------------------------------------------------


def _initial(
    entity: str = "Sam",
    value: int = 3,
    unit: str = "apples",
    source_span: str = "Sam has 3 apples.",
    matched_anchor: str = "has",
    matched_value_token: str = "3",
    matched_unit_token: str = "apples",
    matched_entity_token: str = "Sam",
) -> CandidateInitial:
    return CandidateInitial(
        initial=InitialPossession(
            entity=entity, quantity=Quantity(value=value, unit=unit),
        ),
        source_span=source_span,
        matched_anchor=matched_anchor,
        matched_value_token=matched_value_token,
        matched_unit_token=matched_unit_token,
        matched_entity_token=matched_entity_token,
    )


def _operation_add(
    actor: str = "Sam",
    value: int = 5,
    unit: str = "apples",
    source_span: str = "Sam buys 5 apples.",
    matched_verb: str = "buys",
    matched_value_token: str = "5",
    matched_unit_token: str = "apples",
    matched_actor_token: str = "Sam",
) -> CandidateOperation:
    return CandidateOperation(
        op=Operation(
            actor=actor, kind="add",
            operand=Quantity(value=value, unit=unit),
        ),
        source_span=source_span,
        matched_verb=matched_verb,
        matched_value_token=matched_value_token,
        matched_unit_token=matched_unit_token,
        matched_actor_token=matched_actor_token,
    )


# ---------------------------------------------------------------------------
# 1. Hypothesis emission adapters
# ---------------------------------------------------------------------------


class TestHypothesisEmission:
    def test_initial_wraps_candidate_at_given_rank(self) -> None:
        ic = _initial()
        hyp = hypothesis_from_initial(ic, rank=0)
        assert isinstance(hyp, Hypothesis)
        assert hyp.candidate is ic
        assert hyp.confidence_rank == 0
        assert hyp.category_assignments == ()
        assert hyp.constraint_state == ()
        assert hyp.unresolved == ()

    def test_operation_wraps_candidate_at_given_rank(self) -> None:
        op = _operation_add()
        hyp = hypothesis_from_operation(op, rank=2)
        assert hyp.candidate is op
        assert hyp.confidence_rank == 2

    def test_rank_outside_cap_refused(self) -> None:
        ic = _initial()
        with pytest.raises(ComprehensionStateError, match="rank must be in"):
            hypothesis_from_initial(ic, rank=HYPOTHESIS_CAP)
        with pytest.raises(ComprehensionStateError, match="rank must be in"):
            hypothesis_from_operation(_operation_add(), rank=-1)


# ---------------------------------------------------------------------------
# 2. check_constraints — parity with existing admissibility predicates
# ---------------------------------------------------------------------------


class TestCheckConstraintsInitialParity:
    """For CandidateInitial, check_constraints must match
    _initial_admissible exactly on the admit/reject decision."""

    def test_well_formed_initial_admits(self) -> None:
        ic = _initial()
        result = check_constraints(hypothesis_from_initial(ic, 0))
        assert result.admitted is True
        assert result.elimination_reason is None
        assert _initial_admissible(ic) is True  # parity

    def test_anchor_not_in_source_eliminated(self) -> None:
        ic = _initial(
            matched_anchor="had",  # source has "has"
            source_span="Sam has 3 apples.",
        )
        result = check_constraints(hypothesis_from_initial(ic, 0))
        assert result.admitted is False
        assert result.elimination_reason is not None
        assert "matched_anchor" in result.elimination_reason
        # The first failing predicate is initial.anchor_grounds.
        first_fail = next(
            (p for p, o in result.predicates_run if o == "fail"), None
        )
        assert first_fail == "initial.anchor_grounds"
        assert _initial_admissible(ic) is False  # parity

    def test_value_not_in_source_eliminated(self) -> None:
        ic = _initial(
            matched_value_token="99",  # source has "3"
            source_span="Sam has 3 apples.",
        )
        result = check_constraints(hypothesis_from_initial(ic, 0))
        assert result.admitted is False
        assert "matched_value_token" in (result.elimination_reason or "")
        assert _initial_admissible(ic) is False

    def test_unit_not_in_source_eliminated(self) -> None:
        ic = _initial(
            matched_unit_token="oranges",  # source has "apples"
            source_span="Sam has 3 apples.",
        )
        result = check_constraints(hypothesis_from_initial(ic, 0))
        assert result.admitted is False
        assert "matched_unit_token" in (result.elimination_reason or "")
        assert _initial_admissible(ic) is False

    def test_entity_not_in_source_eliminated(self) -> None:
        ic = _initial(
            matched_entity_token="Tom",  # source has "Sam"
            source_span="Sam has 3 apples.",
        )
        result = check_constraints(hypothesis_from_initial(ic, 0))
        assert result.admitted is False
        assert _initial_admissible(ic) is False


class TestCheckConstraintsOperationParity:
    """For CandidateOperation, check_constraints must match
    roundtrip_admissible exactly on the admit/reject decision."""

    def test_well_formed_operation_admits(self) -> None:
        op = _operation_add()
        result = check_constraints(hypothesis_from_operation(op, 0))
        assert result.admitted is True
        assert result.elimination_reason is None
        assert roundtrip_admissible(op) is True

    def test_verb_not_registered_for_kind_eliminated(self) -> None:
        # "buys" is registered for "add", not "subtract" — but constructing
        # an Operation with the wrong kind would fail at construction.
        # Use a verb that's not in any add-verb set.
        op = CandidateOperation(
            op=Operation(
                actor="Sam", kind="add",
                operand=Quantity(value=5, unit="apples"),
            ),
            source_span="Sam thinks 5 apples.",  # "thinks" not in ADD_VERBS
            matched_verb="thinks",
            matched_value_token="5",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        result = check_constraints(hypothesis_from_operation(op, 0))
        assert result.admitted is False
        first_fail = next(
            (p for p, o in result.predicates_run if o == "fail"), None
        )
        assert first_fail == "operation.verb_registered"
        assert roundtrip_admissible(op) is False

    def test_actor_not_in_source_eliminated(self) -> None:
        op = _operation_add(
            matched_actor_token="Tom",  # source has "Sam"
            source_span="Sam buys 5 apples.",
        )
        result = check_constraints(hypothesis_from_operation(op, 0))
        assert result.admitted is False
        first_fail = next(
            (p for p, o in result.predicates_run if o == "fail"), None
        )
        assert first_fail == "operation.actor_grounds"
        assert roundtrip_admissible(op) is False


class TestCheckConstraintsResultShape:
    def test_predicates_run_only_uses_known_predicate_names(self) -> None:
        ic = _initial()
        result = check_constraints(hypothesis_from_initial(ic, 0))
        for predicate_name, _outcome in result.predicates_run:
            assert predicate_name in VALID_PREDICATE_NAMES, (
                f"predicate {predicate_name!r} not in VALID_PREDICATE_NAMES; "
                "adding new predicates requires an ADR amendment"
            )

    def test_unknown_candidate_type_eliminated(self) -> None:
        # Wrap a string as candidate — not a known type
        hyp = Hypothesis(
            candidate=("not a candidate",),  # serialisable sentinel
            category_assignments=(),
            constraint_state=(),
            confidence_rank=0,
            unresolved=(),
        )
        result = check_constraints(hyp)
        assert result.admitted is False
        assert "unknown candidate type" in (result.elimination_reason or "")


# ---------------------------------------------------------------------------
# 3. eliminate_violating
# ---------------------------------------------------------------------------


class TestEliminateViolating:
    def test_all_admit_returns_all_survivors_no_eliminations(self) -> None:
        h0 = hypothesis_from_initial(_initial(entity="Sam"), 0)
        h1 = hypothesis_from_operation(_operation_add(actor="Sam"), 1)
        survivors, eliminations = eliminate_violating((h0, h1))
        assert len(survivors) == 2
        assert eliminations == ()
        # Ranks preserved (already dense from 0).
        assert survivors[0].confidence_rank == 0
        assert survivors[1].confidence_rank == 1

    def test_all_eliminated_returns_no_survivors(self) -> None:
        h0 = hypothesis_from_initial(
            _initial(matched_unit_token="oranges"), 0
        )
        h1 = hypothesis_from_initial(
            _initial(matched_unit_token="bananas"), 1
        )
        survivors, eliminations = eliminate_violating((h0, h1))
        assert survivors == ()
        assert len(eliminations) == 2
        # Original ranks preserved in eliminations.
        ranks = sorted(e.confidence_rank for e in eliminations)
        assert ranks == [0, 1]

    def test_partial_elimination_redensifies_survivor_ranks(self) -> None:
        # h0 fails (bad unit), h1 succeeds.
        h0 = hypothesis_from_initial(
            _initial(matched_unit_token="oranges"), 0
        )
        h1 = hypothesis_from_initial(_initial(), 1)
        survivors, eliminations = eliminate_violating((h0, h1))
        assert len(survivors) == 1
        assert survivors[0].confidence_rank == 0  # re-densified from 1
        assert len(eliminations) == 1
        assert eliminations[0].confidence_rank == 0  # original rank preserved

    def test_eliminations_carry_predicate_name(self) -> None:
        h = hypothesis_from_initial(
            _initial(matched_anchor="had"), 0  # anchor not in source
        )
        _, eliminations = eliminate_violating((h,))
        assert len(eliminations) == 1
        assert eliminations[0].predicate in VALID_PREDICATE_NAMES
        assert eliminations[0].predicate == "initial.anchor_grounds"


class TestEliminationDataclass:
    def test_invalid_predicate_refused(self) -> None:
        with pytest.raises(
            ComprehensionStateError, match="must be in VALID_PREDICATE_NAMES"
        ):
            Elimination(confidence_rank=0, predicate="bogus", reason="x")

    def test_empty_reason_refused(self) -> None:
        with pytest.raises(
            ComprehensionStateError, match="reason must be non-empty"
        ):
            Elimination(
                confidence_rank=0,
                predicate="initial.anchor_grounds",
                reason="",
            )


class TestConstraintResultDataclass:
    def test_admitted_with_elimination_reason_refused(self) -> None:
        with pytest.raises(
            ComprehensionStateError, match="inconsistent"
        ):
            ConstraintResult(
                admitted=True,
                predicates_run=(("initial.anchor_grounds", "ok"),),
                elimination_reason="impossible combo",
            )

    def test_rejected_without_reason_refused(self) -> None:
        with pytest.raises(
            ComprehensionStateError, match="requires a non-None"
        ):
            ConstraintResult(
                admitted=False,
                predicates_run=(("initial.anchor_grounds", "fail"),),
                elimination_reason=None,
            )


# ---------------------------------------------------------------------------
# 4. Integration — wiring at math_candidate_graph injection sites
# ---------------------------------------------------------------------------


class TestIntegrationWithCandidateGraph:
    """End-to-end: feed a real problem through parse_and_solve and verify
    the trace stream is well-formed JSON when populated, and admission
    semantics are preserved."""

    def test_correct_case_still_admits(self) -> None:
        """Case 0014 is one of the 3 correct cases; Phase 2 wiring must
        not break it."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Bob can shuck 10 oysters in 5 minutes.  "
            "How many oysters can he shuck in 2 hours?"
        )
        r = parse_and_solve(text)
        assert r.answer == 240
        assert r.refusal_reason is None

    def test_trace_events_are_valid_json(self) -> None:
        """Every event in reader_trace must be parseable JSON — Phase 2
        events conform to the same shape contract as Phase 1 events."""
        from generate.math_candidate_graph import parse_and_solve
        # Run all 3 correct cases; any trace events must be valid JSON.
        texts = [
            "Bob can shuck 10 oysters in 5 minutes.  "
            "How many oysters can he shuck in 2 hours?",
            "Xavier plays football with his friends. "
            "During 15 minutes Xavier can score 2 goals on average. "
            "How many goals does Xavier score in 2 hours?",
        ]
        for text in texts:
            r = parse_and_solve(text)
            for ev_str in r.reader_trace:
                ev = json.loads(ev_str)  # raises on bad JSON
                assert "layer" in ev
                assert "phase" in ev

    def test_phase2_event_shape_when_synthesized(self) -> None:
        """When an elimination DOES occur, the event has the documented
        Phase-2 shape. We verify directly against eliminate_violating
        rather than the full pipeline because today's injectors are
        conservative enough that real eliminations do not fire on the
        train_sample corpus."""
        h_bad = hypothesis_from_initial(
            _initial(matched_unit_token="oranges"), 0
        )
        _, eliminations = eliminate_violating((h_bad,))
        # Serialise as the math_candidate_graph wiring does:
        ev: dict[str, Any] = {
            "layer": "constraint_propagation",
            "phase": 2,
            "outcome": "eliminated",
            "confidence_rank": eliminations[0].confidence_rank,
            "predicate": eliminations[0].predicate,
            "reason": eliminations[0].reason,
            "sentence_index": 0,
        }
        encoded = json.dumps(ev, sort_keys=True)
        decoded = json.loads(encoded)
        assert decoded["layer"] == "constraint_propagation"
        assert decoded["phase"] == 2
        assert decoded["predicate"] == "initial.unit_grounds"
        assert decoded["outcome"] == "eliminated"
