"""ADR-0107 — `mathematics_logic` expert-demo deferral invariant.

Pins `adr_0107_no_silent_promotion`: the ADR-0107 decision is *defer*,
not promote. If a later change silently flips the math row to
`expert_demo=true` without ADR-0109 + ADR-0110 landing first, this gate
must fail.

This test reads the *live* ledger, not a fixture. A green test asserts
that the contract is behaving as ADR-0107 records: math sits at
`reasoning-capable`, no `expert_demo_claims` entry for math is present,
and the row carries a named refusal reason.
"""

from __future__ import annotations

from core.capability.reporting import ledger_report
from core.capability.reviewers import load_reviewer_registry
from core.capability.sources import LEDGER_SOURCES
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _math_row() -> dict:
    report = ledger_report()
    for row in report["domains"]:
        if row["domain"] == "mathematics_logic":
            return row
    raise AssertionError("mathematics_logic row missing from ledger_report()")


class TestAdr0107NoSilentPromotion:
    def test_math_row_is_reasoning_capable_not_expert_demo(self) -> None:
        row = _math_row()
        assert row["predicates"]["reasoning_capable"] is True
        assert row["predicates"]["expert_demo"] is False
        assert row["status"] == "reasoning-capable"

    def test_math_has_no_expert_demo_claim(self) -> None:
        registry_path = _REPO_ROOT / LEDGER_SOURCES.reviewers
        registry = load_reviewer_registry(registry_path)
        assert registry.expert_demo_claim_for("mathematics_logic") is None

    def test_refusal_reason_is_named(self) -> None:
        row = _math_row()
        reason = row.get("expert_demo_reason", "")
        assert reason, "expert_demo_reason must be populated"
        assert reason != "all expert-demo predicates satisfied"
