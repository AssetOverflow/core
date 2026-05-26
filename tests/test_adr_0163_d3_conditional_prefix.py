"""ADR-0163.D.3 — conditional-prefix recovery for question admission.

When a question carries an ``If X, ...`` conditional prefix, the
existing question regex misses it.  Phase D.3 strips the prefix and
re-tries via the same admission path.  Result: the
``nested_question_target`` shape (11 of 38 GSM8K train_sample
question refusals post-Phase-D) becomes admissible without changing
the underlying parser regex or the solver.

The transformation is deterministic and pure.  wrong=0 invariant is
preserved by construction — a recovered candidate flows through the
same ``_question_admissible`` gate as any other parser output.
"""

from __future__ import annotations

import pytest

from generate.math_candidate_graph import (
    _filtered_question_choices,
    _strip_conditional_prefix,
)


# ---------------------------------------------------------------------------
# _strip_conditional_prefix is pure + deterministic
# ---------------------------------------------------------------------------


class TestStripConditionalPrefix:
    def test_strips_canonical_if_prefix(self) -> None:
        out = _strip_conditional_prefix(
            "If she works 10 hours every day for 5 days, "
            "how much money does she make?"
        )
        assert out == "How much money does she make?"

    def test_uppercases_leading_letter(self) -> None:
        out = _strip_conditional_prefix(
            "If Jen has 150 ducks, how many total birds does she have?"
        )
        assert out is not None and out.startswith("How ")

    def test_returns_none_when_no_prefix(self) -> None:
        assert _strip_conditional_prefix("How many oysters in 2 hours?") is None

    def test_returns_none_on_malformed_if(self) -> None:
        assert _strip_conditional_prefix("If") is None

    def test_handles_lowercase_if(self) -> None:
        # Case-insensitive prefix match.
        out = _strip_conditional_prefix(
            "if Marnie has 50 beads, how many bracelets can she make?"
        )
        assert out is not None
        assert out.startswith("How many bracelets")

    def test_is_pure_deterministic(self) -> None:
        prompt = "If x, how many y does z have?"
        first = _strip_conditional_prefix(prompt)
        second = _strip_conditional_prefix(prompt)
        assert first == second

    def test_no_mutation_of_input(self) -> None:
        prompt = "If z, how many y does w have?"
        original = str(prompt)
        _strip_conditional_prefix(prompt)
        assert prompt == original  # str immutability check + no in-place edit


# ---------------------------------------------------------------------------
# _filtered_question_choices recovers via prefix strip when the bare
# parser fails
# ---------------------------------------------------------------------------


class TestQuestionRecovery:
    def test_bare_how_many_still_admits(self) -> None:
        """Pre-D.3 path stays — bare ``How many X does Y have?`` admits
        without conditional-prefix recovery."""
        out = _filtered_question_choices("How many apples does Tom have?")
        # The parser handles this; recovery should not fire.
        assert out, "bare canonical form must still admit"

    def test_conditional_prefix_recovers(self) -> None:
        """ADR-0163.D.3 — ``If X, how many Y does Z have?`` admits via
        prefix-strip recovery."""
        with_prefix = "If something, how many apples does Tom have?"
        bare = "How many apples does Tom have?"
        recovered = _filtered_question_choices(with_prefix)
        baseline = _filtered_question_choices(bare)
        assert len(recovered) == len(baseline)

    def test_non_question_returns_empty(self) -> None:
        assert _filtered_question_choices("Tom has 5 apples.") == []

    def test_recovery_returns_empty_when_suffix_unparseable(self) -> None:
        """If the suffix is still outside the parser's accepted shapes,
        admission stays empty.  No false admission.  wrong=0 by
        construction."""
        out = _filtered_question_choices(
            "If X, this is not even a question shape."
        )
        assert out == []


# ---------------------------------------------------------------------------
# Real GSM8K train_sample examples — the cases this phase is designed
# to lift.  These are the literal questions from the still-refused 38
# that carry the conditional-prefix shape.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "If she works 10 hours every day for 5 days, how much money does she make?",
        "If 50 beads are used to make one bracelet, how many bracelets will Marnie be able to make out of the beads she bought?",
        "If Jen has 150 ducks, how many total birds does she have?",
    ],
)
def test_real_gsm8k_conditional_prefixes_strip_cleanly(question: str) -> None:
    """The prefix-strip operation succeeds on real GSM8K conditional
    questions.  Whether the SUFFIX is admissible by the parser is a
    separate concern — this test pins only the deterministic prefix
    removal.
    """
    stripped = _strip_conditional_prefix(question)
    assert stripped is not None
    assert stripped.lower().startswith("how ")
