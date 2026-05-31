"""Foundation-curriculum relation binding v1 tests.

This suite pins the first deterministic binding layer above claim parsing.  The
binder converts parsed claim records into explicit relation structures only when
operands are present; otherwise it returns ``UNBOUND`` with a typed reason.
"""

from __future__ import annotations

import json
from pathlib import Path

from language_packs.claim_parsing import parse_claim
from language_packs.relation_binding import bind_claim, bind_text


EVAL_DIR = Path(__file__).resolve().parent.parent / "evals" / "language_relation_binding"
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


def test_every_public_case_matches_expected_relation_binding() -> None:
    cases = _cases_by_id()
    expected = _expected_by_id()
    for case_id, text in cases.items():
        assert bind_text(text).as_dict() == expected[case_id], case_id


def test_bound_relations_preserve_exact_evidence_span() -> None:
    for case_id, text in _cases_by_id().items():
        relation = bind_text(text).as_dict()
        if relation["state"] == "BOUND":
            assert relation["evidence_span"] == text, case_id
            assert relation["refusal_reason"] is None, case_id
            assert relation["relation"], case_id
            assert relation["arguments"], case_id


def test_unbound_relations_have_no_fabricated_arguments() -> None:
    for case_id, text in _cases_by_id().items():
        relation = bind_text(text).as_dict()
        if relation["state"] == "UNBOUND":
            assert relation["kind"] == "unbound", case_id
            assert relation["relation"] is None, case_id
            assert relation["arguments"] == {}, case_id
            assert relation["refusal_reason"], case_id


def test_binding_is_deterministic_across_repeated_calls() -> None:
    for text in _cases_by_id().values():
        first = bind_text(text).as_dict()
        for _ in range(5):
            assert bind_text(text).as_dict() == first


def test_bind_claim_preserves_source_kind_and_evidence() -> None:
    text = "Mary has 3 books."
    claim = parse_claim(text)
    relation = bind_claim(claim).as_dict()
    assert relation["source_kind"] == claim.kind
    assert relation["evidence_span"] == claim.evidence_span
    assert relation["state"] == "BOUND"
    assert relation["arguments"]["quantity"] == 3


def test_unmatched_claim_shape_stays_unbound() -> None:
    relation = bind_text("The sentence contains a structure not admitted by v1.").as_dict()
    assert relation["state"] == "UNBOUND"
    assert relation["kind"] == "unbound"
    assert relation["refusal_reason"] == "unmatched_v1_claim_shape"
