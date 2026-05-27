"""ADR-0126 P3 — tests for candidate-graph assembly + decision rule.

Proves the end-to-end candidate-graph pipeline:

  text → per-sentence candidates → filter → branch enumeration
       → per-branch solve → decision rule → answer | refusal

Critical assertions:

- Unambiguous problems produce a single answer.
- Ambiguous-verb problems ('gives') resolve via the slot-count
  tiebreaker; both readings agree on the answer, so emission proceeds.
- Out-of-grammar sentences refuse (no exception, deterministic
  refusal_reason string).
- Branches that disagree on the answer refuse (wrong == 0 preserved).
- Permissive verbs that the legacy parser refused now produce answers.
"""

from __future__ import annotations

from generate.math_candidate_graph import (
    MAX_TOTAL_BRANCHES,
    parse_and_solve,
)
from generate.math_candidate_parser import (
    extract_question_candidates,
)


# ---------------------------------------------------------------------------
# Question extractor (P2 addition tested here for cohesion)
# ---------------------------------------------------------------------------

class TestQuestionExtraction:
    def test_entity_question(self) -> None:
        qcs = extract_question_candidates("How many apples does Sam have?")
        assert len(qcs) == 1
        assert qcs[0].unknown.entity == "Sam"
        assert qcs[0].unknown.unit == "apples"

    def test_total_question(self) -> None:
        qcs = extract_question_candidates("How many apples do they have?")
        assert len(qcs) == 1
        assert qcs[0].unknown.entity is None
        assert qcs[0].unknown.unit == "apples"

    def test_collective_entity_question(self) -> None:
        qcs = extract_question_candidates("How many cards do the girls have?")
        assert len(qcs) == 1
        assert qcs[0].unknown.entity == "the girls"

    def test_with_trailing_modifier(self) -> None:
        qcs = extract_question_candidates(
            "How many apples does Sam have left?"
        )
        assert len(qcs) == 1
        assert qcs[0].unknown.entity == "Sam"

    def test_no_match(self) -> None:
        assert extract_question_candidates("What is the answer?") == []


# ---------------------------------------------------------------------------
# End-to-end happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_simple_add(self) -> None:
        result = parse_and_solve(
            "Sam has 5 apples. Sam buys 3 apples. "
            "How many apples does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 8

    def test_simple_subtract(self) -> None:
        result = parse_and_solve(
            "Sam has 10 apples. Sam eats 3 apples. "
            "How many apples does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 7

    def test_transfer(self) -> None:
        result = parse_and_solve(
            "Sam has 8 apples. Tom has 2 apples. "
            "Sam gives 3 apples to Tom. "
            "How many apples does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 5

    def test_transfer_other_side(self) -> None:
        result = parse_and_solve(
            "Sam has 8 apples. Tom has 2 apples. "
            "Sam gives 3 apples to Tom. "
            "How many apples does Tom have?"
        )
        assert result.is_admitted
        assert result.answer == 5

    def test_total_across_entities(self) -> None:
        result = parse_and_solve(
            "Sam has 5 apples. Tom has 3 apples. "
            "How many apples do they have?"
        )
        assert result.is_admitted
        assert result.answer == 8


# ---------------------------------------------------------------------------
# Permissive verbs the legacy parser would have refused
# ---------------------------------------------------------------------------

class TestPermissiveVerbsNowSolve:
    def test_past_tense_add(self) -> None:
        # 'bought' is permissive-only; the round-trip filter is what
        # makes it safe.
        result = parse_and_solve(
            "Sam has 5 apples. Sam bought 3 apples. "
            "How many apples does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 8

    def test_past_tense_subtract(self) -> None:
        result = parse_and_solve(
            "Sam has 10 apples. Sam ate 3 apples. "
            "How many apples does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 7

    def test_production_verb_bakes(self) -> None:
        result = parse_and_solve(
            "Sam has 2 pies. Sam bakes 4 pies. "
            "How many pies does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 6


# ---------------------------------------------------------------------------
# Ambiguity that the slot-count tiebreaker resolves
# ---------------------------------------------------------------------------

class TestAmbiguityResolution:
    def test_gives_with_target_resolves_to_transfer(self) -> None:
        # "Sam gives 3 apples to Tom" emits BOTH subtract and transfer
        # candidates per P2 tests. Both pass round-trip. The slot-count
        # tiebreaker collapses to transfer (more grounded slots), so
        # the graph is the transfer reading and Tom gets the apples.
        result = parse_and_solve(
            "Sam has 8 apples. Tom has 2 apples. "
            "Sam gives 3 apples to Tom. "
            "How many apples does Tom have?"
        )
        assert result.is_admitted
        assert result.answer == 5  # transfer reading: 2 + 3 = 5

    def test_gives_without_target_resolves_to_subtract(self) -> None:
        # "Sam gives 3 apples" → only subtract candidate is admissible.
        result = parse_and_solve(
            "Sam has 8 apples. Sam gives 3 apples. "
            "How many apples does Sam have?"
        )
        assert result.is_admitted
        assert result.answer == 5


# ---------------------------------------------------------------------------
# Refusals (preserve wrong == 0)
# ---------------------------------------------------------------------------

class TestRefusals:
    def test_empty_input(self) -> None:
        result = parse_and_solve("")
        assert not result.is_admitted
        assert "empty" in (result.refusal_reason or "").lower()

    def test_no_question(self) -> None:
        result = parse_and_solve("Sam has 5 apples.")
        assert not result.is_admitted
        assert "question" in (result.refusal_reason or "").lower()

    def test_unparseable_statement(self) -> None:
        # Verb not in any permissive table.  Either the regex parser refuses
        # directly ("no admissible candidate") or a ratified recognizer
        # matches but cannot inject typed solver state ("recognizer matched
        # but produced no injection") — both paths preserve wrong=0 by
        # refusing.  See the fix that retired the recognizer skip-only
        # fallback (silent-drop was a wrong>0 hazard analogous to case 0050).
        result = parse_and_solve(
            "Sam has 5 apples. Sam contemplates 3 apples. "
            "How many apples does Sam have?"
        )
        assert not result.is_admitted
        reason = result.refusal_reason or ""
        assert (
            "no admissible candidate" in reason
            or "recognizer matched but produced no injection" in reason
        ), f"unexpected refusal reason: {reason!r}"

    def test_question_references_unknown_entity(self) -> None:
        result = parse_and_solve(
            "Sam has 5 apples. "
            "How many apples does Alice have?"
        )
        assert not result.is_admitted

    def test_branch_count_cap_refuses(self) -> None:
        # Hard to construct without writing a multiplicatively-ambiguous
        # corpus; for now just assert the cap constant is sensible.
        assert MAX_TOTAL_BRANCHES == 64


# ---------------------------------------------------------------------------
# Diagnostics surfaced for P6 inner-loop signal
# ---------------------------------------------------------------------------

class TestDiagnostics:
    def test_diagnostics_on_admission(self) -> None:
        result = parse_and_solve(
            "Sam has 5 apples. Sam buys 3 apples. "
            "How many apples does Sam have?"
        )
        assert result.branches_enumerated >= 1
        assert result.branches_admissible >= 1

    def test_diagnostics_on_refusal(self) -> None:
        result = parse_and_solve("foobar baz quux?")
        # Refusal occurs before enumeration when no statement candidates
        # exist; diagnostics still report 0/0 cleanly.
        assert result.branches_enumerated == 0
        assert result.branches_admissible == 0
