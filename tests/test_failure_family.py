"""Tests for the failure-family registry (N4).

Pins that the registry is a PARTITION (every reachable organ refusal reason maps to exactly
one family), that it covers the entire live refusal surface, that only the three R2 ``missing_*``
families are growth surfaces, and that correct wrong=0 boundaries stay refused with no proposal.
"""

from __future__ import annotations

from core.comprehension_attempt import classify_r1, classify_r2
from core.comprehension_attempt.failure_family import (
    ANSWER_KEY_CONTRADICTION,
    REGISTRY,
    enrich_family,
    family_for_reason,
)
from evals.constraint_oracle.runner import _load_r2_gold
from evals.setup_oracle.runner import _load_r1_gold

#: The full live refusal surface (R1 reader/admissibility, classify, R2 reader/solver/choice).
ALL_REASONS = {
    # R1
    "empty", "no_quantity_template", "non_digit_quantity", "non_identifier_name",
    "unreadable_quantity_query", "unreadable_quantity_clause", "no_single_quantity_query",
    "admissibility_refused", "multiple_inverse_bases", "multiple_partitions",
    "partition_query_mismatch", "partition_container_mismatch", "invalid_binding_graph",
    "unprojectable",
    # R2 reader
    "too_many_categories", "missing_total_count", "missing_weighted_total",
    "category_pair_not_found", "coefficient_unit_mismatch", "coefficient_conflict",
    "query_target_not_a_category",
    # R2 solver
    "indistinguishable_weights", "non_integer_solution", "negative_solution",
    "query_target_unsolved", "verification_failed",
    # R2 answer-choice
    "no_matching_option", "ambiguous_options", "no_options", "unknown_provided_label",
    "unparseable_option",
    # R3 rate reader
    "rate_unit_mismatch", "combined_rates", "missing_rate", "missing_time", "missing_quantity",
    "temporal_state", "query_target_unrecognized", "no_query", "not_rate_shaped",
    # R4 combined-rate (reader + solver reasons namespaced cmb_*; not_combined_rate_shaped is the
    # bare step-aside reason -> the cross input_shape family).
    "not_combined_rate_shaped",
    "cmb_rate_unit_mismatch", "cmb_combine_mode_ambiguous", "cmb_missing_second_rate",
    "cmb_three_or_more_rates", "cmb_reciprocal_work_rate_deferred", "cmb_clock_interval_deferred",
    "cmb_non_positive_net_rate", "cmb_non_integer_solution",
}


def test_registry_is_a_partition() -> None:
    seen: dict[str, str] = {}
    for family in REGISTRY:
        for reason in family.refusal_reasons:
            assert reason not in seen, f"{reason} in both {seen.get(reason)} and {family.name}"
            seen[reason] = family.name


def test_registry_covers_the_whole_refusal_surface() -> None:
    for reason in ALL_REASONS:
        assert family_for_reason(reason) is not None, f"unmapped reason: {reason}"


def test_every_gold_refusal_reason_maps_to_a_family() -> None:
    attempts = [classify_r2(f["text"]) for f in _load_r2_gold()]
    attempts += [classify_r1(f["text"]) for f in _load_r1_gold()]
    for att in attempts:
        if att.outcome == "setup_refused":
            assert family_for_reason(att.refusal_reason) is not None, att.refusal_reason


def test_only_precise_missing_totals_are_reachable_growth_surfaces() -> None:
    # Only the PRECISE R2 gaps are reachable growth surfaces. category_pair_not_found is too broad
    # (fires on any non-R2 text), so it maps to input_shape, and missing_category_pair is reserved.
    growth = {f.name for f in REGISTRY if f.proposal_allowed and f.refusal_reasons}
    assert growth == {
        "missing_total_count", "missing_weighted_total", "unsupported_rate_duration",
        "cmb_unsupported_rate_count", "cmb_unsupported_reciprocal", "cmb_unsupported_clock_interval",
    }
    assert family_for_reason("category_pair_not_found").name == "input_shape"
    for f in REGISTRY:
        if f.proposal_allowed:
            assert not f.must_remain_refused  # a growth surface is never a hard boundary


def test_correct_boundaries_stay_refused_with_no_proposal() -> None:
    for reason in ("too_many_categories", "non_integer_solution", "negative_solution",
                   "unreadable_quantity_clause", "indistinguishable_weights",
                   "coefficient_unit_mismatch", "admissibility_refused"):
        fam = family_for_reason(reason)
        assert fam is not None and fam.must_remain_refused and not fam.proposal_allowed, reason


def test_growth_reasons_allow_proposals() -> None:
    for reason in ("missing_total_count", "missing_weighted_total"):
        fam = family_for_reason(reason)
        assert fam is not None and fam.proposal_allowed and not fam.must_remain_refused
        assert fam.proposal_target == "r2_gold_fixture"


def test_enrich_sets_family_on_a_refused_attempt() -> None:
    fx = next(f for f in _load_r2_gold() if f["expect"] == "reader_refuses")
    enriched = enrich_family(classify_r2(fx["text"]))
    assert enriched.family is not None
    assert family_for_reason(enriched.refusal_reason).name == enriched.family


def test_contradiction_family_reports_and_never_proposes() -> None:
    assert ANSWER_KEY_CONTRADICTION.name == "answer_key_contradiction"
    assert not ANSWER_KEY_CONTRADICTION.proposal_allowed
    assert "report" in ANSWER_KEY_CONTRADICTION.safe_next_action


def test_family_for_reason_none_is_none() -> None:
    assert family_for_reason(None) is None
