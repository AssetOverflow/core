"""Foundation-curriculum claim parsing v1 tests.

This test suite pins the first executable layer above ``en_core_syntax_v1``:
a deliberately small deterministic parser that emits typed claim records with
exact evidence spans, or ``UNDETERMINED`` with an explicit reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from language_packs.claim_parsing import parse_claim


EVAL_DIR = Path(__file__).resolve().parent.parent / "evals" / "language_claim_parsing"
CASES_PATH = EVAL_DIR / "cases_public.jsonl"
EXPECTED_PATH = EVAL_DIR / "expected_public.jsonl"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def _cases_by_id() -> dict[str, str]:
    return {entry["case_id"]: entry["text"] for entry in _jsonl(CASES_PATH)}


def _expected_by_id() -> dict[str, dict]:
    return {entry["case_id"]: entry["expected"] for entry in _jsonl(EXPECTED_PATH)}


def test_public_cases_and_expectations_are_line_aligned() -> None:
    cases = _jsonl(CASES_PATH)
    expected = _jsonl(EXPECTED_PATH)
    assert [entry["case_id"] for entry in cases] == [entry["case_id"] for entry in expected]


def test_every_public_case_matches_expected_claim_record() -> None:
    cases = _cases_by_id()
    expected = _expected_by_id()
    for case_id, text in cases.items():
        assert parse_claim(text).as_dict() == expected[case_id], case_id


def test_evidenced_claims_preserve_exact_input_as_evidence_span() -> None:
    for case_id, text in _cases_by_id().items():
        parsed = parse_claim(text).as_dict()
        if parsed["epistemic_state"] == "EVIDENCED":
            assert parsed["evidence_span"] == text, case_id
            assert parsed["refusal_reason"] is None, case_id


def test_undetermined_claims_include_refusal_reason() -> None:
    for case_id, text in _cases_by_id().items():
        parsed = parse_claim(text).as_dict()
        if parsed["epistemic_state"] == "UNDETERMINED":
            assert parsed["kind"] == "undetermined", case_id
            assert parsed["refusal_reason"], case_id
            assert parsed["subject"] is None, case_id
            assert parsed["relation"] is None, case_id
            assert parsed["object"] is None, case_id


def test_parser_is_deterministic_across_repeated_calls() -> None:
    for text in _cases_by_id().values():
        first = parse_claim(text).as_dict()
        for _ in range(5):
            assert parse_claim(text).as_dict() == first


def test_empty_input_refuses_without_fabricating_evidence() -> None:
    parsed = parse_claim("   ").as_dict()
    assert parsed["kind"] == "undetermined"
    assert parsed["epistemic_state"] == "UNDETERMINED"
    assert parsed["evidence_span"] == ""
    assert parsed["refusal_reason"] == "empty_input"
