"""Tests for the proposal-only failure-artifact emitter (N5).

Pins the toothless guarantees: proposals are only emitted for growth-surface families, are
content-addressed + deterministic + idempotent, carry `status=proposal_only` / `mounted=false`,
hash (never store) the problem text, and are never referenced by any serving-path module.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.comprehension_attempt import classify_r1, classify_r2, family_by_name
from core.comprehension_attempt.proposal import (
    FailureProposal,
    build_proposal,
    emit_proposal,
)

_MISSING_TOTAL = "Each large bus holds 50 students and each small bus holds 30 students. The buses carry 260 students in total. How many large buses are there?"


def _attempts(text: str):
    return (classify_r1(text), classify_r2(text))


def test_emit_writes_proposal_only_for_growth_surface(tmp_path: Path) -> None:
    family = family_by_name("missing_total_count")
    path = emit_proposal(_MISSING_TOTAL, family, _attempts(_MISSING_TOTAL), root=tmp_path)
    assert path is not None and path.exists()
    doc = json.loads(path.read_text())
    assert doc["status"] == "proposal_only"
    assert doc["mounted"] is False and doc["requires_review"] is True
    assert doc["failure_family"] == "missing_total_count"
    assert doc["suggested_next_fixture"] is None


def test_no_proposal_for_a_correct_boundary(tmp_path: Path) -> None:
    family = family_by_name("unsupported_system_size")  # too_many_categories — must stay refused
    text = "A lot has 10 vehicles. Each car has 4 wheels, each motorcycle has 2 wheels, and each truck has 6 wheels. Together the vehicles have 34 wheels. How many cars are there?"
    assert build_proposal(text, family, _attempts(text)) is None
    assert emit_proposal(text, family, _attempts(text), root=tmp_path) is None
    assert list(tmp_path.glob("*.json")) == []


def test_content_addressed_filename_is_deterministic(tmp_path: Path) -> None:
    family = family_by_name("missing_total_count")
    a = emit_proposal(_MISSING_TOTAL, family, _attempts(_MISSING_TOTAL), root=tmp_path)
    b = emit_proposal(_MISSING_TOTAL, family, _attempts(_MISSING_TOTAL), root=tmp_path)
    assert a == b  # same failure -> same path
    assert len(list(tmp_path.glob("*.json"))) == 1  # idempotent: one file
    assert a.read_text() == b.read_text()  # byte-identical


def test_problem_text_is_hashed_not_stored(tmp_path: Path) -> None:
    family = family_by_name("missing_total_count")
    path = emit_proposal(_MISSING_TOTAL, family, _attempts(_MISSING_TOTAL), root=tmp_path)
    raw = path.read_text()
    assert "large bus" not in raw and "students" not in raw  # the prose is not embedded
    assert json.loads(raw)["problem_text_sha256"]


def test_proposal_invariants_cannot_be_overridden() -> None:
    with pytest.raises(ValueError):
        FailureProposal("missing_total_count", "abc", (), status="ratified")
    with pytest.raises(ValueError):
        FailureProposal("missing_total_count", "abc", (), mounted=True)
    with pytest.raises(ValueError):
        FailureProposal("missing_total_count", "abc", (), requires_review=False)


def test_serving_path_never_references_proposals() -> None:
    # No serving-path module reads the proposal sink. Scan the forbidden/serving sources.
    repo = Path(__file__).resolve().parents[1]
    serving = [
        repo / "generate" / "stream.py",
        repo / "field" / "propagate.py",
        repo / "vault" / "store.py",
        repo / "generate" / "derivation",
        repo / "core" / "reliability_gate",
    ]
    for target in serving:
        files = [target] if target.is_file() else sorted(target.rglob("*.py")) if target.exists() else []
        for f in files:
            assert "comprehension_failures" not in f.read_text(encoding="utf-8"), f
