"""Executable invariants for the Phase 5b composition validation sub-corpus.

The corpus (``evals/gsm8k_math/composition_validation/v1/cases.jsonl``) is the
ADR-0174 OQ#5 measurement instrument.  A JSONL of cases plus a prose contract is
only *decoration* until a test can fail under the violations it names
(CLAUDE.md, "Schema-Defined Proof Obligations").  This module is that test.

It enforces two kinds of obligation:

* **Forever-invariants** (never need updating as Phase 5b lands):
  - wrong=0 firewall: a case may only refuse or answer exactly ``gold``;
    a ``gold == null`` case may only refuse.
  - regression net: every ``gate == "baseline"`` row keeps solving to ``gold``.
  - permanence: every ``gate == "permanent"`` row keeps refusing.
  - frozen baseline snapshot for those non-positive rows matches the live tree.

* **Current snapshot** (the one assertion a Phase 5b slice updates when it
  flips a positive): the aggregate is ``4 solve / 16 refuse / 0 wrong`` today.

A future positive (``gate`` like ``5b-R1``) is *expected* to flip
refuse -> solve when its slice lands; that flip must still satisfy the firewall,
so it is checked by the firewall test, not pinned by a per-row baseline match.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.math_candidate_graph import parse_and_solve

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CASES_PATH = (
    _REPO_ROOT / "evals" / "gsm8k_math" / "composition_validation" / "v1" / "cases.jsonl"
)

_REQUIRED_FIELDS = frozenset(
    {
        "case_id",
        "source",
        "question",
        "gold",
        "target_verdict",
        "composition",
        "gate",
        "baseline_verdict",
        "baseline_answer",
        "baseline_branches_enumerated",
        "note",
    }
)

_EXPECTED_TOTAL = 22
_EXPECTED_BASELINE_CONTROLS = 4
_EXPECTED_PERMANENT = 7
_EXPECTED_FUTURE_POSITIVE = 11


def _load_cases() -> list[dict]:
    rows = [
        json.loads(line)
        for line in _CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return rows


_CASES = _load_cases()
_IDS = [c["case_id"] for c in _CASES]


def _num_eq(a, b) -> bool:
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) < 1e-6


def test_corpus_structure() -> None:
    """22 unique, fully-specified rows with the expected gate partition."""
    assert len(_CASES) == _EXPECTED_TOTAL
    assert len(set(_IDS)) == _EXPECTED_TOTAL, "duplicate case_id"
    for c in _CASES:
        missing = _REQUIRED_FIELDS - c.keys()
        assert not missing, f"{c.get('case_id')} missing fields: {missing}"
        assert c["target_verdict"] in {"solve", "refuse"}
        # gate ↔ target_verdict consistency
        if c["gate"] == "baseline":
            assert c["target_verdict"] == "solve"
        if c["target_verdict"] == "refuse":
            assert c["gate"] == "permanent", (
                f"{c['case_id']}: refuse target must be a permanent gate"
            )

    baseline = [c for c in _CASES if c["gate"] == "baseline"]
    permanent = [c for c in _CASES if c["gate"] == "permanent"]
    future = [c for c in _CASES if c["gate"].startswith("5b-")]
    assert len(baseline) == _EXPECTED_BASELINE_CONTROLS
    assert len(permanent) == _EXPECTED_PERMANENT
    assert len(future) == _EXPECTED_FUTURE_POSITIVE
    assert len(baseline) + len(permanent) + len(future) == _EXPECTED_TOTAL


@pytest.mark.parametrize("case", _CASES, ids=_IDS)
def test_wrong_zero_firewall(case: dict) -> None:
    """Forever: a case refuses or answers exactly gold; null-gold ⇒ refuse."""
    res = parse_and_solve(case["question"])
    if res.is_admitted:
        assert case["gold"] is not None, (
            f"{case['case_id']}: admitted {res.answer!r} but gold is null"
        )
        assert _num_eq(res.answer, case["gold"]), (
            f"{case['case_id']}: WRONG — admitted {res.answer!r} != gold {case['gold']!r}"
        )


@pytest.mark.parametrize(
    "case", [c for c in _CASES if c["gate"] == "baseline"], ids=[c["case_id"] for c in _CASES if c["gate"] == "baseline"]
)
def test_baseline_controls_still_solve(case: dict) -> None:
    """Forever regression net: baseline controls solve to gold."""
    res = parse_and_solve(case["question"])
    assert res.is_admitted, f"{case['case_id']}: control regressed to refuse"
    assert _num_eq(res.answer, case["gold"])


@pytest.mark.parametrize(
    "case", [c for c in _CASES if c["gate"] == "permanent"], ids=[c["case_id"] for c in _CASES if c["gate"] == "permanent"]
)
def test_permanent_refusals_still_refuse(case: dict) -> None:
    """Forever: permanent hard-negatives never admit."""
    res = parse_and_solve(case["question"])
    assert not res.is_admitted, (
        f"{case['case_id']}: permanent refusal admitted {res.answer!r}"
    )


@pytest.mark.parametrize(
    "case",
    [c for c in _CASES if c["gate"] in {"baseline", "permanent"}],
    ids=[c["case_id"] for c in _CASES if c["gate"] in {"baseline", "permanent"}],
)
def test_frozen_baseline_fields_match_tree(case: dict) -> None:
    """Non-positive rows never drift, so their recorded baseline snapshot must
    still equal the live result.  (Future positives are intentionally excluded —
    their snapshot is what a 5b slice flips.)"""
    res = parse_and_solve(case["question"])
    live_verdict = "solve" if res.is_admitted else "refuse"
    assert live_verdict == case["baseline_verdict"]
    assert res.branches_enumerated == case["baseline_branches_enumerated"]
    if res.is_admitted:
        assert _num_eq(res.answer, case["baseline_answer"])
    else:
        assert case["baseline_answer"] is None


def test_current_baseline_snapshot() -> None:
    """Current aggregate is 4 solve / 18 refuse / 0 wrong.

    This is the single assertion a Phase 5b slice updates when it flips a
    positive (refuse -> solve); the forever-invariants above do not change.
    """
    solve = refuse = wrong = 0
    for case in _CASES:
        res = parse_and_solve(case["question"])
        if res.is_admitted:
            solve += 1
            if case["gold"] is None or not _num_eq(res.answer, case["gold"]):
                wrong += 1
        else:
            refuse += 1
    assert wrong == 0
    assert (solve, refuse) == (4, 18), (
        f"snapshot moved to {solve} solve / {refuse} refuse — if a Phase 5b "
        f"slice landed, update this expectation and the affected rows' "
        f"baseline fields in lockstep"
    )


_TRAIN_SAMPLE_PATH = (
    _REPO_ROOT / "evals" / "gsm8k_math" / "train_sample" / "v1" / "cases.jsonl"
)


def _load_train_sample_answers() -> dict[str, object]:
    answers: dict[str, object] = {}
    for line in _TRAIN_SAMPLE_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        answers[rec["case_id"]] = rec["answer_numeric"]
    return answers


def test_dataset_golds_match_answer_numeric() -> None:
    """Contract invariant 6: every ``gsm8k_train_sample:*`` row's ``gold`` equals
    that case's ``answer_numeric`` verbatim.  A hand-computed (and thus possibly
    wrong) gold would be a ``wrong=0`` hazard inside the measurement instrument
    itself, so this is a real proof obligation, not decoration.

    ``guard:*`` / ``analysis:*`` rows are seeded probes, not dataset cases, and
    are intentionally excluded.
    """
    answers = _load_train_sample_answers()
    checked = 0
    for case in _CASES:
        source = case["source"]
        if not source.startswith("gsm8k_train_sample:"):
            continue
        idx = source.split(":", 1)[1]
        ts_id = f"gsm8k-train-sample-v1-{idx}"
        assert ts_id in answers, f"{case['case_id']}: unknown train_sample source {source}"
        assert _num_eq(case["gold"], answers[ts_id]), (
            f"{case['case_id']}: gold {case['gold']!r} != dataset answer_numeric "
            f"{answers[ts_id]!r} for {source} — hand-computed gold is a wrong=0 hazard"
        )
        checked += 1
    assert checked >= 8, f"expected ≥8 dataset-sourced rows, checked {checked}"
