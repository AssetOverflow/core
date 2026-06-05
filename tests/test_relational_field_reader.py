"""Phase W — the geometric field reader on forward-substitutable relations.

Proves the field reads problem TEXT into an exact integer answer via conformal
translators + projective read-back, and REFUSES (never guesses) outside its sealed
metric grammar. wrong==0 is structural: every commit is an exact-integer read-back.
"""

from __future__ import annotations

from generate.relational_field_reader import READER_LINEAGE, read_relational


# --- commits: the field reads correctly ------------------------------------


def test_fact_then_more_than():
    r = read_relational(
        "Tom has 3 marbles. Jane has 5 more marbles than Tom. "
        "How many marbles does Jane have?"
    )
    assert not r.refused
    assert r.answer == 8
    assert r.answer_unit == "marbles"
    assert r.reader_lineage == READER_LINEAGE


def test_fewer_than():
    r = read_relational(
        "Anna has 20 apples. Ben has 7 fewer apples than Anna. "
        "How many apples does Ben have?"
    )
    assert not r.refused
    assert r.answer == 13


def test_chained_forward_substitution():
    r = read_relational(
        "Tom has 4 coins. Jane has 6 more coins than Tom. "
        "Sara has 10 more coins than Jane. How many coins does Sara have?"
    )
    assert not r.refused
    assert r.answer == 20  # 4 -> 10 -> 20


def test_part_whole_sum_query():
    r = read_relational(
        "Tom has 3 marbles. Jane has 5 more marbles than Tom. "
        "How many marbles do Tom and Jane have?"
    )
    assert not r.refused
    assert r.answer == 11  # 3 + 8


def test_large_value_within_ceiling_is_exact():
    # x=12345 already collapses f32 (the n_o weight loses the ±1 past ~4096);
    # f64 + translator stays exact here.
    r = read_relational(
        "Tom has 12345 dollars. Jane has 5000 more dollars than Tom. "
        "How many dollars does Jane have?"
    )
    assert not r.refused
    assert r.answer == 17345


def test_never_commits_a_drifted_answer():
    """wrong==0 guard: at a scale where the translator sandwich loses f64 integer
    exactness, the field REFUSES (precision_drift) rather than commit a wrong int."""
    r = read_relational(
        "Tom has 123456 dollars. Jane has 654321 more dollars than Tom. "
        "How many dollars does Jane have?"
    )
    # Either it commits the EXACT answer, or it refuses — never a wrong integer.
    assert r.refused or r.answer == 777777
    if r.refused:
        assert r.refusal_reason == "precision_drift"


# --- refusals: the field declines outside its sealed grammar ----------------


def test_refuses_multiplicative():
    r = read_relational(
        "Tom has 3 marbles. Jane has twice as many marbles as Tom. "
        "How many marbles does Jane have?"
    )
    assert r.refused
    assert r.refusal_reason == "fenced_multiplicative"


def test_refuses_times_cue():
    r = read_relational(
        "Tom has 3 marbles. Jane has 4 times as many marbles as Tom. "
        "How many marbles does Jane have?"
    )
    assert r.refused
    assert r.refusal_reason == "fenced_multiplicative"


def test_refuses_over_ceiling():
    r = read_relational(
        "Tom has 9000000 marbles. How many marbles does Tom have?"
    )
    assert r.refused
    assert r.refusal_reason == "over_ceiling"


def test_refuses_forward_reference():
    r = read_relational(
        "Jane has 5 more marbles than Tom. Tom has 3 marbles. "
        "How many marbles does Jane have?"
    )
    assert r.refused
    assert r.refusal_reason == "non_forward_substitutable"


def test_refuses_no_question():
    r = read_relational("Tom has 3 marbles. Jane has 5 more marbles than Tom.")
    assert r.refused
    assert r.refusal_reason == "no_query"


def test_refuses_negative_quantity():
    r = read_relational(
        "Tom has 3 marbles. Jane has 5 fewer marbles than Tom. "
        "How many marbles does Jane have?"
    )
    assert r.refused
    assert r.refusal_reason == "negative_quantity"


def test_refuses_empty():
    assert read_relational("").refused
    assert read_relational("   ").refusal_reason == "empty_input"
