"""Tests for the comprehension contemplation v0 pass manager (N6).

(Distinct from ADR-0056's teaching contemplation loop in ``tests/test_contemplation.py`` — this
is the comprehension-failure pass over the R1/R2 setup compilers, ``generate/contemplation/``.)

Drives every terminal state over both gold corpora and pins the batch acceptance criteria:

    known correct refusal      -> no proposal
    unsupported capability gap  -> proposal-only artifact
    answer-key contradiction    -> contradiction terminal
    multiple organ conflict     -> refusal (AMBIGUOUS_ORGAN)

Proposals are written to a tmp root so the repo is never touched.
"""

from __future__ import annotations

from pathlib import Path

from core.comprehension_attempt import ComprehensionAttempt, RouteResult
from evals.constraint_oracle.runner import _load_r2_gold
from evals.setup_oracle.runner import _load_r1_gold
from generate.contemplation import Terminal, contemplate
from generate.contemplation import pass_manager


def _expected_r2_terminal(fx: dict) -> Terminal:
    if fx["expect"] == "solved":
        return Terminal.SOLVED_VERIFIED
    if fx["expect"] == "solver_refuses":
        return Terminal.REFUSED_KNOWN_BOUNDARY
    if fx["reader_reason"] == "too_many_categories":
        return Terminal.REFUSED_UNSUPPORTED_FAMILY
    return Terminal.PROPOSAL_EMITTED  # missing_total_count / missing_weighted_total


def test_r2_gold_terminals_and_only_gaps_propose(tmp_path: Path) -> None:
    for fx in _load_r2_gold():
        kwargs = {}
        if fx["expect"] == "solved":
            kwargs = {"options": fx["options"], "answer_key": fx["answer"]}
        result = contemplate(fx["text"], proposal_root=tmp_path, case_id=fx["id"], **kwargs)
        assert result.terminal == _expected_r2_terminal(fx), f"{fx['id']}: {result.terminal}"
        if fx["expect"] == "solved":
            assert result.answer == fx["gold"]
    # ONLY the two missing_* gaps emitted a proposal — never a correct boundary.
    proposals = list(tmp_path.glob("*.json"))
    assert len(proposals) == 2, [p.name for p in proposals]


def test_r1_gold_terminals_emit_no_proposals(tmp_path: Path) -> None:
    expected = {
        "r1-08-ambiguous-referent": Terminal.REFUSED_UNSUPPORTED_FAMILY,
        "r1-09-missing-base": Terminal.REFUSED_KNOWN_BOUNDARY,
        "r1-10-distractor": Terminal.REFUSED_UNSUPPORTED_FAMILY,
    }
    for fx in _load_r1_gold():
        result = contemplate(fx["text"], proposal_root=tmp_path, case_id=fx["id"])
        assert result.terminal == expected.get(fx["id"], Terminal.SOLVED_VERIFIED), fx["id"]
    assert list(tmp_path.glob("*.json")) == []  # no proposal for any correct R1 refusal


def test_answer_key_contradiction_is_a_terminal() -> None:
    fx = next(f for f in _load_r2_gold() if f["id"] == "r2-002-chickens")  # gold 11 == option A
    result = contemplate(fx["text"], options=fx["options"], answer_key="D")  # D = 13 (wrong)
    assert result.terminal == Terminal.CONTRADICTION_DETECTED
    assert result.answer == 11 and result.family == "answer_key_contradiction"
    assert "contradicts" in result.message


def test_solved_setup_with_no_options_still_solves() -> None:
    fx = next(f for f in _load_r2_gold() if f["id"] == "r2-001-buses")
    result = contemplate(fx["text"])  # no options -> solve without choice verification
    assert result.terminal == Terminal.SOLVED_VERIFIED and result.answer == fx["gold"]


def test_ambiguous_organ_terminal(monkeypatch) -> None:
    # Both organs admitting a setup is incomparable -> the router refuses; the pass surfaces it.
    a1 = ComprehensionAttempt("r1_quantitative", "setup_correct", setup_signature="x")
    a2 = ComprehensionAttempt("r2_constraints", "setup_correct", setup_signature="y")
    monkeypatch.setattr(
        pass_manager, "route_setup",
        lambda text, case_id=None: RouteResult((a1, a2), None, "ambiguous"),
    )
    result = contemplate("anything")
    assert result.terminal == Terminal.AMBIGUOUS_ORGAN


def test_unrecognized_text_makes_no_progress(tmp_path: Path) -> None:
    result = contemplate("The weather is nice today.", proposal_root=tmp_path)
    assert result.terminal == Terminal.NO_PROGRESS
    assert list(tmp_path.glob("*.json")) == []
