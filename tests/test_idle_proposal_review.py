"""Contract tests for the read-only proposal-review sub-pass of idle_tick (IT-b).

Pins the runtime contract: default-off preserves the existing IdleTickResult shape/behavior;
enabled surfaces a summary; a reporter exception is CAPTURED (safe=False) and never corrupts
the tick; the read-only sub-pass never sets did_work / checkpoints / mutates / creates proposals.
"""

from __future__ import annotations

from pathlib import Path

import chat.runtime as rtmod
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.proposal_review.summary import ProposalReviewIdleSummary

_OK = ProposalReviewIdleSummary(safe=True, total=0, review_needed=0, malformed=0, by_family=())


def _rt(tmp_path: Path, *, review: bool = False) -> ChatRuntime:
    return ChatRuntime(
        config=RuntimeConfig(review_pending_proposals=review), engine_state_path=tmp_path
    )


def test_default_off_proposal_review_is_none(tmp_path: Path) -> None:
    result = _rt(tmp_path).idle_tick()
    assert result.proposal_review is None  # additive field absent for existing callers
    assert result.candidates_contemplated == 0 and result.proposals_created == 0


def test_enabled_surfaces_the_summary(tmp_path: Path, monkeypatch) -> None:
    sentinel = ProposalReviewIdleSummary(
        safe=True, total=3, review_needed=3, malformed=0, by_family=(("missing_total_count", 3),)
    )
    monkeypatch.setattr(rtmod, "idle_summary", lambda *a, **k: sentinel)
    assert _rt(tmp_path, review=True).idle_tick().proposal_review == sentinel


def test_reporter_exception_is_captured_not_propagated(tmp_path: Path, monkeypatch) -> None:
    def _boom(*a, **k):
        raise ValueError("sink exploded")

    monkeypatch.setattr(rtmod, "idle_summary", _boom)
    result = _rt(tmp_path, review=True).idle_tick()  # must NOT raise
    assert result.proposal_review is not None
    assert result.proposal_review.safe is False
    assert result.proposal_review.errors == ("proposal_review_failed:ValueError",)
    assert result.candidates_contemplated == 0 and result.proposals_created == 0  # tick intact


def test_review_subpass_does_not_checkpoint_or_set_did_work(tmp_path: Path, monkeypatch) -> None:
    rt = _rt(tmp_path, review=True)
    calls: list[int] = []
    monkeypatch.setattr(rt, "checkpoint_engine_state", lambda: calls.append(1))
    monkeypatch.setattr(rtmod, "idle_summary", lambda *a, **k: _OK)
    result = rt.idle_tick()
    assert result.proposal_review is not None  # the review ran
    assert calls == []  # ...but a read-only review never checkpoints (no did_work)


def test_enabled_does_not_perturb_other_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rtmod, "idle_summary", lambda *a, **k: _OK)
    on = _rt(tmp_path, review=True).idle_tick()
    off = _rt(tmp_path).idle_tick()
    assert (on.candidates_contemplated, on.proposals_created, on.facts_consolidated) == (
        off.candidates_contemplated,
        off.proposals_created,
        off.facts_consolidated,
    )
