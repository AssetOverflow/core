"""ADR-0097 — Mathematics-Logic Reasoning-Capable Ratification.

Pins the load-bearing invariant: the capability ledger emits a row
for ``domain_id: mathematics_logic`` with ``status: reasoning-capable``,
its provenance points at ADR-0097, and ``expert-demo`` remains gated
until a future ADR attaches the audit-tour-equivalent reports.
"""

from __future__ import annotations

from core.capability import (
    evaluate_domain_contract,
    ledger_report,
)


PACK_ID = "en_mathematics_logic_v1"
DOMAIN_ID = "mathematics_logic"


def _ledger_row(domain_id: str) -> dict:
    report = ledger_report()
    rows = {row["domain"]: row for row in report["domains"]}
    assert domain_id in rows, f"missing ledger row for {domain_id!r}"
    return rows[domain_id]


class TestRatificationPredicates:
    """The nine ADR-0091 predicates all pass for math/logic."""

    def test_all_nine_predicates_pass(self) -> None:
        report = evaluate_domain_contract(PACK_ID)
        assert report.contract_present is True
        assert report.contract_valid is True
        assert report.all_passed is True
        ids = [p.predicate_id for p in report.predicates]
        assert ids == ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9"]
        failing = [p.predicate_id for p in report.predicates if not p.passed]
        assert failing == []

    def test_domain_id_matches(self) -> None:
        report = evaluate_domain_contract(PACK_ID)
        assert report.domain_id == DOMAIN_ID

    def test_provenance_points_at_adr_0097(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        contracts = row["domain_contracts"]
        assert contracts, "math/logic ledger row has no domain_contracts"
        provenances = [c["contract"]["provenance"] for c in contracts]
        assert any(
            p.startswith("adr-0097:reviewed:") for p in provenances
        ), f"expected an adr-0097 provenance, got {provenances}"


class TestLedgerStatus:
    """ADR-0097 invariant: ``mathematics_logic_reasoning_capable_ledger_row``."""

    def test_status_meets_reasoning_capable_at_minimum(self) -> None:
        """ADR-0097 ratified math at reasoning-capable. ADR-0110 later
        promoted it to audit-passed (renamed from expert-demo by
        ADR-0113). The load-bearing invariant for ADR-0097 is that
        reasoning_capable holds; the status string moves with later
        promotions."""
        row = _ledger_row(DOMAIN_ID)
        assert row["status"] in ("reasoning-capable", "audit-passed")
        assert row["predicates"]["reasoning_capable"] is True

    def test_reasoning_capable_predicate_holds(self) -> None:
        """ADR-0097's load-bearing invariant: reasoning_capable=True."""
        row = _ledger_row(DOMAIN_ID)
        assert row["predicates"]["reasoning_capable"] is True

    def test_no_open_gaps(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        assert row["open_gaps"] == []

    def test_intent_shapes_meet_minimum(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        assert row["intent_shapes_present"] >= 3
        assert row["intent_shapes_required"] == 3

    def test_operator_chain_coverage_meets_minimum(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        coverage = row["operator_chain_coverage"]
        for op_family in ("transitive", "proof_chain", "contradiction"):
            assert coverage[op_family]["ready"] is True
            assert coverage[op_family]["chains_present"] >= 8


class TestContractFieldShape:
    """Ratified contract carries the exact fields ADR-0097 declares."""

    def test_contract_fields_present(self) -> None:
        report = evaluate_domain_contract(PACK_ID)
        assert report.contract_present is True

    def test_three_eval_lanes_declared(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        contract = row["domain_contracts"][0]["contract"]
        lane_names = {lane["lane"] for lane in contract["eval_lanes"]}
        assert lane_names == {
            "elementary_mathematics_ood",
            "inference_closure",
            "fabrication_control",
        }

    def test_eval_lanes_have_all_three_splits(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        contract = row["domain_contracts"][0]["contract"]
        for lane in contract["eval_lanes"]:
            assert set(lane["splits"]) == {"dev", "public", "holdout"}

    def test_teaching_chains_corpus(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        contract = row["domain_contracts"][0]["contract"]
        assert contract["teaching_chains"] == ["mathematics_logic_chains_v1"]

    def test_axioms_and_rules_null_at_v1(self) -> None:
        """ADR-0097 §Manifest additions: axioms/rules stay null at v1."""
        row = _ledger_row(DOMAIN_ID)
        contract = row["domain_contracts"][0]["contract"]
        assert contract["axioms"] is None
        assert contract["rules"] is None

    def test_primary_reviewer_resolves(self) -> None:
        row = _ledger_row(DOMAIN_ID)
        contract = row["domain_contracts"][0]["contract"]
        assert contract["reviewers"] == ["shay-j"]
