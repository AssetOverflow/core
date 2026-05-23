"""ADR-0114a Obligation #8 — adversarial generation auditor tests.

Pins the invariants:
  - thresholds pinned (>= 30 cases, >= 8 families)
  - every documented family has at least one case (closed taxonomy)
  - wrong == 0 invariant on the committed adversarial set
  - missing cases file refuses cleanly
  - report is deterministic + artifact byte-equal
  - snapshot: current main satisfies obligation #8
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.adversarial import (
    DEFAULT_CASES_PATH,
    MIN_FAMILIES,
    MIN_TOTAL_CASES,
    emit_adversarial_report,
    evaluate_adversarial,
)


# Closed family taxonomy — adding a new family requires an ADR amendment.
_KNOWN_FAMILIES = frozenset({
    "paraphrase",
    "unrecognized_unit",
    "conditional",
    "pronoun_coref",
    "hedged_quantity",
    "ordinal_confusion",
    "implicit_subject",
    "self_reference",
    "distractor_noise",
})


# ---------------------------------------------------------------------------
# Threshold + taxonomy
# ---------------------------------------------------------------------------


def test_thresholds_pinned() -> None:
    """ADR-0120 pins ≥30 cases × ≥8 families. Changing requires a new ADR."""
    assert MIN_TOTAL_CASES == 30
    assert MIN_FAMILIES == 8


def test_committed_dataset_meets_thresholds() -> None:
    cases = [
        json.loads(line)
        for line in DEFAULT_CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(cases) >= MIN_TOTAL_CASES
    families = {c["family"] for c in cases}
    assert len(families) >= MIN_FAMILIES


def test_committed_dataset_uses_only_known_families() -> None:
    cases = [
        json.loads(line)
        for line in DEFAULT_CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    families = {c["family"] for c in cases}
    extra = families - _KNOWN_FAMILIES
    assert not extra, f"unknown families — extend taxonomy in ADR before adding: {extra}"


def test_every_known_family_has_at_least_one_case() -> None:
    cases = [
        json.loads(line)
        for line in DEFAULT_CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    families = {c["family"] for c in cases}
    missing = _KNOWN_FAMILIES - families
    assert not missing, f"missing case coverage for families: {missing}"


def test_every_case_has_required_fields() -> None:
    cases = [
        json.loads(line)
        for line in DEFAULT_CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for c in cases:
        assert "case_id" in c
        assert "family" in c
        assert "problem" in c
        assert "note" in c
        assert isinstance(c["problem"], str) and c["problem"].strip()


# ---------------------------------------------------------------------------
# Snapshot: obligation #8 passes on current main
# ---------------------------------------------------------------------------


def test_obligation_8_passes_on_current_main() -> None:
    """The load-bearing snapshot. If this fails, either a parser change
    started producing wrong answers on adversarial input, or the case
    set was reduced below thresholds. Either way, investigate before
    relaxing."""
    r = evaluate_adversarial()
    assert r.obligation_8_passed is True, (
        f"obligation #8 failed: {r.refusal_reason}\n"
        f"families: {[(f.family, f.cases_wrong) for f in r.families if f.cases_wrong > 0]}"
    )
    assert r.wrong_count_is_zero is True
    assert r.threshold_cases_met is True
    assert r.threshold_families_met is True


def test_wrong_count_is_zero_per_family() -> None:
    r = evaluate_adversarial()
    for f in r.families:
        assert f.cases_wrong == 0, (
            f"family {f.family!r} produced {f.cases_wrong} wrong answer(s)"
        )


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_refuses_on_missing_cases_file(tmp_path: Path) -> None:
    r = evaluate_adversarial(cases_path=tmp_path / "missing.jsonl")
    assert r.obligation_8_passed is False
    assert "not found" in r.refusal_reason.lower()


def test_refuses_when_cases_below_threshold(tmp_path: Path) -> None:
    """Synthetic fixture with only 5 cases — must refuse on count
    threshold even if all 5 pass with wrong=0."""
    cases_file = tmp_path / "small.jsonl"
    rows = [
        json.dumps({
            "case_id": f"small-{i}",
            "family": f"fam_{i}",
            "problem": "Sam has 5 apples. How many apples does Sam have?",
            "note": "synthetic",
        })
        for i in range(5)
    ]
    cases_file.write_text("\n".join(rows) + "\n", encoding="utf-8")
    r = evaluate_adversarial(cases_path=cases_file)
    assert r.obligation_8_passed is False
    assert "cases_total=5" in r.refusal_reason


# ---------------------------------------------------------------------------
# Determinism + artifact byte-equality
# ---------------------------------------------------------------------------


def test_report_is_deterministic() -> None:
    r1 = evaluate_adversarial()
    r2 = evaluate_adversarial()
    assert json.dumps(r1.as_dict(), sort_keys=True) == json.dumps(r2.as_dict(), sort_keys=True)


def test_artifact_emission_byte_equal(tmp_path: Path) -> None:
    r = evaluate_adversarial()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    emit_adversarial_report(r, out1)
    emit_adversarial_report(r, out2)
    assert out1.read_bytes() == out2.read_bytes()
