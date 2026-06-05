"""The symbolic reader — the ablation control arm and the C3 capability path.

It must be a *competent* reader (correct on the grammar, fences the same out-of-domain
cases, detects over-determination), so the ablation is a fair test of whether the field
adds anything over it. Unlike the field it has no precision limit (pure int).
"""

from __future__ import annotations

from generate.relational_symbolic_reader import READER_LINEAGE, read_relational


def test_commits_additive_more_than():
    r = read_relational(
        "Tom has 3 marbles. Jane has 5 more marbles than Tom. "
        "How many marbles does Jane have?"
    )
    assert not r.refused and r.answer == 8
    assert r.reader_lineage == READER_LINEAGE


def test_commits_part_whole_sum():
    r = read_relational(
        "Tom has 3 marbles. Jane has 5 more marbles than Tom. "
        "How many marbles do Tom and Jane have?"
    )
    assert not r.refused and r.answer == 11


def test_commits_beyond_field_ceiling():
    """The symbolic reader has no f64 precision limit — it commits where the field
    refuses (over_ceiling). This is the field's coverage liability, not a symbolic bug."""
    r = read_relational("Gus has 9000000 apples. How many apples does Gus have?")
    assert not r.refused and r.answer == 9000000


def test_fences_multiplicative():
    r = read_relational(
        "Tom has 3 marbles. Jane has twice as many marbles as Tom. "
        "How many marbles does Jane have?"
    )
    assert r.refused and r.refusal_reason == "fenced_multiplicative"


def test_detects_over_determination():
    """A competent reader refuses a conflicting re-statement (so the field's geometric
    coherence check is not a unique advantage)."""
    r = read_relational(
        "Tom has 3 marbles. Tom has 5 marbles. How many marbles does Tom have?"
    )
    assert r.refused and r.refusal_reason == "over_determined_conflict"


def test_refuses_forward_reference():
    r = read_relational(
        "Jane has 5 more marbles than Tom. Tom has 3 marbles. "
        "How many marbles does Jane have?"
    )
    assert r.refused and r.refusal_reason == "non_forward_substitutable"
