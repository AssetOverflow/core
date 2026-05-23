"""ADR-0126 — tests for the candidate-emitting parser (P2).

Proves the candidate-emission topology end-to-end against the round-trip
filter from P1:

- Unambiguous sentences emit exactly one candidate, which the filter
  admits.
- Ambiguous sentences (e.g. verb in both SUBTRACT_VERBS and
  TRANSFER_VERBS) emit multiple candidates; the filter admits the
  correct one based on grounded slots.
- Out-of-grammar sentences emit zero candidates (no ParseError raised).
- Permissive verbs not in the legacy math_parser tables (e.g. "bought",
  "lost", "gave") now produce admissible candidates — the whole point
  of P2 + filter.
"""

from __future__ import annotations

from generate.math_candidate_parser import (
    extract_initial_candidates,
    extract_operation_candidates,
)
from generate.math_roundtrip import roundtrip_admissible


# ---------------------------------------------------------------------------
# Initial-possession extraction
# ---------------------------------------------------------------------------

class TestInitialExtraction:
    def test_single_entity_digit(self) -> None:
        cands = extract_initial_candidates("Sam has 5 apples.")
        assert len(cands) == 1
        c = cands[0]
        assert c.initial.entity == "Sam"
        assert c.initial.quantity.value == 5
        assert c.initial.quantity.unit == "apples"

    def test_single_entity_word_number(self) -> None:
        cands = extract_initial_candidates("Sam has three apples.")
        assert len(cands) == 1
        assert cands[0].initial.quantity.value == 3

    def test_collective_entity(self) -> None:
        cands = extract_initial_candidates("The boys have 10 marbles.")
        assert len(cands) == 1
        assert cands[0].initial.entity == "the boys"

    def test_singular_unit_pluralized(self) -> None:
        cands = extract_initial_candidates("Sam has 1 apple.")
        assert len(cands) == 1
        # math_parser canonicalization rule: always pluralize
        assert cands[0].initial.quantity.unit == "apples"

    def test_no_match_returns_empty(self) -> None:
        # Out-of-grammar shape — empty list, NOT an exception.
        assert extract_initial_candidates("Sam went to the store.") == []
        assert extract_initial_candidates("How many apples?") == []


# ---------------------------------------------------------------------------
# Operation extraction — unambiguous verbs
# ---------------------------------------------------------------------------

class TestUnambiguousOperations:
    def test_add_present_tense(self) -> None:
        cands = extract_operation_candidates("Sam buys 3 apples.")
        assert len(cands) == 1
        assert cands[0].op.kind == "add"
        assert cands[0].op.operand.value == 3
        assert roundtrip_admissible(cands[0])

    def test_add_past_tense_permissive(self) -> None:
        # "bought" is in the new permissive ADD_VERBS but NOT in the
        # legacy math_parser._ADD_VERBS. The whole point of P2 is to
        # admit these via the round-trip filter.
        cands = extract_operation_candidates("Sam bought 3 apples.")
        assert len(cands) == 1
        assert cands[0].op.kind == "add"
        assert cands[0].matched_verb == "bought"
        assert roundtrip_admissible(cands[0])

    def test_subtract_present_tense(self) -> None:
        cands = extract_operation_candidates("Sam eats 2 apples.")
        assert len(cands) == 1
        assert cands[0].op.kind == "subtract"
        assert roundtrip_admissible(cands[0])

    def test_subtract_past_tense_permissive(self) -> None:
        # "ate" is in the new permissive SUBTRACT_VERBS but not legacy.
        cands = extract_operation_candidates("Sam ate 2 apples.")
        assert len(cands) == 1
        assert cands[0].op.kind == "subtract"
        assert cands[0].matched_verb == "ate"
        assert roundtrip_admissible(cands[0])

    def test_production_verb_permissive(self) -> None:
        # "bakes" is a production verb — actor creates instances. Not
        # in legacy ADD_VERBS, accepted now via the permissive table.
        cands = extract_operation_candidates("Sam bakes 4 pies.")
        assert len(cands) == 1
        assert cands[0].op.kind == "add"
        assert cands[0].matched_verb == "bakes"
        assert roundtrip_admissible(cands[0])

    def test_no_match_returns_empty(self) -> None:
        # Out-of-grammar: a verb we don't recognize at all.
        assert extract_operation_candidates("Sam contemplates 3 apples.") == []
        # Sentence missing required slots (no value).
        assert extract_operation_candidates("Sam buys apples.") == []


# ---------------------------------------------------------------------------
# Operation extraction — ambiguous verbs (THE key test for P2)
# ---------------------------------------------------------------------------

class TestAmbiguousOperations:
    def test_gives_with_target_emits_subtract_and_transfer(self) -> None:
        # "gives" appears in both SUBTRACT_VERBS (intransitive-like
        # reading "Sam gives 3 apples") and TRANSFER_VERBS (transitive
        # "Sam gives 3 apples to Tom"). When a target IS present, both
        # candidates fire by design — the filter and decision rule
        # resolve the ambiguity downstream.
        cands = extract_operation_candidates("Sam gives 3 apples to Tom.")
        kinds = sorted(c.op.kind for c in cands)
        assert kinds == ["subtract", "transfer"]

    def test_filter_admits_both_for_gives_to_target(self) -> None:
        # Both candidates pass round-trip — neither claims a slot that
        # isn't in the source. The P3 decision rule will need a
        # tiebreaker (most-grounded-slots-wins is one option). This
        # test pins the current filter behavior; the tiebreaker is
        # P3's responsibility.
        cands = extract_operation_candidates("Sam gives 3 apples to Tom.")
        admitted = [c for c in cands if roundtrip_admissible(c)]
        assert len(admitted) == 2
        # Transfer candidate has a target slot (4 grounded entities),
        # subtract candidate does not (3 grounded entities). Slot count
        # is the structural signal P3 will use.

    def test_gives_without_target_only_subtract_admits(self) -> None:
        # "Sam gives 3 apples." — no target slot in source. The
        # transfer pattern requires a "to <Target>" clause and won't
        # match; subtract pattern matches and is admissible.
        cands = extract_operation_candidates("Sam gives 3 apples.")
        admitted = [c for c in cands if roundtrip_admissible(c)]
        assert len(admitted) == 1
        assert admitted[0].op.kind == "subtract"

    def test_returns_emits_both_subtract_and_transfer(self) -> None:
        # "returns" is also overloaded.
        cands = extract_operation_candidates("Sam returns 2 books to Tom.")
        kinds = sorted(c.op.kind for c in cands)
        assert kinds == ["subtract", "transfer"]
        admitted = [c for c in cands if roundtrip_admissible(c)]
        assert len(admitted) == 2


# ---------------------------------------------------------------------------
# Wrong-answer firewall demonstrated end-to-end
# ---------------------------------------------------------------------------

class TestFirewallEndToEnd:
    def test_filter_rejects_when_legacy_parser_would_have_misparsed(self) -> None:
        # Imagine the old parser had a bug where "loses" was registered
        # as ADD. Under candidate-graph, even if such a buggy candidate
        # were emitted, the round-trip filter would catch it because
        # "loses" is not in ADD_VERBS.
        #
        # We simulate by constructing the buggy candidate by hand and
        # showing the filter rejects it.
        from generate.math_problem_graph import Operation, Quantity
        from generate.math_roundtrip import CandidateOperation
        buggy = CandidateOperation(
            op=Operation(actor="Sam", kind="add",
                         operand=Quantity(value=2, unit="apples")),
            source_span="Sam loses 2 apples.",
            matched_verb="loses",  # the bug
            matched_value_token="2",
            matched_unit_token="apples",
            matched_actor_token="Sam",
        )
        assert not roundtrip_admissible(buggy)

    def test_correct_subtract_candidate_for_loses_is_admissible(self) -> None:
        # And the correct subtract reading IS emitted by the extractor.
        cands = extract_operation_candidates("Sam loses 2 apples.")
        admitted = [c for c in cands if roundtrip_admissible(c)]
        assert len(admitted) == 1
        assert admitted[0].op.kind == "subtract"
        assert admitted[0].matched_verb == "loses"
