"""ADR-0174 Phase 3a — lookback re-evaluation operator + pronoun resolution.

Acceptance tests:

  1. ``reevaluate`` operator semantics: no-op when refinement doesn't
     apply, refined hypothesis when constraints pass, None when
     constraints fail post-refinement.

  2. ``PronounResolution`` dataclass invariants — validates pronoun /
     resolved_to / evidence_source / kind shape.

  3. End-to-end wiring: a synthetic problem with pronoun-subject
     statement that the regex parser refuses fires the lookback path
     and emits an "admitted" trace event when the discourse antecedent
     resolves.

  4. Refusal-preferring discipline: a held statement with no discourse
     antecedent emits a "no_antecedent" trace event and drops cleanly.

  5. wrong=0 preserved on train_sample/v1 (score now 4/46/0 after ADR-0207 §5 step 2).

Phase 3a substrate scope: this PR builds the reevaluate operator and
wires pronoun resolution into the recognizer-injection branch of
math_candidate_graph.parse_and_solve.  The wiring is correct but does
not fire on any of the 50 train_sample cases because the cases the
ADR identified (21 empty-anchor discrete_count failures) refuse for
verb-set narrowness reasons (recognizer scope, ADR-0163.x) BEFORE
reaching the pronoun layer.  This file therefore exercises the wiring
via synthetic problems that target the path directly.

See docs/handoff/PHASE-3.1-FOLLOWUP-RECOGNIZER-EXPANSION.md for the
follow-up brief documenting which recognizer expansions would surface
real cases that exercise this path on the train_sample corpus.
"""

from __future__ import annotations

import json

import pytest

from generate.comprehension.constraint_propagation import (
    hypothesis_from_initial,
    hypothesis_from_operation,
)
from generate.comprehension.lookback import (
    PronounResolution,
    ReevaluateResult,
    VALID_REFINEMENT_KINDS,
    VALID_UNRESOLVED_SLOTS,
    reevaluate,
)
from generate.comprehension.state import (
    ComprehensionStateError,
    Hypothesis,
)
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import (
    InitialPossession,
    Operation,
    Quantity,
)
from generate.math_roundtrip import CandidateOperation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _operation_with_pronoun_actor(
    pronoun: str = "He",
    source_span: str = "He buys 3 apples.",
) -> CandidateOperation:
    return CandidateOperation(
        op=Operation(
            actor=pronoun, kind="add",
            operand=Quantity(value=3, unit="apples"),
        ),
        source_span=source_span,
        matched_verb="buys",
        matched_value_token="3",
        matched_unit_token="apples",
        matched_actor_token=pronoun,
    )


def _initial_with_pronoun_actor(
    pronoun: str = "She",
    source_span: str = "She has 5 books.",
) -> CandidateInitial:
    return CandidateInitial(
        initial=InitialPossession(
            entity=pronoun,
            quantity=Quantity(value=5, unit="books"),
        ),
        source_span=source_span,
        matched_anchor="has",
        matched_value_token="5",
        matched_unit_token="books",
        matched_entity_token=pronoun,
    )


def _held_hypothesis(candidate: object, rank: int = 0) -> Hypothesis:
    """Construct a Hypothesis with unresolved=('actor_pronoun',) as the
    Phase 3 wiring would produce."""
    if isinstance(candidate, CandidateOperation):
        base = hypothesis_from_operation(candidate, rank)
    elif isinstance(candidate, CandidateInitial):
        base = hypothesis_from_initial(candidate, rank)
    else:
        raise ValueError(f"unknown candidate type {type(candidate).__name__}")
    return Hypothesis(
        candidate=base.candidate,
        category_assignments=base.category_assignments,
        constraint_state=base.constraint_state,
        confidence_rank=base.confidence_rank,
        unresolved=("actor_pronoun",),
    )


# ---------------------------------------------------------------------------
# 1. reevaluate operator semantics
# ---------------------------------------------------------------------------


class TestReevaluateOnOperation:
    def test_pronoun_resolution_succeeds_when_constraints_pass(self) -> None:
        cand = _operation_with_pronoun_actor(pronoun="He")
        hyp = _held_hypothesis(cand, rank=0)
        ref = PronounResolution(
            pronoun="He", resolved_to="Bob",
            evidence_source="discourse_prior_subjects",
        )
        result = reevaluate(hyp, ref)
        assert result.refined is not None
        assert result.elimination_reason is None
        # The Operation.actor is rewritten to the resolved name.
        assert result.refined.candidate.op.actor == "Bob"  # type: ignore[attr-defined]
        # matched_actor_token STAYS as the pronoun so grounding still
        # passes against the held statement's source span.
        assert result.refined.candidate.matched_actor_token == "He"  # type: ignore[attr-defined]
        # The 'actor_pronoun' slot is no longer unresolved.
        assert "actor_pronoun" not in result.refined.unresolved
        # category_assignments records the refinement event for trace.
        assert any(
            tup[1] == "pronoun_resolved"
            for tup in result.refined.category_assignments
        )

    def test_noop_when_hypothesis_has_no_unresolved_pronoun(self) -> None:
        cand = _operation_with_pronoun_actor()
        hyp = hypothesis_from_operation(cand, 0)  # unresolved=() by default
        ref = PronounResolution(
            pronoun="He", resolved_to="Bob",
            evidence_source="discourse_prior_subjects",
        )
        result = reevaluate(hyp, ref)
        # No-op: refined == original hypothesis, no elimination.
        assert result.refined is hyp
        assert result.elimination_reason is None
        assert result.constraint_result is None

    def test_eliminated_when_refined_candidate_fails_constraints(self) -> None:
        # Construct a candidate whose source_span doesn't contain the
        # pronoun — the rebuilt candidate will fail matched_actor_token
        # grounding because the pronoun isn't in haystack.  This is a
        # degenerate case but proves the constraint re-check actually
        # fires.
        cand = CandidateOperation(
            op=Operation(
                actor="He", kind="add",
                operand=Quantity(value=3, unit="apples"),
            ),
            source_span="Sam buys 3 apples.",  # 'He' not in source
            matched_verb="buys",
            matched_value_token="3",
            matched_unit_token="apples",
            matched_actor_token="He",  # would fail _token_in even before refinement
        )
        hyp = _held_hypothesis(cand, 0)
        ref = PronounResolution(
            pronoun="He", resolved_to="Bob",
            evidence_source="discourse_prior_subjects",
        )
        result = reevaluate(hyp, ref)
        assert result.refined is None
        assert result.elimination_reason is not None
        # The first failing predicate is operation.actor_grounds —
        # observable via constraint_result.predicates_run.
        assert result.constraint_result is not None
        first_fail = next(
            (p for p, o in result.constraint_result.predicates_run if o == "fail"),
            None,
        )
        assert first_fail == "operation.actor_grounds"


class TestReevaluateOnInitial:
    def test_pronoun_resolution_rewrites_initial_entity(self) -> None:
        cand = _initial_with_pronoun_actor(pronoun="She")
        hyp = _held_hypothesis(cand, rank=0)
        ref = PronounResolution(
            pronoun="She", resolved_to="Jan",
            evidence_source="discourse_prior_subjects",
        )
        result = reevaluate(hyp, ref)
        assert result.refined is not None
        assert result.refined.candidate.initial.entity == "Jan"  # type: ignore[attr-defined]
        assert result.refined.candidate.matched_entity_token == "She"  # type: ignore[attr-defined]


class TestReevaluateResultDataclass:
    def test_invalid_refinement_kind_refused(self) -> None:
        cand = _operation_with_pronoun_actor()
        hyp = _held_hypothesis(cand, 0)
        with pytest.raises(
            ComprehensionStateError, match="refinement_kind must be in"
        ):
            ReevaluateResult(
                refined=hyp, previous=hyp,
                refinement_kind="not_a_kind",
                constraint_result=None,
                elimination_reason=None,
            )

    def test_inconsistent_refined_and_elimination_refused(self) -> None:
        cand = _operation_with_pronoun_actor()
        hyp = _held_hypothesis(cand, 0)
        with pytest.raises(
            ComprehensionStateError, match="inconsistent"
        ):
            ReevaluateResult(
                refined=hyp, previous=hyp,
                refinement_kind="pronoun_resolution",
                constraint_result=None,
                elimination_reason="impossible combo",
            )

    def test_none_refined_requires_elimination_reason(self) -> None:
        cand = _operation_with_pronoun_actor()
        hyp = _held_hypothesis(cand, 0)
        with pytest.raises(
            ComprehensionStateError, match="requires a non-None"
        ):
            ReevaluateResult(
                refined=None, previous=hyp,
                refinement_kind="pronoun_resolution",
                constraint_result=None,
                elimination_reason=None,
            )


# ---------------------------------------------------------------------------
# 2. PronounResolution dataclass invariants
# ---------------------------------------------------------------------------


class TestPronounResolutionConstruction:
    def test_minimal_valid(self) -> None:
        r = PronounResolution(
            pronoun="He", resolved_to="Bob",
            evidence_source="discourse_prior_subjects",
        )
        assert r.kind == "pronoun_resolution"
        assert r.pronoun == "He"

    def test_empty_pronoun_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="pronoun"):
            PronounResolution(
                pronoun="", resolved_to="Bob",
                evidence_source="discourse_prior_subjects",
            )

    def test_empty_resolved_to_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="resolved_to"):
            PronounResolution(
                pronoun="He", resolved_to="",
                evidence_source="discourse_prior_subjects",
            )

    def test_invalid_evidence_source_refused(self) -> None:
        with pytest.raises(ComprehensionStateError, match="evidence_source"):
            PronounResolution(
                pronoun="He", resolved_to="Bob",
                evidence_source="grok_intuition",  # type: ignore[arg-type]
            )

    def test_kind_must_be_pronoun_resolution(self) -> None:
        with pytest.raises(ComprehensionStateError, match="kind"):
            PronounResolution(
                pronoun="He", resolved_to="Bob",
                evidence_source="discourse_prior_subjects",
                kind="wrong_kind",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# 3. Closed-set constants
# ---------------------------------------------------------------------------


class TestADR0174Phase3Constants:
    def test_pronoun_resolution_in_valid_kinds(self) -> None:
        assert "pronoun_resolution" in VALID_REFINEMENT_KINDS

    def test_actor_pronoun_in_valid_unresolved_slots(self) -> None:
        assert "actor_pronoun" in VALID_UNRESOLVED_SLOTS


# ---------------------------------------------------------------------------
# 4. End-to-end integration via parse_and_solve
# ---------------------------------------------------------------------------


class TestPhase3WiringEndToEnd:
    """Synthetic problems that exercise the Phase 3 wiring in
    math_candidate_graph.  These do NOT correspond to any train_sample
    case (the train_sample cases refuse for other narrowness reasons
    before reaching the pronoun-resolution path — see PHASE-3.1
    follow-up brief)."""

    def test_resolved_pronoun_emits_admitted_trace_event(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        # 'He collected N Pokemon cards' — regex returns 0 choices
        # (multi-word unit + acquisition verb), recognizer matches
        # discrete_count_statement and the pronoun marker fires.
        # 'Bob' is the discourse antecedent.
        text = (
            "Bob has 10 Pokemon cards. "
            "He collected 5 Pokemon cards. "
            "How many Pokemon cards does Bob have?"
        )
        r = parse_and_solve(text)
        # The downstream question regex doesn't admit this exact
        # phrasing — but our wiring should fire and produce a lookback
        # admitted event on the second sentence.
        lookback_events = [
            json.loads(ev) for ev in r.reader_trace
            if json.loads(ev).get("layer") == "lookback"
        ]
        assert any(
            ev.get("outcome") == "admitted"
            and ev.get("pronoun") == "He"
            and ev.get("resolved_to") == "Bob"
            for ev in lookback_events
        ), f"expected lookback admitted event; trace={lookback_events}"

    def test_multi_actor_ambiguous_refuses_with_no_antecedent_ambiguous(self) -> None:
        """ADR-0174 Phase 3a wrong=0 hazard defense — surfaced by
        2026-05-28 lookback review.

        When a problem has more than one distinct proper-noun subject
        in prior context, the _discourse_prior_subjects lookup is
        gender-blind and would silently pick the most-recent-prior as
        the antecedent. In 'Alice has 5. Bob has 3. She buys 2.',
        this would resolve 'She' to 'Bob' and attribute Alice's
        purchase to Bob — wrong attribution with no downstream safety
        net.

        Defense: refuse with no_antecedent_ambiguous trace event when
        multiple distinct proper-noun subjects appear in prior
        context. Refusal-preferring discipline preserves wrong=0.
        """
        # ADR-0174 Phase 4 amendment: when Phase 4's contemplate can
        # disambiguate the pronoun via gendered-names pack (mixed-
        # gender antecedents), the defense correctly does NOT fire —
        # the case admits via Phase 4. To test the defense in
        # isolation, use SAME-GENDER antecedents so Phase 4 returns
        # None (no disambiguation possible) and the defense still
        # fires.
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Alice has 5 Pokemon cards. "
            "Mary has 3 Pokemon cards. "
            "She collected 2 Pokemon cards. "
            "How many Pokemon cards does Alice have?"
        )
        r = parse_and_solve(text)
        # MUST refuse — wrong attribution is the hazard.
        assert r.answer is None
        lookback_events = [
            json.loads(ev) for ev in r.reader_trace
            if json.loads(ev).get("layer") == "lookback"
        ]
        ambig = [
            ev for ev in lookback_events
            if ev.get("outcome") == "no_antecedent_ambiguous"
        ]
        assert ambig, (
            f"expected no_antecedent_ambiguous event; trace={lookback_events}"
        )
        ev = ambig[0]
        assert "Alice" in ev["candidate_antecedents"]
        assert "Mary" in ev["candidate_antecedents"]
        assert ev["pronoun"] == "She"

    def test_single_actor_pronoun_still_resolves(self) -> None:
        """Counter-test: when there's only ONE distinct prior subject,
        the defense MUST NOT fire — pronoun resolution proceeds."""
        from generate.math_candidate_graph import parse_and_solve
        text = (
            "Bob has 10 Pokemon cards. "
            "He collected 5 Pokemon cards. "
            "How many Pokemon cards does Bob have?"
        )
        r = parse_and_solve(text)
        lookback_events = [
            json.loads(ev) for ev in r.reader_trace
            if json.loads(ev).get("layer") == "lookback"
        ]
        assert not any(
            ev.get("outcome") == "no_antecedent_ambiguous"
            for ev in lookback_events
        ), (
            f"single-actor case must not trigger ambiguity defense; "
            f"trace={lookback_events}"
        )
        assert any(
            ev.get("outcome") == "admitted" and ev.get("resolved_to") == "Bob"
            for ev in lookback_events
        )

    def test_no_antecedent_emits_no_antecedent_trace_event(self) -> None:
        from generate.math_candidate_graph import parse_and_solve
        # No proper-noun antecedent before the held pronoun sentence.
        text = (
            "He collected 5 Pokemon cards. "
            "How many Pokemon cards does he have?"
        )
        r = parse_and_solve(text)
        lookback_events = [
            json.loads(ev) for ev in r.reader_trace
            if json.loads(ev).get("layer") == "lookback"
        ]
        assert r.refusal_reason is not None or r.answer is None
        for ev in lookback_events:
            assert ev.get("outcome") in (
                "no_antecedent", "no_antecedent_ambiguous", "eliminated"
            ), f"unexpected lookback outcome on no-antecedent input: {ev}"


# ---------------------------------------------------------------------------
# 5. wrong=0 preservation on train_sample/v1
# ---------------------------------------------------------------------------


class TestWrongZeroPreservation:
    def test_train_sample_score_unchanged(self) -> None:
        """Phase 3 substrate must preserve the current train_sample score.

        Any change here would indicate the lookback path is firing on cases it
        should not, or breaking cases it should not.
        """
        import json
        from pathlib import Path
        from evals.gsm8k_math.train_sample.v1.runner import (
            build_report, _CASES_PATH,
        )
        cases = [
            json.loads(line)
            for line in Path(_CASES_PATH).open(encoding="utf-8")
            if line.strip()
        ]
        report = build_report(cases)
        counts = report["counts"]
        assert counts["wrong"] == 0, (
            f"wrong=0 invariant violated: {counts}"
        )
        assert counts["correct"] == 6, (
            f"correct count moved from 6 to {counts['correct']}; "
            "Phase 3a substrate should not lift score on this corpus "
            "(see PHASE-3.1 follow-up brief for what would lift it)"
        )
        assert counts["refused"] == 44, (
            f"refused count moved from 44 to {counts['refused']}"
        )
