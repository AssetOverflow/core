"""Regression: ratified-recognizer skip-only fallback was a wrong>0 hazard.

A ratified ``discrete_count_statement`` recognizer (introduced 2026-05-26
by ADR-0163.D.2 / PR #315) over-matches any sentence containing a
number + noun, irrespective of the verb.  When the recognizer matched
but ``inject_from_match`` returned ``()``, the old code path silently
*dropped* the sentence and let the solver answer from whatever initial
state remained — exactly the case-0050-class hazard (silently admitting
a partial graph at the problem level).

This regression pins the corrected behaviour: recognized-but-uninjected
statements REFUSE.  When an injector lands that handles this shape, the
test continues to hold because the injector path returns choices and
the refusal branch is never reached.

Reference:
* ``feedback-wrong-zero-hazard-case-0050`` (memory)
* ADR-0167 §"correct-count greed" / Brief 11
* Original drop site: ``generate.math_candidate_graph`` recognizer branch
  at the end of ``per_sentence_choices`` enumeration
"""

from __future__ import annotations

import pytest

from generate.math_candidate_graph import parse_and_solve


@pytest.mark.parametrize(
    "verb",
    [
        # Real-English verbs the regex parser has no template for, but the
        # sentences are number+noun-shaped — the historical silent-drop
        # trigger.  Vetted: each verb falls through the parser's templates
        # AND is outside the comprehension reader's transactional verb
        # categories.  "donates" was considered and rejected for this list
        # because it resolves to a depletion verb on the existing regex
        # path.
        "contemplates",
        "ponders",
        "memorises",
    ],
)
def test_unparseable_verb_with_number_noun_refuses(verb: str) -> None:
    """When the regex parser cannot match a number+noun statement and the
    ratified recognizer matches but cannot inject typed solver state,
    parse_and_solve MUST refuse — not silently drop the statement and
    answer from whatever initial-state remains."""
    text = (
        f"Sam has 5 apples. Sam {verb} 3 apples. "
        f"How many apples does Sam have?"
    )
    result = parse_and_solve(text)
    assert not result.is_admitted, (
        f"silent admission with verb={verb!r}: answer={result.answer!r}, "
        f"graph={result.selected_graph!r} — this is the wrong=0 hazard "
        f"the skip-only fallback re-introduced and this fix retired."
    )


def test_unparseable_nonsense_verb_refuses() -> None:
    """Defence-in-depth: a token that is neither in the regex parser nor in
    any natural-language lexicon must still refuse."""
    text = (
        "Sam has 5 apples. Sam ipsum-doloriks 3 apples. "
        "How many apples does Sam have?"
    )
    result = parse_and_solve(text)
    assert not result.is_admitted
    assert result.answer is None


def test_known_initial_then_known_operation_still_admits() -> None:
    """Anti-regression: the fix must not break legitimate admissions where
    both the initial-state sentence and the operation sentence have
    verbs the parser knows."""
    text = "Sam has 5 apples. Sam gets 3 more apples. How many apples does Sam have?"
    result = parse_and_solve(text)
    assert result.is_admitted, f"legitimate problem refused: {result.refusal_reason!r}"
    assert result.answer == 8
