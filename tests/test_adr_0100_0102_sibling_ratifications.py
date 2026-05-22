"""ADR-0100 / ADR-0101 / ADR-0102 — sibling domain ratification tests.

Pins the load-bearing invariants for the three sibling domains
ratified after ADR-0097's mathematics_logic template:

- ADR-0100 ``physics``
- ADR-0101 ``systems_software``
- ADR-0102 ``hebrew_greek_textual_reasoning`` (multi-pack)

Each domain's capability ledger row must report ``reasoning-capable``,
provenance must point at the right ADR, and ``expert-demo`` stays
gated for a future ADR.
"""

from __future__ import annotations

import pytest

from core.capability import evaluate_domain_contract, ledger_report


_DOMAINS: dict[str, dict] = {
    "physics": {
        "adr": "adr-0100",
        "packs": ("en_physics_v1",),
        "claimed_operators": ("causal", "modal"),
        "min_intent_shapes": 3,
        "expected_chains": ["physics_chains_v1"],
        "expected_lanes": {
            "foundational_physics_ood",
            "inference_closure",
            "fabrication_control",
        },
    },
    "systems_software": {
        "adr": "adr-0101",
        "packs": ("en_systems_software_v1",),
        "claimed_operators": ("transitive", "causal"),
        "min_intent_shapes": 3,
        "expected_chains": ["systems_software_chains_v1"],
        "expected_lanes": {
            "symbolic_logic",
            "inference_closure",
            "fabrication_control",
        },
    },
    "hebrew_greek_textual_reasoning": {
        "adr": "adr-0103",
        "packs": (
            "grc_logos_micro_v1",
            "grc_logos_cognition_v1",
            "he_logos_micro_v1",
            "he_core_cognition_v1",
        ),
        "claimed_operators": ("causal", "contradiction"),
        "min_intent_shapes": 3,
        "expected_chains": ["hebrew_greek_textual_reasoning_chains_v1"],
        "expected_lanes": {
            "inference_closure",
            "fabrication_control",
            "hebrew_fluency",
            "koine_greek_fluency",
        },
    },
}


def _ledger_row(domain_id: str) -> dict:
    report = ledger_report()
    rows = {row["domain"]: row for row in report["domains"]}
    assert domain_id in rows, f"missing ledger row for {domain_id!r}"
    return rows[domain_id]


# ---------------------------------------------------------------------------
# Per-pack 9-predicate validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pack_id,domain_id",
    [
        (pack, domain)
        for domain, spec in _DOMAINS.items()
        for pack in spec["packs"]
    ],
)
def test_pack_passes_all_nine_predicates(
    pack_id: str, domain_id: str
) -> None:
    report = evaluate_domain_contract(pack_id)
    assert report.contract_present is True, (
        f"{pack_id} missing domain contract"
    )
    assert report.contract_valid is True, (
        f"{pack_id} contract parse errors: {report.contract_errors}"
    )
    failing = [p.predicate_id for p in report.predicates if not p.passed]
    assert failing == [], (
        f"{pack_id} failing predicates: {failing}"
    )
    assert report.domain_id == domain_id


# ---------------------------------------------------------------------------
# Per-domain ledger status (invariants per ADR)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("domain_id", list(_DOMAINS.keys()))
class TestLedgerStatus:
    def test_status_meets_reasoning_capable_at_minimum(self, domain_id: str) -> None:
        """Each ratification ADR established reasoning-capable as the
        floor. ADR-0111 later promoted physics to audit-passed (renamed
        from expert-demo by ADR-0113); the load-bearing invariant for
        the ratification ADRs is that reasoning_capable holds, not
        that the status string never moves up."""
        row = _ledger_row(domain_id)
        assert row["status"] in ("reasoning-capable", "audit-passed")

    def test_reasoning_capable_predicate_true(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        assert row["predicates"]["reasoning_capable"] is True

    def test_no_open_gaps(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        assert row["open_gaps"] == []

    def test_provenance_points_at_correct_adr(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        contracts = row["domain_contracts"]
        assert contracts, f"{domain_id} ledger row has no domain_contracts"
        expected_prefix = _DOMAINS[domain_id]["adr"] + ":reviewed:"
        provenances = [c["contract"]["provenance"] for c in contracts]
        assert all(
            p.startswith(expected_prefix) for p in provenances
        ), f"{domain_id}: provenance mismatch, got {provenances}"

    def test_operator_chain_coverage(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        coverage = row["operator_chain_coverage"]
        for op in _DOMAINS[domain_id]["claimed_operators"]:
            assert coverage[op]["ready"] is True, (
                f"{domain_id} op {op!r} not ready: {coverage[op]}"
            )
            assert coverage[op]["chains_present"] >= 8

    def test_intent_shapes_meet_minimum(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        assert row["intent_shapes_present"] >= _DOMAINS[domain_id]["min_intent_shapes"]


# ---------------------------------------------------------------------------
# Per-domain contract field shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("domain_id", list(_DOMAINS.keys()))
class TestContractFields:
    def test_teaching_chains_match(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        for contract_entry in row["domain_contracts"]:
            chains = contract_entry["contract"]["teaching_chains"]
            assert chains == _DOMAINS[domain_id]["expected_chains"], (
                f"{domain_id} ({contract_entry['pack_id']}): unexpected "
                f"teaching_chains {chains}"
            )

    def test_expected_eval_lanes(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        for contract_entry in row["domain_contracts"]:
            lanes = {lane["lane"] for lane in contract_entry["contract"]["eval_lanes"]}
            assert lanes == _DOMAINS[domain_id]["expected_lanes"], (
                f"{domain_id} ({contract_entry['pack_id']}): expected "
                f"lanes {_DOMAINS[domain_id]['expected_lanes']}, got {lanes}"
            )

    def test_all_lanes_cover_three_splits(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        for contract_entry in row["domain_contracts"]:
            for lane in contract_entry["contract"]["eval_lanes"]:
                assert set(lane["splits"]) == {"dev", "public", "holdout"}, (
                    f"{domain_id}: lane {lane['lane']!r} declares "
                    f"{lane['splits']}, expected dev/public/holdout"
                )

    def test_axioms_and_rules_null_at_v1(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        for contract_entry in row["domain_contracts"]:
            contract = contract_entry["contract"]
            assert contract["axioms"] is None
            assert contract["rules"] is None

    def test_primary_reviewer_resolves(self, domain_id: str) -> None:
        row = _ledger_row(domain_id)
        for contract_entry in row["domain_contracts"]:
            assert contract_entry["contract"]["reviewers"] == ["shay-j"]


# ---------------------------------------------------------------------------
# ADR-0102 specific — multi-pack uniformity invariant
# ---------------------------------------------------------------------------


class TestHebrewGreekMultiPackUniformity:
    """ADR-0102 invariant: all four packs declare uniform contract."""

    def test_all_four_packs_carry_contract(self) -> None:
        row = _ledger_row("hebrew_greek_textual_reasoning")
        contract_pack_ids = {c["pack_id"] for c in row["domain_contracts"]}
        assert contract_pack_ids == set(
            _DOMAINS["hebrew_greek_textual_reasoning"]["packs"]
        )

    def test_contracts_identical_modulo_pack_id(self) -> None:
        row = _ledger_row("hebrew_greek_textual_reasoning")
        # Strip pack_id so we can compare the remaining contract fields
        # for cross-pack uniformity.
        canonical = None
        for entry in row["domain_contracts"]:
            contract = dict(entry["contract"])
            if canonical is None:
                canonical = contract
                continue
            assert contract == canonical, (
                f"hebrew/greek pack {entry['pack_id']} drifted from canonical: "
                f"{contract!r} vs {canonical!r}"
            )
