"""Tests for the proposal-review safety dry-check + CLI (RPT-c).

Each safety assertion is proven meaningful-fail: planting exactly one violating artifact makes
the dry-check fail on exactly that check. Also confirms serving never reads the sink (real repo).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.proposal_review.safety import dry_check
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


def _write(root: Path, *, family: str = "missing_total_count", text_sha: str = "a" * 64,
           name: str | None = None, **overrides: object) -> str:
    doc = {
        "status": "proposal_only", "failure_family": family, "problem_text_sha256": text_sha,
        "observed_attempts": [], "suggested_next_fixture": None, "requires_review": True,
        "mounted": False,
    }
    doc.update(overrides)
    stem = name or hashlib.sha256(f"{family}:{text_sha}".encode("utf-8")).hexdigest()
    (root / f"{stem}.json").write_text(json.dumps(doc), encoding="utf-8")
    return stem


def test_dry_check_passes_for_real_proposals(tmp_path: Path) -> None:
    _emit(tmp_path)
    verdict = dry_check(*scan(tmp_path), root=tmp_path)
    assert verdict.ok and verdict.violations == ()


def test_dry_check_flags_mounted(tmp_path: Path) -> None:
    _write(tmp_path, mounted=True)
    verdict = dry_check(*scan(tmp_path), root=tmp_path)
    assert not verdict.ok and any("mounted" in v for v in verdict.violations)


def test_dry_check_flags_non_proposal_status(tmp_path: Path) -> None:
    _write(tmp_path, status="ratified")
    verdict = dry_check(*scan(tmp_path), root=tmp_path)
    assert not verdict.ok and any("status" in v for v in verdict.violations)


def test_dry_check_flags_requires_review_false(tmp_path: Path) -> None:
    _write(tmp_path, requires_review=False)
    verdict = dry_check(*scan(tmp_path), root=tmp_path)
    assert not verdict.ok and any("requires_review" in v for v in verdict.violations)


def test_dry_check_flags_content_address_mismatch(tmp_path: Path) -> None:
    _write(tmp_path, name="deadbeef")  # filename != sha256(family:text_sha)
    verdict = dry_check(*scan(tmp_path), root=tmp_path)
    assert not verdict.ok and any("content-address" in v for v in verdict.violations)


def test_dry_check_flags_malformed(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{ not json", encoding="utf-8")
    verdict = dry_check(*scan(tmp_path), root=tmp_path)
    assert not verdict.ok and any("malformed" in v for v in verdict.violations)


def test_serving_never_reads_the_sink_real_repo() -> None:
    # Against the real tree: no serving module references the sink, so an empty sink is OK.
    verdict = dry_check([], [], root=None)
    assert verdict.ok and not any("serving reads" in v for v in verdict.violations)


def test_cli_exit_codes(tmp_path: Path) -> None:
    from core.proposal_review.__main__ import main

    _emit(tmp_path)
    assert main(["--root", str(tmp_path)]) == 0
    assert main(["--root", str(tmp_path), "--json"]) == 0
    _write(tmp_path, mounted=True)
    assert main(["--root", str(tmp_path)]) == 1
