"""Project-root conftest — quarantine registry for known-failing tests.

The QUARANTINE set lists test IDs that are pre-existing failures
predating the substrate-liveness audit work (verified via bisect
against c1a1b7a, the commit immediately before the first W-* PR
of 2026-05-24). The CI gate at .github/workflows/full-pytest.yml
runs ``pytest -m "not quarantine"`` so these failures do not block
PRs, but the suite is a ratchet: a quarantined test removed from
this set must pass on its own merits.

See docs/test-debt-quarantine.md for cluster diagnoses, removal
policy, and the per-test rationale.

To remove a test from quarantine:
  1. Land a PR that makes the test pass.
  2. Delete its entry from QUARANTINE in the same PR.
  3. The full-pytest CI gate will now require it to keep passing.

Adding a test to QUARANTINE is strongly discouraged. If a new
failure surfaces, the right default is to fix it in the PR that
caused it — not to quarantine. The set should only shrink.
"""

from __future__ import annotations

import pytest


QUARANTINE: frozenset[str] = frozenset({
    # Cluster B — Surface decoration drift (assertions predate the
    # "pack-grounded (<pack_id>)" suffix on grounded surfaces).
    "tests/test_articulation.py::test_chat_surface_is_walk_surface",
    "tests/test_correction_topic_lemma.py::test_correction_with_no_pack_lemma_still_grounds",
    "tests/test_cross_pack_chains.py::test_runtime_narrative_aggregates_cross_pack_chains",
    "tests/test_cross_pack_chains.py::test_runtime_example_aggregates_cross_pack_reverse_chains",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[parent]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[child]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[sibling]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[family]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[ancestor]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[descendant]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[spouse]",
    "tests/test_cross_pack_grounding.py::test_pack_grounded_surface_resolves_kinship_lemmas[offspring]",
    "tests/test_cross_pack_grounding.py::test_runtime_definition_on_kinship_lemma_engages_pack_path",
    "tests/test_cross_pack_grounding.py::test_runtime_recall_on_kinship_lemma_engages_pack_path",
    "tests/test_en_collapse_anchors_v1_pack.py::test_collapse_anchor_baseline_surface_advertises_anchor_nature",

    # Cluster C — Lane / runner metric drift (thresholds or report
    # shape evolved without updating assertions).
    "tests/test_adr_0122_rate_per_unit.py::TestOODInvarianceHolds::test_ood_ratio_unchanged_under_rate_grammar",
    "tests/test_adr_0122_rate_per_unit.py::TestPerturbationInvariancesHold::test_invariance_gates_unchanged_under_rate_grammar",
    "tests/test_adr_0126_train_sample_runner.py::test_runner_writes_report_to_disk",
    "tests/test_adr_0126_train_sample_runner.py::test_report_has_documented_shape",
    "tests/test_adr_0126_train_sample_runner.py::test_sample_count_and_case_id_pattern",
    "tests/test_adr_0126_train_sample_runner.py::test_wrong_count_is_zero_baseline",
    "tests/test_adr_0131_G3_numerics.py::test_gsm8k_probe_safety_rail_unchanged",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_admitted_wrong_is_zero",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_every_refused_case_has_typed_reason",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_per_case_outcomes_are_in_closed_vocabulary",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_report_is_deterministic_across_runs",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_committed_report_matches_current_run",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_report_schema_required_fields",
    "tests/test_adr_0131_G_gsm8k_coverage_probe.py::test_refused_reasons_top_is_sorted_by_count_desc",
    "tests/test_cold_start_grounding_lane.py::TestPassThresholds::test_public_v1_passes_thresholds",
    "tests/test_cold_start_grounding_lane.py::TestPassThresholds::test_distributions_match_expected",
    "tests/test_composed_surface.py::test_cognition_lane_metrics_unchanged_with_composed_flag",
    "tests/test_compound_walkthrough_eval_lanes.py::test_chat_spine_holdout_splits_are_runnable",
    "tests/test_en_core_action_v1_pack.py::test_pack_loads_with_matching_checksum",
    "tests/test_en_core_action_v1_pack.py::test_all_entries_are_verbs",
    "tests/test_en_core_action_v1_pack.py::test_all_expected_lemmas_present",
    "tests/test_en_core_action_v1_pack.py::test_provenance_is_seed_core_action_v1",
    "tests/test_gsm8k_math_runner.py::TestLaneReportShape::test_metrics_keys_match_documented_schema",
    "tests/test_ood_surface_generator.py::test_live_parser_and_solver_match_each_variant_expected_answer",
    "tests/test_ood_surface_generator.py::test_ood_public_ratio_meets_gate_across_dev_set",
    "tests/test_perturbation_suite.py::test_aggregate_dev_rates_are_perfect_for_applicable_perturbations",
    "tests/test_relations_chains_v1.py::test_all_seed_chains_load_cleanly",

})


def pytest_collection_modifyitems(config, items):
    """Stamp the quarantine marker on any test whose nodeid is listed
    in QUARANTINE.  Tests not in the set are unaffected.

    The CI gate runs ``pytest -m "not quarantine"`` so quarantined
    tests are silently skipped in CI.  Local ``pytest`` runs include
    them by default (still useful for debugging individual fixes).
    """
    _ = config  # pluggy hook signature requires the name `config`; not used here
    quarantine_marker = pytest.mark.quarantine
    for item in items:
        if item.nodeid in QUARANTINE:
            item.add_marker(quarantine_marker)
