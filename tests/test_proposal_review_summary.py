"""Tests for the pure idle_summary function (IT-a)."""

from __future__ import annotations

import json
from pathlib import Path

from core.proposal_review.summary import ProposalReviewIdleSummary, idle_summary
from evals.constraint_oracle.runner import _load_r2_gold
from generate.contemplation import contemplate


def _emit(root: Path) -> None:
    for fx in _load_r2_gold():
        if fx["expect"] == "reader_refuses" and fx["reader_reason"] in (
            "missing_total_count",
            "missing_weighted_total",
        ):
            contemplate(fx["text"], proposal_root=root, case_id=fx["id"])


def test_empty_sink_is_safe_and_zero(tmp_path: Path) -> None:
    s = idle_summary(tmp_path)
    assert s == ProposalReviewIdleSummary(safe=True, total=0, review_needed=0, malformed=0, by_family=())


def test_valid_proposals_summarized(tmp_path: Path) -> None:
    _emit(tmp_path)
    s = idle_summary(tmp_path)
    assert s.safe and s.total == 2 and s.review_needed == 2 and s.malformed == 0
    assert dict(s.by_family) == {"missing_total_count": 1, "missing_weighted_total": 1}
    assert s.errors == ()


def test_malformed_makes_unsafe(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{ not json", encoding="utf-8")
    s = idle_summary(tmp_path)
    assert not s.safe and s.malformed == 1 and s.errors


def test_unsafe_artifact_flagged(tmp_path: Path) -> None:
    doc = {
        "status": "proposal_only", "failure_family": "missing_total_count",
        "problem_text_sha256": "a" * 64, "observed_attempts": [],
        "suggested_next_fixture": None, "requires_review": True, "mounted": True,  # <- unsafe
    }
    import hashlib

    h = hashlib.sha256(b"missing_total_count:" + b"a" * 64).hexdigest()
    (tmp_path / f"{h}.json").write_text(json.dumps(doc), encoding="utf-8")
    s = idle_summary(tmp_path)
    assert not s.safe and any("mounted" in e for e in s.errors)


def test_summary_is_deterministic(tmp_path: Path) -> None:
    _emit(tmp_path)
    assert idle_summary(tmp_path) == idle_summary(tmp_path)


def test_summary_is_read_only(tmp_path: Path) -> None:
    _emit(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    idle_summary(tmp_path)
    after = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    assert before == after and before


def test_summary_is_json_serializable(tmp_path: Path) -> None:
    _emit(tmp_path)
    s = idle_summary(tmp_path)
    # primitives only -> trivially serializable (no paths / raw content / mutable dicts)
    json.dumps(
        {
            "safe": s.safe, "total": s.total, "review_needed": s.review_needed,
            "malformed": s.malformed, "by_family": list(s.by_family), "errors": list(s.errors),
        }
    )
