"""Tests for the deterministic proposal review report (RPT-b)."""

from __future__ import annotations

from pathlib import Path

from core.proposal_review.report import build_report, report_json, report_text
from core.proposal_review.scan import scan
from evals.constraint_oracle.runner import _load_r2_gold
from generate.contemplation import contemplate


def _emit(root: Path) -> None:
    for fx in _load_r2_gold():
        if fx["expect"] == "reader_refuses" and fx["reader_reason"] in (
            "missing_total_count",
            "missing_weighted_total",
        ):
            contemplate(fx["text"], proposal_root=root, case_id=fx["id"])


def test_report_counts(tmp_path: Path) -> None:
    _emit(tmp_path)
    report = build_report(*scan(tmp_path))
    assert report.total == 2
    assert report.by_family == {"missing_total_count": 1, "missing_weighted_total": 1}
    assert report.by_status == {"proposal_only": 2}
    assert report.malformed == 0
    assert len(report.review_needed) == 2


def test_report_json_is_deterministic(tmp_path: Path) -> None:
    _emit(tmp_path)
    assert report_json(build_report(*scan(tmp_path))) == report_json(build_report(*scan(tmp_path)))


def test_report_counts_malformed(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{ not json", encoding="utf-8")
    report = build_report(*scan(tmp_path))
    assert report.total == 0 and report.malformed == 1


def test_report_text_lists_families(tmp_path: Path) -> None:
    _emit(tmp_path)
    text = report_text(build_report(*scan(tmp_path)))
    assert "missing_total_count" in text and "2 pending" in text


def test_empty_sink_report(tmp_path: Path) -> None:
    report = build_report(*scan(tmp_path))
    assert report.total == 0 and report.by_family == {} and report.review_needed == ()
