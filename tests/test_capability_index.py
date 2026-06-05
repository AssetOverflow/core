"""Cross-domain capability index — AGI-roadmap Phase 1 (MEASURE).

The yardstick that gates every later "more capable" claim. Two honest axes —
**accuracy** (of committed answers; wrong stays 0 in assert mode) and **coverage**
(attempted-not-refused) — aggregated across domains so it CANNOT be gamed by a
narrow per-domain win: the headline coverage is the GEOMETRIC MEAN across domains,
which only rises if *every* domain rises. A hack that maxes one lane and leaves
the rest at zero leaves the geomean ~0.
"""

from __future__ import annotations

from evals.capability_index.index import (
    DomainResult,
    aggregate,
    deterministic_digest,
)


def _d(domain: str, correct: int, wrong: int, refused: int) -> DomainResult:
    return DomainResult(domain=domain, correct=correct, wrong=wrong, refused=refused)


def test_domain_result_axes() -> None:
    r = _d("logic", correct=8, wrong=0, refused=2)
    assert r.total == 10
    assert r.attempted == 8
    assert r.coverage == 0.8
    assert r.accuracy == 1.0  # of committed answers


def test_aggregate_axes_micro() -> None:
    idx = aggregate([_d("a", 6, 0, 4), _d("b", 2, 0, 8)])
    assert idx.wrong_total == 0
    assert idx.coverage == 0.4  # (6+2)/(10+10) micro
    assert idx.accuracy == 1.0  # no wrong
    assert idx.breadth == 2  # both domains have some coverage


def test_geomean_coverage_resists_narrow_gaming() -> None:
    # A NARROW hack: one domain maxed, the rest at zero coverage.
    narrow = aggregate(
        [_d("gamed", 10, 0, 0), _d("x", 0, 0, 10), _d("y", 0, 0, 10)]
    )
    # A BALANCED engine: every domain partially covered.
    balanced = aggregate(
        [_d("gamed", 4, 0, 6), _d("x", 4, 0, 6), _d("y", 4, 0, 6)]
    )
    # Micro-coverage is similar (~0.33 vs 0.40), but the geomean exposes the hack:
    assert narrow.coverage_geomean == 0.0  # any zero-coverage domain -> geomean 0
    assert balanced.coverage_geomean > 0.39
    # The capability score (geomean × accuracy) refuses to reward the narrow hack.
    assert narrow.capability_score == 0.0
    assert balanced.capability_score > 0.39


def test_balanced_progress_moves_the_score_monotonically() -> None:
    low = aggregate([_d("a", 2, 0, 8), _d("b", 2, 0, 8)])
    high = aggregate([_d("a", 6, 0, 4), _d("b", 6, 0, 4)])
    assert high.coverage_geomean > low.coverage_geomean
    assert high.capability_score > low.capability_score


def test_wrong_is_a_hard_gate() -> None:
    # In assert mode wrong MUST be 0; any wrong invalidates the index (score 0)
    # and is surfaced — never averaged away.
    idx = aggregate([_d("a", 8, 1, 1), _d("b", 5, 0, 5)])
    assert idx.wrong_total == 1
    assert idx.assert_mode_valid is False
    assert idx.capability_score == 0.0  # wrong=0 is non-negotiable in assert mode


def test_digest_is_deterministic_and_bites() -> None:
    a = aggregate([_d("a", 6, 0, 4), _d("b", 2, 0, 8)])
    b = aggregate([_d("a", 6, 0, 4), _d("b", 2, 0, 8)])
    assert deterministic_digest(a) == deterministic_digest(b)
    moved = aggregate([_d("a", 7, 0, 3), _d("b", 2, 0, 8)])
    assert deterministic_digest(moved) != deterministic_digest(a)


def test_empty_index_is_well_defined() -> None:
    idx = aggregate([])
    assert idx.coverage == 0.0
    assert idx.coverage_geomean == 0.0
    assert idx.breadth == 0
    assert idx.capability_score == 0.0


def test_real_lanes_compose_into_the_index_with_wrong_zero() -> None:
    # The three structured-input reasoning lanes PLUS the three Phase-2a
    # comprehension lanes (general reader scored on prose) compose into the
    # cross-domain index with zero wrong commits.
    from evals.capability_index.adapters import collect_domain_results

    collection = collect_domain_results()
    assert collection.not_covered == ()  # every adapter ran (no silent drop)
    idx = aggregate(list(collection.results))
    assert idx.wrong_total == 0
    assert idx.assert_mode_valid
    assert idx.breadth == 6
    assert {d.domain for d in idx.domains} == {
        "deductive_logic",
        "dimensional",
        "relational_metric",
        "comprehension_set_membership",
        "comprehension_syllogism",
        "comprehension_total_ordering",
    }
    assert idx.capability_score > 0.5  # real, non-trivial cross-domain capability


def test_index_report_is_deterministic_across_runs() -> None:
    # The capability number is reproducible — improvement is a replayable curve.
    from evals.capability_index.adapters import collect_domain_results

    a = deterministic_digest(aggregate(list(collect_domain_results().results)))
    b = deterministic_digest(aggregate(list(collect_domain_results().results)))
    assert a == b
