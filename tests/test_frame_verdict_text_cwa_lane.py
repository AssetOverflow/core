"""Text closed-world (CWA) FrameVerdict lane (B4 PR-2).

Two obligations kept separate:
  - the production ``evaluate_frame_verdict`` matches the hand-authored gold (wrong=0);
  - the gold is INDEPENDENT — cross-checked against the disjoint truth-table oracle
    (``oracle.oracle_frame_verdict``, which imports no engine module and uses its own parser
    + brute-force enumeration, NOT the ROBDD). A passing lane cannot be the evaluator grading
    its own output. Closed-world False (``entailed_false``) is produced ONLY inside a
    ``FrameVerdict`` with an admissible positive-refutation proof; absence stays UNDETERMINED.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from evals.frame_verdict_text_cwa.oracle import oracle_frame_verdict
from evals.frame_verdict_text_cwa.score import _frame, _load, run
from generate.frame_verdict import (
    FrameVerdict,
    FrameVerdictKind,
    PositiveRefutationKind,
    evaluate_frame_verdict,
)

_V1 = Path(__file__).resolve().parent.parent / "evals" / "frame_verdict_text_cwa" / "v1"
_CASES_SHA = "519e9b0de4bf43a5766593f61107b74dc4debb619e53dbba9011d0674bc8c1d4"


def test_cases_sha_pinned() -> None:
    assert hashlib.sha256((_V1 / "cases.jsonl").read_bytes()).hexdigest() == _CASES_SHA


def test_lane_wrong_zero_and_covers() -> None:
    r = run()
    assert r["wrong"] == 0, r["wrongs"]
    assert r["correct"] == r["total"] >= 12


def _oracle(case) -> str:
    return oracle_frame_verdict(
        case["propositions"], case["query"],
        frame_kind=case["frame_kind"], world_assumption=case["world_assumption"],
        closure_declared=case["closure_declared"],
    )


def test_gold_matches_independent_oracle() -> None:
    # non-vacuity: the disjoint truth-table oracle independently confirms every gold.
    for case in _load():
        assert _oracle(case) == case["gold"], case["id"]


def test_engine_matches_independent_oracle() -> None:
    # the production ROBDD evaluator agrees with the disjoint truth-table oracle on every case.
    for case in _load():
        v = evaluate_frame_verdict(_frame(case), case["query"])
        assert isinstance(v, FrameVerdict)  # never a Determined — no open-world leak
        assert v.verdict.name == _oracle(case), case["id"]


def test_entailed_false_is_admissible_and_proof_backed() -> None:
    for case in _load():
        v = evaluate_frame_verdict(_frame(case), case["query"])
        if v.verdict is FrameVerdictKind.ENTAILED_FALSE:
            assert v.proof.producer == "proof_chain.entail"
            assert v.proof.positive_refutation_kind is PositiveRefutationKind.ROBDD_REFUTATION
            assert v.proof.proof_sha256


def test_absence_and_open_are_never_false() -> None:
    # the absence/open cases must NOT be entailed_false (the wrong=0 bite for this lane).
    for case in _load():
        if case["id"] in {"fvt-003", "fvt-006", "fvt-007", "fvt-008"}:
            v = evaluate_frame_verdict(_frame(case), case["query"])
            assert v.verdict is not FrameVerdictKind.ENTAILED_FALSE, case["id"]
