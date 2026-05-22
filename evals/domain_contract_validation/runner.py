"""Runner for evals/domain_contract_validation/ (ADR-0093).

Builds synthetic pack fixtures in a temp directory, runs the nine
ADR-0091 predicates via
:func:`core.capability.domain_contract_predicates.evaluate_domain_contract`,
and asserts each case's actual outcome matches its declared expectation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from core.capability.domain_contract_predicates import (
    DomainContractPredicateReport,
    evaluate_domain_contract,
)
from core.capability.reviewers import Reviewer, ReviewerRegistry, SCHEMA_VERSION


PACK_ID = "synthetic_math_pack_v1"


def _registry() -> ReviewerRegistry:
    return ReviewerRegistry(
        schema_version=SCHEMA_VERSION,
        reviewers=(
            Reviewer(
                reviewer_id="shay-j",
                display_name="Joshua Shay",
                role="primary",
                domains=("*",),
                review_scope=("pack", "proposal", "chain", "eval"),
                provenance="adr-0092:lane:test",
            ),
            Reviewer(
                reviewer_id="physics-only",
                display_name="Physics Reviewer",
                role="domain",
                domains=("physics",),
                review_scope=("pack",),
                provenance="adr-0092:lane:test",
            ),
        ),
    )


def _full_inventory() -> dict[str, Any]:
    return {
        "by_domain_operator_family": {
            "mathematics_logic": {
                "transitive": 10,
                "proof_chain": 9,
                "contradiction": 8,
            },
        },
        "by_domain_intent_shape": {
            "mathematics_logic": {
                "cause": 4,
                "verification": 3,
                "comparison": 5,
            },
        },
    }


def _sparse_inventory() -> dict[str, Any]:
    return {
        "by_domain_operator_family": {
            "mathematics_logic": {
                "transitive": 2,
                "proof_chain": 9,
                "contradiction": 8,
            },
        },
        "by_domain_intent_shape": {
            "mathematics_logic": {
                "cause": 4,
                "verification": 3,
                "comparison": 5,
            },
        },
    }


def _thin_intent_inventory() -> dict[str, Any]:
    return {
        "by_domain_operator_family": {
            "mathematics_logic": {
                "transitive": 10,
                "proof_chain": 9,
                "contradiction": 8,
            },
        },
        "by_domain_intent_shape": {
            "mathematics_logic": {"cause": 4, "verification": 0, "comparison": 0},
        },
    }


def _write_pack(
    data_root: Path,
    *,
    domain_id: str = "mathematics_logic",
    teaching_chains: tuple[str, ...] = ("mathematics_logic_chains_v1",),
    reviewers: tuple[str, ...] = ("shay-j",),
    eval_lanes: tuple[dict[str, Any], ...] = (
        {
            "lane": "elementary_mathematics_ood",
            "version": "v1",
            "splits": ["dev", "public", "holdout"],
        },
    ),
    known_gaps: tuple[str, ...] = (),
) -> None:
    pack_dir = data_root / PACK_ID
    pack_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "pack_id": PACK_ID,
        "name": "synthetic pack",
        "domain_contract_version": 1,
        "domain_id": domain_id,
        "axioms": None,
        "rules": None,
        "teaching_chains": list(teaching_chains),
        "eval_lanes": [dict(lane) for lane in eval_lanes],
        "reviewers": list(reviewers),
        "known_gaps": list(known_gaps),
        "provenance": "lane:fixture:v1",
    }
    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )


def _evaluate(
    data_root: Path,
    *,
    inventory: dict[str, Any] | None = None,
    registry: ReviewerRegistry | None = None,
) -> DomainContractPredicateReport:
    return evaluate_domain_contract(
        PACK_ID,
        data_root=data_root,
        chain_inventory=inventory or _full_inventory(),
        reviewer_registry=registry or _registry(),
    )


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


def _case_positive(tmp_root: Path) -> dict[str, Any]:
    """Synthetic fixtures cannot satisfy P1/P2 (require a compiled pack).

    The lane asserts the *semantic* predicates P3-P9 pass on a
    well-formed contract; P1/P2 are exercised against in-tree packs
    elsewhere (and by tests/test_domain_contract_predicates.py).
    """
    data_root = tmp_root / "positive"
    _write_pack(data_root)
    report = _evaluate(data_root)
    semantic = [p for p in report.predicates if p.predicate_id not in {"P1", "P2"}]
    failing = [p.predicate_id for p in semantic if not p.passed]
    if failing:
        return _fail(
            "positive_all_predicates_pass",
            f"P3-P9 expected pass; failing={failing}",
        )
    return _pass(
        "positive_all_predicates_pass",
        {
            "semantic_predicates_passed": len(semantic),
            "p1_p2_under_synthetic_fixture_excluded": True,
        },
    )


def _case_p3(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p3"
    _write_pack(data_root, domain_id="alien_domain")
    report = _evaluate(data_root)
    if report.contract_valid:
        return _fail("p3_unknown_domain", "contract should be parse-rejected")
    if not any("domain_id:unknown" in e for e in report.contract_errors):
        return _fail("p3_unknown_domain", f"missing domain_id:unknown error; errors={report.contract_errors}")
    return _pass("p3_unknown_domain", {"contract_errors": list(report.contract_errors)})


def _case_p4(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p4"
    _write_pack(data_root, teaching_chains=("ghost_chains_v999",))
    report = _evaluate(data_root)
    p4 = _find(report, "P4")
    if p4.passed:
        return _fail("p4_unregistered_chain", "P4 should fail on unregistered corpus")
    return _pass("p4_unregistered_chain", {"notes": p4.notes})


def _case_p5(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p5"
    _write_pack(data_root)
    report = _evaluate(data_root, inventory=_sparse_inventory())
    p5 = _find(report, "P5")
    if p5.passed:
        return _fail("p5_chain_shortfall", "P5 should fail with transitive=2")
    return _pass("p5_chain_shortfall", {"notes": p5.notes})


def _case_p6(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p6"
    _write_pack(data_root)
    report = _evaluate(data_root, inventory=_thin_intent_inventory())
    p6 = _find(report, "P6")
    if p6.passed:
        return _fail("p6_too_few_intents", "P6 should fail with 1 intent shape")
    return _pass("p6_too_few_intents", {"notes": p6.notes})


def _case_p7(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p7"
    _write_pack(
        data_root,
        eval_lanes=(
            {
                "lane": "elementary_mathematics_ood",
                "version": "v1",
                "splits": ["dev", "public"],
            },
        ),
    )
    report = _evaluate(data_root)
    p7 = _find(report, "P7")
    if p7.passed:
        return _fail("p7_incomplete_splits", "P7 should fail without holdout")
    return _pass("p7_incomplete_splits", {"notes": p7.notes})


def _case_p8(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p8"
    _write_pack(data_root, reviewers=("ghost-reviewer",))
    report = _evaluate(data_root)
    p8 = _find(report, "P8")
    if p8.passed:
        return _fail("p8_unknown_reviewer", "P8 should fail on unknown reviewer")
    return _pass("p8_unknown_reviewer", {"notes": p8.notes})


def _case_p9(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "p9"
    _write_pack(data_root, known_gaps=("gap:absolutely_imaginary_blocker",))
    report = _evaluate(data_root)
    p9 = _find(report, "P9")
    if p9.passed:
        return _fail("p9_open_gap", "P9 should fail on unknown gap")
    return _pass("p9_open_gap", {"notes": p9.notes})


def _case_determinism(tmp_root: Path) -> dict[str, Any]:
    data_root = tmp_root / "determinism"
    _write_pack(data_root)
    a = _evaluate(data_root).as_dict()
    b = _evaluate(data_root).as_dict()
    if a != b:
        return _fail("determinism", "two evaluations produced different reports")
    return _pass("determinism", {"all_passed": a["all_passed"]})


CASES: tuple[tuple[str, Callable[[Path], dict[str, Any]]], ...] = (
    ("positive_all_predicates_pass", _case_positive),
    ("p3_unknown_domain", _case_p3),
    ("p4_unregistered_chain", _case_p4),
    ("p5_chain_shortfall", _case_p5),
    ("p6_too_few_intents", _case_p6),
    ("p7_incomplete_splits", _case_p7),
    ("p8_unknown_reviewer", _case_p8),
    ("p9_open_gap", _case_p9),
    ("determinism", _case_determinism),
)


def _find(report: DomainContractPredicateReport, predicate_id: str) -> Any:
    for p in report.predicates:
        if p.predicate_id == predicate_id:
            return p
    raise RuntimeError(f"predicate {predicate_id} missing from report")


def _pass(case_id: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"case_id": case_id, "passed": True, "details": details, "divergence": None}


def _fail(case_id: str, divergence: str) -> dict[str, Any]:
    return {"case_id": case_id, "passed": False, "details": {}, "divergence": divergence}


def run() -> dict[str, Any]:
    tmp_root = Path(tempfile.mkdtemp(prefix="domain_contract_lane_"))
    try:
        case_results = [fn(tmp_root) for _, fn in CASES]
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    return {
        "lane": "domain_contract_validation",
        "lane_version": "v1",
        "split": "dev",
        "adr": "ADR-0093",
        "invariant": "domain_contract_v1_predicates_enforced",
        "total_cases": len(case_results),
        "passed_cases": sum(1 for r in case_results if r["passed"]),
        "failed_cases": sum(1 for r in case_results if not r["passed"]),
        "all_passed": all(r["passed"] for r in case_results),
        "cases": case_results,
    }


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="domain_contract_validation lane runner")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    summary = run()
    lane_dir = Path(__file__).resolve().parent
    report_path = args.report or (lane_dir / "results" / "v1_dev.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = _canonical_json(summary)
    report_path.write_bytes(payload_bytes)

    print(f"report: {report_path}")
    print(f"sha256: {hashlib.sha256(payload_bytes).hexdigest()}")
    print(f"passed: {summary['passed_cases']}/{summary['total_cases']}")

    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
