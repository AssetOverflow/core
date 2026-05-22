from __future__ import annotations

from core.capability import (
    CapabilityArtifactQuery,
    artifact_report,
    chain_report,
    evidence_plan_report,
    flag_report,
    ledger_report,
)
from core.config import DEFAULT_CONFIG


def test_chain_report_exposes_required_count_axes() -> None:
    report = chain_report()

    assert report["active_chains"] == sum(report["by_corpus"].values())
    assert report["by_intent_shape"]
    assert report["by_connective"]
    assert report["by_operator_family"]
    assert "by_pack" in report
    assert "by_domain" in report
    assert report["formula"]["chains_required"] == 8 * 5 * 5
    assert report["formula"]["chains_remaining"] == (
        report["formula"]["chains_required"] - report["formula"]["chains_present"]
    )
    assert report["missing_target_intent_shapes"] == []
    for domain, operators in {
        "systems_software": ("transitive", "causal"),
        "mathematics_logic": ("transitive", "proof_chain", "contradiction"),
        "physics": ("causal", "modal"),
    }.items():
        domain_ops = report["by_domain_operator_family"][domain]
        for op in operators:
            assert domain_ops[op] >= 8
        assert len(report["by_domain_intent_shape"][domain]) >= 3
    he_grc_ops = report["by_domain_operator_family"]["hebrew_greek_textual_reasoning"]
    assert he_grc_ops["causal"] >= 8
    assert he_grc_ops["contradiction"] >= 8
    he_grc_intents = report["by_domain_intent_shape"]["hebrew_greek_textual_reasoning"]
    assert len(he_grc_intents) >= 3
    philosophy_ops = report["by_domain_operator_family"]["philosophy_theology"]
    assert philosophy_ops["modal"] >= 8
    assert philosophy_ops["contradiction"] >= 8
    philosophy_intents = report["by_domain_intent_shape"]["philosophy_theology"]
    assert len(philosophy_intents) >= 3


def test_flag_report_classification_matches_actual_defaults() -> None:
    """Catalog classification must match DEFAULT_CONFIG's actual values.

    A flag in ``flag_shipped_default_off`` MUST be False on DEFAULT_CONFIG;
    a flag in ``flag_shipped_default_on`` MUST be True. Drift between the
    catalog and the runtime default is itself a bug — catching it here
    prevents the kind of silent re-classification that landed when
    ``discourse_planner`` was flipped to True on 2026-05-21 without
    updating the catalog.
    """
    report = flag_report()
    default_off = {row["flag"] for row in report["flag_shipped_default_off"]}
    default_on = {row["flag"] for row in report["flag_shipped_default_on"]}

    for flag in (
        "realizer_grounded_authority",
        "composed_surface",
        "transitive_surface",
        "gloss_aware_cause",
        "thread_anaphora",
    ):
        assert flag in default_off, f"{flag!r} expected in default_off"
        assert getattr(DEFAULT_CONFIG, flag) is False, (
            f"{flag!r} catalog says default_off but DEFAULT_CONFIG has it True"
        )

    # discourse_planner shipped flag-off and was flipped to default-on
    # on 2026-05-21 after cognition-eval byte-equality verification.
    # The catalog state must match.
    assert "discourse_planner" in default_on, (
        "discourse_planner expected in default_on after the 2026-05-21 flip"
    )
    assert DEFAULT_CONFIG.discourse_planner is True

    # stop_tokens is None-by-default (not a bool); kept in default_off
    # because its absence is the "off" state.
    assert "stop_tokens" in default_off
    assert DEFAULT_CONFIG.stop_tokens is None

    assert report["substrate_shipped_flag_missing"] == [
        {"flag": "compound_intent_dispatch", "adr": "ADR-0089-C2"}
    ]


def test_flag_catalog_state_is_consistent_with_default_config() -> None:
    """Cross-check every catalog entry against DEFAULT_CONFIG.

    Catches any future drift: if someone changes a default in
    ``core.config`` without updating the catalog state, this test
    fails before the lane SHAs can shift.
    """
    report = flag_report()
    for row in report["flag_shipped_default_off"]:
        flag = row["flag"]
        if not hasattr(DEFAULT_CONFIG, flag):
            continue  # substrate flag without a runtime knob
        value = getattr(DEFAULT_CONFIG, flag)
        # ``stop_tokens`` is None-by-default (not a bool). All others
        # should be ``False`` to honor the ``default_off`` classification.
        if flag == "stop_tokens":
            assert value is None
        else:
            assert value is False, (
                f"catalog classifies {flag!r} as default_off but "
                f"DEFAULT_CONFIG has it {value!r}"
            )
    for row in report["flag_shipped_default_on"]:
        flag = row["flag"]
        if not hasattr(DEFAULT_CONFIG, flag):
            continue
        assert getattr(DEFAULT_CONFIG, flag) is True, (
            f"catalog classifies {flag!r} as default_on but "
            f"DEFAULT_CONFIG has it {getattr(DEFAULT_CONFIG, flag)!r}"
        )


def test_ledger_status_is_predicate_derived() -> None:
    report = ledger_report()
    rows = {row["domain"]: row for row in report["domains"]}

    assert report["evidence_counts"]["eval_results"] > 0
    assert report["evidence_counts"]["mastery_reports"] >= 0
    assert report["evidence_counts"]["pack_measurements_present"] is True
    assert report["evidence_counts"]["reviewers_present"] is True
    assert report["evidence_counts"]["gaps_present"] is True

    registry_status = report["evidence_counts"]["reviewer_registry"]
    assert registry_status["valid"] is True
    assert registry_status["schema_version"] == 1
    assert registry_status["reviewer_count"] >= 1
    assert "shay-j" in registry_status["reviewer_ids"]
    assert registry_status["error"] is None

    systems = rows["systems_software"]
    assert systems["status"] == "reasoning-capable"
    assert systems["predicates"]["reasoning_capable"] is True
    assert systems["open_gaps"] == []

    math = rows["mathematics_logic"]
    # ADR-0110 — first expert-demo promotion lands on math.
    assert math["status"] == "expert-demo"
    assert math["predicates"]["reasoning_capable"] is True
    assert math["predicates"]["expert_demo"] is True
    assert math["open_gaps"] == []

    physics = rows["physics"]
    assert physics["status"] == "reasoning-capable"
    assert physics["predicates"]["reasoning_capable"] is True
    assert physics["open_gaps"] == []

    he_grc = rows["hebrew_greek_textual_reasoning"]
    assert he_grc["predicates"]["seeded"] is True
    assert he_grc["predicates"]["grounded"] is True
    assert he_grc["status"] == "reasoning-capable"
    assert he_grc["predicates"]["reasoning_capable"] is True
    assert "gap:grc_he_glosses_absent" not in he_grc["open_gaps"]
    assert he_grc["open_gaps"] == []

    philosophy = rows["philosophy_theology"]
    assert philosophy["status"] == "reasoning-capable"
    assert philosophy["predicates"]["reasoning_capable"] is True
    assert all(contract["valid"] for contract in philosophy["domain_contracts"])
    assert all(contract["present"] is False for contract in philosophy["domain_contracts"])
    assert "gap:en_core_cognition_v1_gloss_coverage_below_threshold" not in philosophy["open_gaps"]
    assert philosophy["open_gaps"] == []
    assert philosophy["operator_chain_coverage"]["modal"]["ready"] is True
    assert philosophy["operator_chain_coverage"]["contradiction"]["ready"] is True


def test_artifact_report_is_deterministic_for_same_tuple() -> None:
    query = CapabilityArtifactQuery(lane="cognition", split="public", version="v1")

    first = artifact_report(query)
    second = artifact_report(query)

    assert first["artifact_id"] == second["artifact_id"]
    assert first["exists"] is True
    assert len(first["artifact_id"]) == 64


def test_evidence_plan_is_content_addressed_and_non_mutating() -> None:
    first = evidence_plan_report()
    second = evidence_plan_report()

    assert first["pack_hash"] == second["pack_hash"]
    assert first["workers_promote_packs"] is False
    assert {job["job_type"] for job in first["jobs"]} == {
        "pack_validation",
        "eval_matrix",
        "replay_sweep",
        "vault_benchmark",
        "curriculum_experiment",
    }
    for job in first["jobs"]:
        assert len(job["job_id"]) == 64
        assert job["mutates_packs"] is False
        assert job["promotion"] == "reviewed-mainline-only"
