"""ADR-0114a Obligation #10 — pack-provenance auditor tests.

Pins the invariants:
  - lemma-id parser handles well-formed + malformed input
  - validator detects: unparseable id, wrong pack id, unknown lemma
  - refusal-expected cases skip cleanly (no false violation)
  - missing pack lexicon refuses with a typed reason
  - report is deterministic across calls
  - snapshot: current main's B3 lane satisfies obligation #10
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.capability.pack_provenance import (
    DEFAULT_MATH_LEXICON,
    DEFAULT_MATH_PACK_ID,
    PackProvenanceError,
    _load_lexicon_lemmas,
    _parse_lemma_id,
    emit_provenance_report,
    validate_lane,
)


# ---------------------------------------------------------------------------
# Lemma-id parser
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lemma_id, expected",
    [
        ("en_arithmetic_v1:add", ("en_arithmetic_v1", "add")),
        ("pack:lemma_with_underscore", ("pack", "lemma_with_underscore")),
        ("a:b", ("a", "b")),
    ],
)
def test_parse_lemma_id_accepts_wellformed(lemma_id, expected) -> None:
    assert _parse_lemma_id(lemma_id) == expected


@pytest.mark.parametrize(
    "lemma_id",
    [
        "",
        "no_colon",
        ":missing_pack",
        "missing_lemma:",
        ":",
    ],
)
def test_parse_lemma_id_rejects_malformed(lemma_id) -> None:
    assert _parse_lemma_id(lemma_id) is None


# ---------------------------------------------------------------------------
# Lexicon loader
# ---------------------------------------------------------------------------


def test_load_lexicon_lemmas_loads_arithmetic_pack() -> None:
    lemmas = _load_lexicon_lemmas(DEFAULT_MATH_LEXICON)
    # The 8 operation kinds the solver requires.
    required = {
        "add", "subtract", "transfer", "multiply", "divide",
        "apply_rate", "compare_additive", "compare_multiplicative",
    }
    assert required.issubset(lemmas), f"missing: {required - lemmas}"


def test_load_lexicon_lemmas_raises_on_missing_pack(tmp_path: Path) -> None:
    with pytest.raises(PackProvenanceError) as exc:
        _load_lexicon_lemmas(tmp_path / "nonexistent.jsonl")
    assert "not found" in str(exc.value).lower()


def test_load_lexicon_lemmas_raises_on_invalid_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not valid json\n", encoding="utf-8")
    with pytest.raises(PackProvenanceError):
        _load_lexicon_lemmas(bad)


def test_load_lexicon_lemmas_raises_on_missing_lemma_field(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"entry_id": "x-001", "surface": "foo"}\n', encoding="utf-8")
    with pytest.raises(PackProvenanceError) as exc:
        _load_lexicon_lemmas(bad)
    assert "lemma" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Lane validation
# ---------------------------------------------------------------------------


def test_validate_lane_passes_on_b3_with_real_pack() -> None:
    """The load-bearing snapshot: current main's B3 lane satisfies
    obligation #10 against ``en_arithmetic_v1``. If this fails, either
    the pack lost a required lemma or B3 parsed a case to an operation
    whose lemma isn't registered — both are obligation violations."""
    report = validate_lane()
    assert report.obligation_10_passed is True, (
        f"obligation #10 failed: {report.refusal_reason}\n"
        f"violated cases: {[c.case_id for c in report.per_case if c.outcome == 'violated']}"
    )
    assert report.cases_validated > 0  # at least one trace was validated
    assert report.cases_violated == 0


def test_validate_lane_observes_expected_op_kinds() -> None:
    """B3's grammar exercises a subset of the 8 operation kinds; the
    observed set must be non-empty and every entry must have the
    expected ``<pack_id>:<lemma>`` shape."""
    report = validate_lane()
    assert len(report.distinct_lemma_ids_observed) > 0
    for lid in report.distinct_lemma_ids_observed:
        assert lid.startswith(f"{DEFAULT_MATH_PACK_ID}:")
        pack_id, _, lemma = lid.partition(":")
        assert pack_id == DEFAULT_MATH_PACK_ID
        assert lemma != ""


def test_validate_lane_refuses_on_missing_pack(tmp_path: Path) -> None:
    report = validate_lane(lexicon_path=tmp_path / "missing.jsonl")
    assert report.obligation_10_passed is False
    assert "not found" in report.refusal_reason.lower()


def test_validate_lane_refuses_on_missing_cases_file(tmp_path: Path) -> None:
    report = validate_lane(cases_path=tmp_path / "missing.jsonl")
    assert report.obligation_10_passed is False
    assert "not found" in report.refusal_reason.lower()


def test_validate_lane_skips_refusal_expected_cases(tmp_path: Path) -> None:
    """Cases with ``expected == "refused"`` must not count as
    obligation violations — they never produce a trace by design."""
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        '\n'.join([
            json.dumps({
                "case_id": "test-refused",
                "problem": "Some out-of-grammar text.",
                "expected": "refused",
            }),
            json.dumps({
                "case_id": "test-solved",
                "problem": "Sam has 5 apples. Sam buys 3 apples. How many apples does Sam have?",
                "expected": "solved_correct",
            }),
        ]) + "\n",
        encoding="utf-8",
    )
    report = validate_lane(cases_path=cases)
    by_id = {c.case_id: c for c in report.per_case}
    assert by_id["test-refused"].outcome == "skipped_unsolved"
    assert by_id["test-solved"].outcome == "validated"
    assert report.obligation_10_passed is True
    assert report.cases_violated == 0


# ---------------------------------------------------------------------------
# Determinism + artifact emission
# ---------------------------------------------------------------------------


def test_validate_lane_is_deterministic() -> None:
    r1 = validate_lane()
    r2 = validate_lane()
    assert json.dumps(r1.as_dict(), sort_keys=True) == json.dumps(r2.as_dict(), sort_keys=True)


def test_artifact_emission_byte_equal(tmp_path: Path) -> None:
    report = validate_lane()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    emit_provenance_report(report, out1)
    emit_provenance_report(report, out2)
    assert out1.read_bytes() == out2.read_bytes()
