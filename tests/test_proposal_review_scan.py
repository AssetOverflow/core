"""Tests for the read-only proposal scanner (RPT-a).

Emits real proposals via the contemplation pass into a tmp sink, scans them into typed
PendingProposal records, flags malformed artifacts, and pins that scanning never mutates the sink.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.proposal_review.model import PendingProposal
from core.proposal_review.scan import scan
from evals.constraint_oracle.runner import _load_r2_gold
from generate.contemplation import contemplate


def _emit_gold_proposals(root: Path) -> None:
    for fx in _load_r2_gold():
        if fx["expect"] == "reader_refuses" and fx["reader_reason"] in (
            "missing_total_count",
            "missing_weighted_total",
        ):
            contemplate(fx["text"], proposal_root=root, case_id=fx["id"])


def test_scan_reads_emitted_proposals(tmp_path: Path) -> None:
    _emit_gold_proposals(tmp_path)
    proposals, malformed = scan(tmp_path)
    assert len(proposals) == 2 and malformed == []
    assert all(isinstance(p, PendingProposal) for p in proposals)
    assert {p.failure_family for p in proposals} == {"missing_total_count", "missing_weighted_total"}
    assert all(p.status == "proposal_only" and not p.mounted and p.requires_review for p in proposals)
    assert all(p.content_hash == Path(p.path).stem for p in proposals)


def test_scan_flags_malformed_artifacts(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{ not valid json", encoding="utf-8")
    (tmp_path / "incomplete.json").write_text(json.dumps({"status": "proposal_only"}), encoding="utf-8")
    proposals, malformed = scan(tmp_path)
    assert proposals == [] and len(malformed) == 2
    reasons = " ".join(m.reason for m in malformed)
    assert "invalid_json" in reasons and "missing_field" in reasons


def test_scan_missing_sink_is_empty(tmp_path: Path) -> None:
    assert scan(tmp_path / "does_not_exist") == ([], [])


def test_scan_is_read_only(tmp_path: Path) -> None:
    _emit_gold_proposals(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    scan(tmp_path)
    scan(tmp_path)
    after = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    assert before == after and before  # unchanged, and non-empty (the proposals exist)
