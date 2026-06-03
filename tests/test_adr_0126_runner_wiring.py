"""ADR-0126 P4 — tests for the candidate-graph scorer wiring.

Proves :func:`evals.gsm8k_math.runner._score_one_candidate_graph`:

- Produces ``correct`` on simple cases that the legacy ``_score_one``
  also handles (no regression on solvable cases).
- Produces ``correct`` on cases that the legacy ``_score_one`` would
  ``refuse`` because of restrictive verb tables (the whole point of
  the architecture pivot).
- Produces ``refused`` (never ``wrong``) on out-of-grammar cases —
  the ``wrong == 0`` invariant is preserved.
"""

from __future__ import annotations

from evals.gsm8k_math.runner import _score_one, _score_one_candidate_graph


def _case(problem: str, *, answer: float, unit: str = "") -> dict[str, object]:
    return {
        "id": "test-case",
        "problem": problem,
        "expected_answer": answer,
        "expected_unit": unit,
    }


class TestNoRegressionOnLegacySolvable:
    """Cases the legacy parser handles must still be correct."""

    def test_simple_add(self) -> None:
        case = _case(
            "Sam has 5 apples. Sam buys 3 apples. "
            "How many apples does Sam have?",
            answer=8.0, unit="apples",
        )
        # Both pipelines should produce correct.
        assert _score_one(case).outcome == "correct"
        assert _score_one_candidate_graph(case).outcome == "correct"

    def test_simple_subtract(self) -> None:
        case = _case(
            "Sam has 10 apples. Sam eats 3 apples. "
            "How many apples does Sam have?",
            answer=7.0, unit="apples",
        )
        assert _score_one(case).outcome == "correct"
        assert _score_one_candidate_graph(case).outcome == "correct"

    def test_transfer(self) -> None:
        case = _case(
            "Sam has 8 apples. Tom has 2 apples. "
            "Sam gives 3 apples to Tom. "
            "How many apples does Tom have?",
            answer=5.0, unit="apples",
        )
        assert _score_one(case).outcome == "correct"
        assert _score_one_candidate_graph(case).outcome == "correct"


class TestLiftOnPermissiveVerbs:
    """Cases the legacy parser refuses must now solve."""

    def test_bought_past_tense(self) -> None:
        case = _case(
            "Sam has 5 apples. Sam bought 3 apples. "
            "How many apples does Sam have?",
            answer=8.0, unit="apples",
        )
        legacy = _score_one(case)
        new = _score_one_candidate_graph(case)
        # Legacy refuses ('bought' not in _ADD_VERBS); new solves.
        assert legacy.outcome == "refused"
        assert new.outcome == "correct"

    def test_ate_past_tense(self) -> None:
        case = _case(
            "Sam has 10 apples. Sam ate 3 apples. "
            "How many apples does Sam have?",
            answer=7.0, unit="apples",
        )
        legacy = _score_one(case)
        new = _score_one_candidate_graph(case)
        assert legacy.outcome == "refused"
        assert new.outcome == "correct"

    def test_bakes_production_verb(self) -> None:
        case = _case(
            "Sam has 2 pies. Sam bakes 4 pies. "
            "How many pies does Sam have?",
            answer=6.0, unit="pies",
        )
        legacy = _score_one(case)
        new = _score_one_candidate_graph(case)
        assert legacy.outcome == "refused"
        assert new.outcome == "correct"


class TestWrongZeroPreserved:
    """Out-of-grammar cases must REFUSE, never wrong."""

    def test_unparseable_refuses(self) -> None:
        case = _case(
            "Sam has 5 apples. Sam contemplates 3 apples. "
            "How many apples does Sam have?",
            answer=8.0, unit="apples",
        )
        outcome = _score_one_candidate_graph(case)
        assert outcome.outcome == "refused"
        # The unparseable "contemplates" sentence refuses. Historically this was
        # "no admissible candidate"; post #359 the recognizer matches the
        # discrete-count shape but produces no injection, giving the more specific
        # "produced no injection" reason. Either non-admission phrasing is valid;
        # the load-bearing invariant is that it refuses (wrong=0).
        assert (
            "no admissible candidate" in outcome.reason
            or "produced no injection" in outcome.reason
        )

    def test_question_with_unknown_entity_refuses(self) -> None:
        case = _case(
            "Sam has 5 apples. "
            "How many apples does Alice have?",
            answer=0.0, unit="apples",
        )
        outcome = _score_one_candidate_graph(case)
        # Either refused (graph rejects unknown entity) or refused via
        # solve failure — both preserve wrong == 0.
        assert outcome.outcome == "refused"

    def test_value_only_grading_for_train_sample_shape(self) -> None:
        # When expected_unit == "" (the train-sample shape), the runner
        # grades on numeric value alone.
        case = _case(
            "Sam has 5 apples. Sam buys 3 apples. "
            "How many apples does Sam have?",
            answer=8.0, unit="",  # empty
        )
        assert _score_one_candidate_graph(case).outcome == "correct"
