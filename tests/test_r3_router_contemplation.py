"""Tests for wiring R3 into the contemplation router + pass manager (R3.1).

Pins the R3.1c matrix: supported R3 → SOLVED_VERIFIED; rate_unit_mismatch/combined → proposal-only
unsupported_rate_duration; temporal_state/missing/non-integer → REFUSED_KNOWN_BOUNDARY (no proposal);
R1/R2 unaffected; non-rate text never blocks an R2 proposal.
"""

from __future__ import annotations

from pathlib import Path

from core.comprehension_attempt import classify_r3, route_setup
from evals.constraint_oracle.runner import _load_r2_gold
from evals.rate_oracle.runner import _load_rate_gold
from evals.setup_oracle.runner import _load_r1_gold
from generate.contemplation import Terminal, contemplate


def test_classify_r3_matches_gold_expect() -> None:
    for fx in _load_rate_gold():
        att = classify_r3(fx["text"], case_id=fx["id"])
        assert att.organ == "r3_rate"
        if fx["expect"] in ("solved", "solver_refuses"):
            assert att.outcome == "setup_correct" and att.setup_signature is not None
        else:
            assert att.outcome == "setup_refused" and att.refusal_reason == fx["reader_reason"]


def test_router_routes_rate_to_r3_and_stays_exclusive() -> None:
    routed = 0
    for fx in _load_rate_gold():
        r = route_setup(fx["text"])
        assert len(r.attempts) == 3 and r.status != "ambiguous"
        if r.selected is not None:
            assert r.selected.organ == "r3_rate"
            routed += 1
    assert routed == 8  # 6 solved + 2 solver_refuses
    # adding R3 does not make any R1/R2 problem ambiguous, nor route it to r3
    for fx in _load_r1_gold() + _load_r2_gold():
        r = route_setup(fx["text"])
        assert r.status != "ambiguous"
        if r.selected is not None:
            assert r.selected.organ != "r3_rate"


def _expected_r3_terminal(fx: dict) -> Terminal:
    if fx["expect"] == "solved":
        return Terminal.SOLVED_VERIFIED
    if fx["expect"] == "solver_refuses":
        return Terminal.REFUSED_KNOWN_BOUNDARY
    if fx["reader_reason"] in ("rate_unit_mismatch", "combined_rates"):
        return Terminal.PROPOSAL_EMITTED
    return Terminal.REFUSED_KNOWN_BOUNDARY  # missing_time / temporal_state


def test_contemplation_r3_terminals_and_only_rate_like_propose(tmp_path: Path) -> None:
    for fx in _load_rate_gold():
        kwargs = {"options": fx["options"], "answer_key": fx["answer"]} if fx["expect"] == "solved" else {}
        result = contemplate(fx["text"], proposal_root=tmp_path, case_id=fx["id"], **kwargs)
        assert result.terminal == _expected_r3_terminal(fx), f"{fx['id']}: {result.terminal}"
        if fx["expect"] == "solved":
            assert result.answer == fx["gold"]
        if result.terminal == Terminal.PROPOSAL_EMITTED:
            assert result.family == "unsupported_rate_duration"
    # ONLY the two rate-like unsupported features proposed; temporal/missing/non-integer did not.
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_non_rate_text_does_not_block_r2_proposal(tmp_path: Path) -> None:
    # r2-011 (missing_total_count) must still PROPOSAL_EMITTED — R3's not_rate_shaped refusal on
    # this non-rate text is input_shape (not-my-domain), never a substantive boundary.
    fx = next(f for f in _load_r2_gold() if f["id"] == "r2-011-missing-total-count")
    result = contemplate(fx["text"], proposal_root=tmp_path)
    assert result.terminal == Terminal.PROPOSAL_EMITTED and result.family == "missing_total_count"
