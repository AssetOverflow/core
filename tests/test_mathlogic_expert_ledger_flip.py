"""ADR-0120 math-expert ledger-flip tests.

Pins:
  - reviewers.yaml ``math_expert_claims:`` top-level key is allow-listed
    (regression test for the bug PR #194 introduced)
  - ``_EXPERT_DOMAIN_STATUSES`` includes ``"expert"``
  - per-domain expert composer wiring (``_EXPERT_COMPOSERS``)
  - claim_digest is filesystem-independent (path-stability fix)
  - mathematics_logic row reports ``status: expert`` + ``predicates.expert: True``
    given the on-disk evidence + signed reviewer entry
  - other domains stay at their existing tier (composer absent → expert=False)
"""

from __future__ import annotations

import json
import yaml
from pathlib import Path

import pytest

from core.capability.composite_math_gate import _rel as _gate_rel, evaluate_composite_math_gate
from core.capability.expert_promotion_math import (
    DOMAIN_ID,
    EXPERT_CLAIMS_KEY,
    _rel as _composer_rel,
    evaluate_math_expert_promotion,
)
from core.capability.reporting import _EXPERT_COMPOSERS, _EXPERT_DOMAIN_STATUSES, ledger_report
from core.capability.reviewers import ALLOWED_TOP_LEVEL_KEYS, load_reviewer_registry


_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Allow-list regression (bug introduced in PR #194, fixed here)
# ---------------------------------------------------------------------------


def test_allowed_top_level_keys_includes_math_expert_claims() -> None:
    """PR #194 added the ``math_expert_claims:`` section to
    docs/reviewers.yaml but didn't extend the loader's allow-list,
    silently breaking the audit_passed predicate for ALL 3 prior
    domains (the loader rejected the whole file)."""
    assert "math_expert_claims" in ALLOWED_TOP_LEVEL_KEYS


def test_reviewers_yaml_loads_after_fix() -> None:
    """The real file should parse without raising — proving the
    allow-list regression is fixed end-to-end."""
    registry = load_reviewer_registry(_REPO_ROOT / "docs" / "reviewers.yaml")
    # Existing 3 audit-passed entries must still resolve.
    assert registry.expert_demo_claim_for("mathematics_logic") is not None
    assert registry.expert_demo_claim_for("physics") is not None
    assert registry.expert_demo_claim_for("systems_software") is not None


# ---------------------------------------------------------------------------
# Expert tier wiring
# ---------------------------------------------------------------------------


def test_expert_status_in_status_order() -> None:
    assert "expert" in _EXPERT_DOMAIN_STATUSES
    # Must come after audit-passed (strict super-tier).
    assert _EXPERT_DOMAIN_STATUSES.index("expert") > _EXPERT_DOMAIN_STATUSES.index("audit-passed")


def test_mathematics_logic_composer_wired() -> None:
    assert _EXPERT_COMPOSERS["mathematics_logic"] == "core.capability.expert_promotion_math"


# ---------------------------------------------------------------------------
# Path-stability fix (digest filesystem-independence)
# ---------------------------------------------------------------------------


def test_rel_returns_repo_relative_posix() -> None:
    """``_rel`` must return repo-relative POSIX, not absolute path,
    so the digest is stable across operator filesystems."""
    p = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
    rel = _composer_rel(p)
    assert not rel.startswith("/")  # not absolute
    assert rel == "evals/math_bounded_grammar/v1/cases.jsonl"
    # composite_math_gate's _rel must agree
    assert _gate_rel(p) == rel


def test_rel_falls_back_to_absolute_outside_repo(tmp_path: Path) -> None:
    """Paths outside the repo root should fall back to absolute
    POSIX (rather than raise)."""
    outside = tmp_path / "elsewhere.json"
    rel = _composer_rel(outside)
    assert rel == outside.as_posix()


def test_composer_digest_uses_relative_paths() -> None:
    """Sanity: the digest's input bundle should contain repo-relative
    paths (not absolute), so it's filesystem-independent."""
    v = evaluate_math_expert_promotion()
    for o in v.obligations:
        assert not o.evidence_pointer.startswith("/"), (
            f"obligation {o.obligation_id} has absolute path: {o.evidence_pointer}"
        )


def test_composite_gate_digest_uses_relative_paths() -> None:
    v = evaluate_composite_math_gate()
    for b in v.benchmarks:
        assert not b.report_path.startswith("/"), (
            f"benchmark {b.benchmark_id} has absolute report_path: {b.report_path}"
        )


# ---------------------------------------------------------------------------
# Ledger flip — mathematics_logic must reach "expert" on current main
# ---------------------------------------------------------------------------


def _math_row(report: dict) -> dict:
    for row in report["domains"]:
        if row["domain"] == "mathematics_logic":
            return row
    raise AssertionError("mathematics_logic row missing from ledger")


def test_mathlogic_status_is_expert_with_signed_evidence() -> None:
    """The load-bearing snapshot. Given the signed entry in
    docs/reviewers.yaml AND every obligation auditor passing AND the
    composite gate passing, the ledger reports
    ``mathematics_logic.status == "expert"``."""
    report = ledger_report()
    row = _math_row(report)
    assert row["status"] == "expert", (
        f"expected status=expert; got {row['status']!r}; "
        f"audit_passed_reason={row.get('audit_passed_reason')}; "
        f"expert_reason={row.get('expert_reason')}"
    )
    assert row["predicates"]["expert"] is True
    assert row["predicates"]["audit_passed"] is True


def test_mathlogic_row_carries_expert_reason() -> None:
    report = ledger_report()
    row = _math_row(report)
    assert "expert_reason" in row
    assert "admitted" in row["expert_reason"].lower()


def test_other_domains_have_expert_false_no_composer_wired() -> None:
    """Domains without an entry in _EXPERT_COMPOSERS keep expert=False
    even when audit_passed=True. Currently only mathematics_logic
    is wired."""
    report = ledger_report()
    for row in report["domains"]:
        if row["domain"] == "mathematics_logic":
            continue
        # Other domains' expert predicate must be False.
        assert row["predicates"]["expert"] is False, (
            f"{row['domain']} unexpectedly reports expert=True"
        )


# ---------------------------------------------------------------------------
# Failure mode: signature missing → status stays at audit-passed
# ---------------------------------------------------------------------------


def test_composer_refuses_without_signature(tmp_path: Path) -> None:
    """If the reviewers file omits the math_expert_claims entry,
    promote_admitted stays False with the expected awaiting-signature
    message."""
    fake = tmp_path / "reviewers.yaml"
    fake.write_text(yaml.safe_dump({
        "schema_version": 1,
        "reviewers": [
            {
                "reviewer_id": "shay-j",
                "display_name": "test",
                "role": "primary",
                "domains": ["*"],
                "review_scope": ["pack", "proposal", "chain", "eval"],
                "provenance": "test",
            }
        ],
        EXPERT_CLAIMS_KEY: [],
    }), encoding="utf-8")
    v = evaluate_math_expert_promotion(reviewers_path=fake)
    assert v.technical_pass is True  # evidence still passes
    assert v.promote_admitted is False
    assert "awaiting reviewer signature" in v.refusal_reason
