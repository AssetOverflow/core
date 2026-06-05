"""Staged independent-gold lanes for future comprehension domains.

These tests validate the GOLD side only: fixed structured cases, independent
oracles, refusal-first malformed handling, and no capability-index wiring before
readers exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.capability_index import adapters
from evals.set_membership import runner as set_runner
from evals.set_membership.oracle import (
    OracleError as SetOracleError,
    oracle_answer as set_answer,
)
from evals.syllogism import runner as syllogism_runner
from evals.syllogism.oracle import (
    OracleError as SyllogismOracleError,
    oracle_answer as syllogism_answer,
)
from evals.total_ordering import runner as order_runner
from evals.total_ordering.oracle import (
    OracleError as OrderOracleError,
    oracle_answer as order_answer,
)


_ROOT = Path(__file__).resolve().parent.parent
_LANES = ("set_membership", "total_ordering", "syllogism")


def _cases(domain: str) -> list[dict]:
    path = _ROOT / "evals" / domain / "v1" / "cases.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@pytest.mark.parametrize(
    ("domain", "runner"),
    [
        ("set_membership", set_runner),
        ("total_ordering", order_runner),
        ("syllogism", syllogism_runner),
    ],
)
def test_staged_gold_lane_integrity(domain, runner) -> None:
    report = runner.run()
    assert report["domain"] == domain
    assert report["gold_integrity_failures"] == []
    assert report["wrong"] == 0
    assert report["refused"] == 0
    assert report["total"] == report["correct"]
    assert report["counts"] == {
        "correct": report["correct"],
        "wrong": 0,
        "refused": 0,
    }


@pytest.mark.parametrize("domain", _LANES)
def test_cases_are_structured_not_text_only(domain: str) -> None:
    cases = _cases(domain)
    assert len(cases) >= 8
    assert [case["id"] for case in cases] == sorted(case["id"] for case in cases)
    assert {case["seed"] for case in cases} == {20260605}
    for case in cases:
        assert isinstance(case["text"], str) and case["text"]
        assert isinstance(case["structure"], dict) and case["structure"]
        assert isinstance(case["query"], dict) and case["query"]
        assert "gold" in case


def test_set_membership_oracle_is_deterministic_and_refusal_first() -> None:
    case = _cases("set_membership")[0]
    assert set_answer(case["structure"], case["query"]) is True
    assert set_answer(case["structure"], case["query"]) is True
    with pytest.raises(SetOracleError):
        set_answer(case["structure"], {"kind": "member", "element": "ghost", "set": "bird"})
    with pytest.raises(SetOracleError):
        set_answer(case["structure"], {"kind": "union", "left": "raven", "right": "bird"})


def test_total_ordering_oracle_is_deterministic_and_refusal_first() -> None:
    case = _cases("total_ordering")[0]
    assert order_answer(case["structure"], case["query"]) == ["bronze", "silver", "gold"]
    assert order_answer(case["structure"], case["query"]) == ["bronze", "silver", "gold"]
    with pytest.raises(OrderOracleError):
        order_answer(
            {"items": ["a", "b", "c"], "relations": [{"less": "a", "greater": "b"}]},
            {"kind": "sort", "order": "ascending"},
        )
    with pytest.raises(OrderOracleError):
        order_answer(
            {
                "items": ["a", "b"],
                "relations": [
                    {"less": "a", "greater": "b"},
                    {"less": "b", "greater": "a"},
                ],
            },
            {"kind": "compare", "left": "a", "right": "b"},
        )


def test_syllogism_oracle_is_deterministic_and_refusal_first() -> None:
    case = _cases("syllogism")[0]
    expected = {
        "valid": True,
        "conclusion": {"form": "A", "subject": "whale", "predicate": "animal"},
    }
    assert syllogism_answer(case["structure"], case["query"]) == expected
    assert syllogism_answer(case["structure"], case["query"]) == expected
    with pytest.raises(SyllogismOracleError):
        syllogism_answer(
            {
                "terms": ["a", "b"],
                "domain_size": 3,
                "premises": [{"form": "X", "subject": "a", "predicate": "b"}],
            },
            {"kind": "validity", "conclusion": {"form": "A", "subject": "a", "predicate": "b"}},
        )
    with pytest.raises(SyllogismOracleError):
        syllogism_answer(
            {
                "terms": ["a", "b"],
                "domain_size": 3,
                "premises": [
                    {"form": "A", "subject": "a", "predicate": "b"},
                    {"form": "O", "subject": "a", "predicate": "b"},
                ],
            },
            {"kind": "validity", "conclusion": {"form": "A", "subject": "a", "predicate": "b"}},
        )


def test_staged_lanes_are_not_capability_index_adapters() -> None:
    adapter_names = {fn.__name__ for fn in adapters.ADAPTERS}
    assert "set_membership_result" not in adapter_names
    assert "total_ordering_result" not in adapter_names
    assert "syllogism_result" not in adapter_names


def test_new_oracles_do_not_import_engine_or_geometry_modules() -> None:
    forbidden = ("import algebra", "import field", "import generate", "from algebra", "from field", "from generate")
    for domain in _LANES:
        source = (_ROOT / "evals" / domain / "oracle.py").read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden)
