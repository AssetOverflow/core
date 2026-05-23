"""ADR-0114a Obligation #2 — OOD surface variation ratio auditor tests.

Pins the invariants:
  - Dataset integrity: ≥30 cases; every case has public_sibling_case_id
    resolving to a real B3 case; every case is in-grammar.
  - Entity-name substitution: every OOD case has a different entity name
    than its public sibling.
  - Unit-noun substitution: every OOD case with a substitutable unit has
    a different unit than its public sibling.
  - Auditor: ratio computed correctly; gate at 0.95 pinned; wrong == 0
    is a separate gate.
  - Refusal on missing public report or missing OOD report.
  - Determinism: report byte-equal across runs.
  - Snapshot: current main satisfies obligation #2 on the shipped OOD set.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.ood_ratio import (
    OOD_RATIO_GATE,
    emit_ood_ratio_report,
    evaluate_ood_ratio,
)
from evals.obligation_2_ood_ratio.v1.runner import build_report, load_cases

_REPO_ROOT = Path(__file__).resolve().parent.parent
_B3_CASES = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "cases.jsonl"
_B3_REPORT = _REPO_ROOT / "evals" / "math_bounded_grammar" / "v1" / "report.json"
_OOD_CASES = _REPO_ROOT / "evals" / "obligation_2_ood_ratio" / "v1" / "cases.jsonl"

# Entity-name substitution pool shipped with this ADR.
_ENTITY_POOL = {"Maya", "Liam", "Noah", "Diana", "Felix", "Priya", "Omar", "Rosa", "Jun", "Kai"}

# Unit-noun substitution pool (count nouns substituted in OOD cases).
_UNIT_SUBSTITUTION_POOL = {"apples", "candies", "birds", "sheets", "books"}


# ---------------------------------------------------------------------------
# Dataset integrity
# ---------------------------------------------------------------------------


def test_ood_case_count_at_least_30() -> None:
    cases = load_cases(_OOD_CASES)
    assert len(cases) >= 30, f"OOD set has {len(cases)} cases, need ≥ 30"


def test_every_ood_case_has_public_sibling_field() -> None:
    cases = load_cases(_OOD_CASES)
    for case in cases:
        assert "public_sibling_case_id" in case, (
            f"{case['case_id']}: missing public_sibling_case_id"
        )
        assert isinstance(case["public_sibling_case_id"], str) and case["public_sibling_case_id"], (
            f"{case['case_id']}: public_sibling_case_id is empty"
        )


def test_every_public_sibling_resolves_to_real_b3_case() -> None:
    ood_cases = load_cases(_OOD_CASES)
    b3_cases = {
        json.loads(l)["case_id"]
        for l in _B3_CASES.read_text(encoding="utf-8").splitlines()
        if l.strip()
    }
    for case in ood_cases:
        sibling = case["public_sibling_case_id"]
        assert sibling in b3_cases, (
            f"{case['case_id']}: public_sibling_case_id {sibling!r} not in B3 public cases"
        )


def test_every_ood_case_is_in_grammar() -> None:
    from generate.math_parser import ParseError, parse_problem

    cases = load_cases(_OOD_CASES)
    failed: list[str] = []
    for case in cases:
        try:
            parse_problem(case["problem"])
        except ParseError as exc:
            failed.append(f"{case['case_id']}: {exc}")
    assert not failed, "OOD cases failed grammar check:\n" + "\n".join(failed)


# ---------------------------------------------------------------------------
# Entity-name substitution
# ---------------------------------------------------------------------------


def _extract_entities_from_problem(problem: str) -> set[str]:
    """Heuristic: title-cased words that are not common English words."""
    _common = {"There", "How", "Each", "An", "Sam", "Tom", "The"}
    words = problem.split()
    return {
        w.rstrip(".,?") for w in words
        if w[0].isupper() and w.rstrip(".,?") not in _common and not w[0].isdigit()
    }


def test_every_ood_case_has_different_entity_than_sibling() -> None:
    ood_cases = load_cases(_OOD_CASES)
    b3_by_id: dict[str, dict] = {}
    for line in _B3_CASES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            b3_by_id[c["case_id"]] = c

    failures: list[str] = []
    for case in ood_cases:
        sibling = b3_by_id[case["public_sibling_case_id"]]
        ood_entities = _extract_entities_from_problem(case["problem"])
        pub_entities = _extract_entities_from_problem(sibling["problem"])
        shape = case.get("shape_category", "")

        # there_are_count shape: the unit noun acts as implicit entity — no named
        # entity is present, so the entity-pool check does not apply.  The unit-noun
        # substitution test (a separate test) covers surface diversity for that shape.
        if shape == "there_are_count":
            continue

        ood_from_pool = ood_entities & _ENTITY_POOL
        pub_in_pool = pub_entities & _ENTITY_POOL
        if not ood_from_pool:
            failures.append(
                f"{case['case_id']}: no OOD entity from pool {_ENTITY_POOL}; "
                f"found {ood_entities}"
            )
        if pub_in_pool:
            failures.append(
                f"{case['case_id']}: public sibling already uses pool entity {pub_in_pool}; "
                f"public entities={pub_entities}"
            )

    assert not failures, "Entity substitution violations:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# Unit-noun substitution
# ---------------------------------------------------------------------------


def test_ood_cases_with_substitutable_unit_differ_from_sibling() -> None:
    ood_cases = load_cases(_OOD_CASES)
    b3_by_id: dict[str, dict] = {}
    for line in _B3_CASES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            b3_by_id[c["case_id"]] = c

    failures: list[str] = []
    for case in ood_cases:
        sibling = b3_by_id[case["public_sibling_case_id"]]
        pub_unit = sibling.get("expected_unit") or ""
        ood_unit = case.get("expected_unit") or ""
        if pub_unit in _UNIT_SUBSTITUTION_POOL:
            if ood_unit == pub_unit:
                failures.append(
                    f"{case['case_id']}: public unit {pub_unit!r} is in substitution pool "
                    f"but OOD unit is unchanged ({ood_unit!r})"
                )

    assert not failures, "Unit substitution violations:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# Auditor ratio computation
# ---------------------------------------------------------------------------


def _make_public_report(total: int, correct: int, tmp_path: Path) -> Path:
    p = tmp_path / "public_report.json"
    p.write_text(json.dumps({
        "schema_version": 1,
        "metrics": {"cases_total": total, "correct": correct, "wrong": 0, "refused": 0}
    }), encoding="utf-8")
    return p


def _make_ood_report(total: int, correct: int, wrong: int, tmp_path: Path) -> Path:
    p = tmp_path / "ood_report.json"
    p.write_text(json.dumps({
        "schema_version": 1,
        "metrics": {"cases_total": total, "correct": correct, "wrong": wrong, "refused": 0}
    }), encoding="utf-8")
    return p


def test_auditor_ratio_computation_exact(tmp_path: Path) -> None:
    pub = _make_public_report(50, 50, tmp_path)
    ood = _make_ood_report(35, 35, 0, tmp_path)
    report = evaluate_ood_ratio(public_report_path=pub, ood_report_path=ood)
    assert report.public_accuracy == 1.0
    assert report.ood_accuracy == 1.0
    assert report.ood_ratio == 1.0
    assert report.obligation_2_ratio_satisfied is True
    assert report.obligation_2_wrong_zero is True
    assert report.obligation_2_passed is True


def test_auditor_ratio_gate_pinned_at_0_95(tmp_path: Path) -> None:
    # ratio exactly at gate passes
    pub = _make_public_report(100, 100, tmp_path)
    ood = _make_ood_report(100, 95, 0, tmp_path)
    report = evaluate_ood_ratio(public_report_path=pub, ood_report_path=ood)
    assert report.ood_ratio == pytest.approx(0.95)
    assert report.obligation_2_ratio_satisfied is True

    # ratio just below gate fails
    ood_fail_path = tmp_path / "ood_fail.json"
    ood_fail_path.write_text(json.dumps({
        "schema_version": 1,
        "metrics": {"cases_total": 100, "correct": 94, "wrong": 0, "refused": 0}
    }), encoding="utf-8")
    report_fail = evaluate_ood_ratio(public_report_path=pub, ood_report_path=ood_fail_path)
    assert report_fail.ood_ratio == pytest.approx(0.94)
    assert report_fail.obligation_2_ratio_satisfied is False
    assert report_fail.obligation_2_passed is False


def test_gate_constant_is_0_95() -> None:
    """Gate threshold is pinned; changing requires a new ADR."""
    assert OOD_RATIO_GATE == 0.95


def test_wrong_zero_gate_is_separate_from_ratio_gate(tmp_path: Path) -> None:
    pub = _make_public_report(50, 50, tmp_path)
    ood_wrong_path = tmp_path / "ood_wrong.json"
    ood_wrong_path.write_text(json.dumps({
        "schema_version": 1,
        "metrics": {"cases_total": 35, "correct": 35, "wrong": 1, "refused": 0}
    }), encoding="utf-8")
    report = evaluate_ood_ratio(public_report_path=pub, ood_report_path=ood_wrong_path)
    # ratio would pass (35+1=36 correct-ish? actually correct=35 so ratio still fine)
    assert report.obligation_2_wrong_zero is False
    assert report.obligation_2_passed is False


# ---------------------------------------------------------------------------
# Refusal on missing inputs
# ---------------------------------------------------------------------------


def test_auditor_refuses_on_missing_public_report(tmp_path: Path) -> None:
    ood = _make_ood_report(35, 35, 0, tmp_path)
    report = evaluate_ood_ratio(
        public_report_path=tmp_path / "nonexistent_public.json",
        ood_report_path=ood,
    )
    assert report.obligation_2_passed is False
    assert "not found" in report.refusal_reason.lower()


def test_auditor_refuses_on_missing_ood_report(tmp_path: Path) -> None:
    pub = _make_public_report(50, 50, tmp_path)
    report = evaluate_ood_ratio(
        public_report_path=pub,
        ood_report_path=tmp_path / "nonexistent_ood.json",
    )
    assert report.obligation_2_passed is False
    assert "not found" in report.refusal_reason.lower()


def test_auditor_refuses_when_public_accuracy_is_zero(tmp_path: Path) -> None:
    pub = _make_public_report(50, 0, tmp_path)
    ood = _make_ood_report(35, 35, 0, tmp_path)
    report = evaluate_ood_ratio(public_report_path=pub, ood_report_path=ood)
    assert report.obligation_2_passed is False
    assert "baseline" in report.refusal_reason.lower()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_auditor_is_deterministic() -> None:
    # Run twice against the live reports
    cases = load_cases(_OOD_CASES)
    ood_data = build_report(cases)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        json.dump(ood_data, f)
        tmp_ood = Path(f.name)
    try:
        r1 = evaluate_ood_ratio(public_report_path=_B3_REPORT, ood_report_path=tmp_ood)
        r2 = evaluate_ood_ratio(public_report_path=_B3_REPORT, ood_report_path=tmp_ood)
        assert json.dumps(r1.as_dict(), sort_keys=True) == json.dumps(r2.as_dict(), sort_keys=True)
    finally:
        os.unlink(tmp_ood)


def test_artifact_emission_byte_equal(tmp_path: Path) -> None:
    cases = load_cases(_OOD_CASES)
    ood_data = build_report(cases)
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        json.dump(ood_data, f)
        tmp_ood = Path(f.name)
    try:
        report = evaluate_ood_ratio(public_report_path=_B3_REPORT, ood_report_path=tmp_ood)
        out1 = tmp_path / "r1.json"
        out2 = tmp_path / "r2.json"
        emit_ood_ratio_report(report, out1)
        emit_ood_ratio_report(report, out2)
        assert out1.read_bytes() == out2.read_bytes()
    finally:
        os.unlink(tmp_ood)


# ---------------------------------------------------------------------------
# Snapshot: current main satisfies obligation #2
# ---------------------------------------------------------------------------


def test_snapshot_obligation_2_satisfied_on_shipped_ood_set() -> None:
    """Load-bearing snapshot: obligation #2 must be satisfied on the OOD
    cases shipped with this PR against the B3 public report.json.
    If this fails, either the OOD cases broke the pipeline or B3
    degraded below the baseline."""
    cases = load_cases(_OOD_CASES)
    ood_runner_report = build_report(cases)

    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        json.dump(ood_runner_report, f)
        tmp_ood = Path(f.name)
    try:
        report = evaluate_ood_ratio(public_report_path=_B3_REPORT, ood_report_path=tmp_ood)
        assert report.obligation_2_passed is True, (
            f"obligation #2 failed: {report.refusal_reason}\n"
            f"ood_ratio={report.ood_ratio:.4f} (gate={OOD_RATIO_GATE})\n"
            f"ood_wrong={report.ood_cases_wrong}"
        )
        assert report.obligation_2_wrong_zero is True
        assert report.ood_ratio >= OOD_RATIO_GATE
    finally:
        os.unlink(tmp_ood)
