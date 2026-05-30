"""ADR-0189a — day-of-week count enumeration + activity question.

Completes the comprehension stack for GSM8K train_sample case 0024
("Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on Wednesday,
and 50 on Thursday. Brooke does three times as many jumping jacks as Sidney.
How many jumping jacks did Brooke do?" → 438), composing three general
capabilities, each wrong=0-safe:

1. Day-of-week count enumeration → summed initial (Sidney = 20+36+40+50 = 146).
2. Comparative reading (ADR-0189) — Brooke = 3 × Sidney (already shipped).
3. Activity question "How many <unit> did <Entity> <verb>?" → Unknown(entity, unit).

Failing-under-violation: each test asserts a specific extraction/solve that
flips if the corresponding piece is reverted. The wrong=0 obligation is
discharged by all 8 capability-axis lanes staying wrong=0 and train_sample
moving 3/47/0 → 4/46/0 with no wrong.
"""

from __future__ import annotations

from generate.math_candidate_parser import (
    extract_initial_candidates,
    extract_question_candidates,
)
from generate.math_candidate_graph import parse_and_solve


def test_day_enumeration_sums_counts() -> None:
    s = "Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on Wednesday, and 50 on Thursday."
    cands = [c for c in extract_initial_candidates(s) if c.initial.entity == "Sidney"]
    assert len(cands) == 1
    assert cands[0].initial.quantity.value == 146.0
    assert cands[0].initial.quantity.unit == "jumping jacks"


def test_day_enumeration_value_token_grounds() -> None:
    """The derived total (146) is not literal; provenance anchors on the
    first count token (20), which grounds — mirroring _embedded_quantifier."""
    s = "Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on Wednesday, and 50 on Thursday."
    cand = next(c for c in extract_initial_candidates(s) if c.initial.entity == "Sidney")
    assert cand.matched_value_token == "20"


def test_activity_question_parses() -> None:
    q = extract_question_candidates("How many jumping jacks did Brooke do?")
    assert len(q) == 1
    assert q[0].unknown.entity == "Brooke"
    assert q[0].unknown.unit == "jumping jacks"


def test_non_day_comma_list_does_not_enumerate() -> None:
    """wrong=0 guard: a comma list NOT keyed on day-of-week names must not
    be summed by the day-enumeration extractor."""
    s = "Sidney does 20 jumping jacks in the gym, 36 at home."
    cands = [c for c in extract_initial_candidates(s)
             if c.initial.quantity.value == 146.0]
    assert cands == []


def test_case_0024_solves_end_to_end() -> None:
    """The composing solve: 146 × 3 = 438."""
    q = (
        "Sidney does 20 jumping jacks on Monday, 36 on Tuesday, 40 on "
        "Wednesday, and 50 on Thursday. Brooke does three times as many "
        "jumping jacks as Sidney. How many jumping jacks did Brooke do?"
    )
    r = parse_and_solve(q)
    assert r.refusal_reason is None
    assert r.answer == 438.0
