"""Tests for ADR-0161 Step 2: HITL review queue backpressure (cap + reports)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    DEFAULT_PENDING_CAP,
    ProposalLog,
    RefusedAtCapacity,
    ReplayEvidence,
    TeachingChainProposal,
    build_proposal,
    propose_from_candidate,
)
from teaching.queue import derive_queue


def make_candidate(candidate_id: str, subject: str, obj: str = "truth") -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain={
            "subject": subject,
            "intent": "cause",
            "connective": "reveals",
            "object": obj,
        },
        trigger="would_have_grounded",
        source_turn_trace="trace_1",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="some_chain",
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )


def _fake_replay_equivalent(chain):
    return ReplayEvidence(
        baseline={"intent_accuracy": 1.0},
        candidate={"intent_accuracy": 1.0},
        regressed_metrics=(),
        replay_equivalent=True,
    )


def test_default_pending_cap_is_pinned():
    """ADR-0161 §4: default pending cap is strictly 256.

    Any changes to this default require an ADR amendment.
    """
    assert DEFAULT_PENDING_CAP == 256


def test_capacity_boundaries(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Pre-populate log with 2 pending proposals; unique objects to avoid
    # the dependent_on_pending check introduced in Step 3.
    for i in range(2):
        c = make_candidate(f"cand_{i}", f"subject_{i}", obj=f"object_{i}")
        proposal = build_proposal(c)
        log.record_created(proposal)

    # cap = 3. Current pending is 2 (which is cap - 1)
    # The 3rd candidate should land successfully
    c3 = make_candidate("cand_2", "subject_2", obj="object_2")
    res3 = propose_from_candidate(
        c3, log=log, run_replay=_fake_replay_equivalent, cap=3
    )
    assert isinstance(res3, TeachingChainProposal)
    assert log.find(res3.proposal_id)["state"] == "pending"

    # Current pending is now 3 (which is at cap).
    # The 4th candidate should be refused
    c4 = make_candidate("cand_3", "subject_3", obj="object_3")
    res4 = propose_from_candidate(
        c4, log=log, run_replay=_fake_replay_equivalent, cap=3
    )
    assert isinstance(res4, RefusedAtCapacity)
    assert res4.candidate_id == "cand_3"
    assert res4.pending_count == 3
    assert res4.cap == 3
    assert res4.report_path.exists()

    # Verify queue_full report contents
    report = json.loads(res4.report_path.read_text(encoding="utf-8"))
    assert report["report_kind"] == "queue_full"
    assert report["pending_count"] == 3
    assert report["cap"] == 3
    assert len(report["candidates_skipped"]) == 1
    assert report["candidates_skipped"][0]["candidate_id"] == "cand_3"
    assert report["candidates_skipped"][0]["shape_category"] == "factual"
    assert report["candidates_skipped"][0]["reason"] == "queue_full"

    # Verify that the 4th proposal was NOT written to the log
    assert log.find(build_proposal(c4).proposal_id) is None


def test_over_cap_refuses_consistently(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    # Pre-populate log with 5 pending proposals
    for i in range(5):
        c = make_candidate(f"cand_{i}", f"subject_{i}")
        proposal = build_proposal(c)
        log.record_created(proposal)

    # With cap = 3 (current pending = 5), we are already over capacity
    # It should refuse consistently
    c_new = make_candidate("cand_new", "subject_new")
    res = propose_from_candidate(
        c_new, log=log, run_replay=_fake_replay_equivalent, cap=3
    )
    assert isinstance(res, RefusedAtCapacity)
    assert res.pending_count == 5
    assert res.cap == 3


def test_core_hitl_pending_cap_env_var_override(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    # Pre-populate log with 2 pending proposals
    for i in range(2):
        c = make_candidate(f"cand_{i}", f"subject_{i}")
        proposal = build_proposal(c)
        log.record_created(proposal)

    # Set env var CORE_HITL_PENDING_CAP = 2. Current pending = 2
    # The 3rd candidate should be refused
    c3 = make_candidate("cand_2", "subject_2")
    with patch.dict(os.environ, {"CORE_HITL_PENDING_CAP": "2"}):
        res = propose_from_candidate(
            c3, log=log, run_replay=_fake_replay_equivalent
        )
        assert isinstance(res, RefusedAtCapacity)
        assert res.cap == 2
        assert res.pending_count == 2


def test_explicit_cap_kwarg_overrides_env_var(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    # Unique objects to avoid the dependent_on_pending check (Step 3).
    for i in range(2):
        c = make_candidate(f"cand_{i}", f"subject_{i}", obj=f"object_{i}")
        proposal = build_proposal(c)
        log.record_created(proposal)

    c3 = make_candidate("cand_2", "subject_2", obj="object_2")
    # env var is 2, but kwarg is 5. Should successfully propose
    with patch.dict(os.environ, {"CORE_HITL_PENDING_CAP": "2"}):
        res = propose_from_candidate(
            c3, log=log, run_replay=_fake_replay_equivalent, cap=5
        )
        assert isinstance(res, TeachingChainProposal)
        assert log.find(res.proposal_id)["state"] == "pending"


def test_repropose_same_candidate_post_clearance(tmp_path: Path):
    """Step 3 behavior: at-capacity duplicate → capacity refusal; under-cap duplicate
    (even if accepted) → RefusedAsDuplicate.  Unique objects used throughout to
    avoid the dependent_on_pending check introduced in Step 3."""
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)

    # 1. Propose candidate when space is available (cap = 2, current pending = 0)
    c1 = make_candidate("cand_1", "subject_1", obj="object_1")
    res1 = propose_from_candidate(
        c1, log=log, run_replay=_fake_replay_equivalent, cap=2
    )
    assert isinstance(res1, TeachingChainProposal)
    proposal_id_original = res1.proposal_id

    # 2. Add another pending to hit cap (unique object avoids dependency check)
    c2 = make_candidate("cand_2", "subject_2", obj="object_2")
    res2 = propose_from_candidate(
        c2, log=log, run_replay=_fake_replay_equivalent, cap=2
    )
    assert isinstance(res2, TeachingChainProposal)

    # Now pending count is 2, cap is 2.
    # 3. Re-proposing candidate 1 at capacity: capacity check fires first (Step 3
    # order: cap → duplicate → dependency).  Returns RefusedAtCapacity.
    from teaching.proposals import RefusedAtCapacity as _RefusedAtCapacity
    res1_again = propose_from_candidate(
        c1, log=log, run_replay=_fake_replay_equivalent, cap=2
    )
    assert isinstance(res1_again, _RefusedAtCapacity)

    # 4. Transition candidate 1 to accepted (clearance)
    log.record_transition(proposal_id_original, "accepted", "ratified")

    # Now pending count is 1 (candidate 2 is still pending, candidate 1 is accepted).
    # Step 3: re-proposing the same content (same proposal_id) returns RefusedAsDuplicate
    # regardless of the existing state.  The duplicate check fires before the replay gate.
    from teaching.proposals import RefusedAsDuplicate as _RefusedAsDuplicate
    res1_post_clear = propose_from_candidate(
        c1, log=log, run_replay=_fake_replay_equivalent, cap=2
    )
    assert isinstance(res1_post_clear, _RefusedAsDuplicate)
    assert res1_post_clear.proposal_id == proposal_id_original
    assert res1_post_clear.existing_state == "accepted"


def test_queue_full_report_byte_stability(tmp_path: Path):
    log_path = tmp_path / "proposals.jsonl"
    log = ProposalLog(log_path)
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Pre-populate log to hit cap
    c = make_candidate("cand_0", "subject_0")
    proposal = build_proposal(c)
    log.record_created(proposal)

    # Force a known revision and timestamp for byte-stability
    with patch("teaching.proposals._current_revision", return_value="f00ba2"):
        c1 = make_candidate("cand_1", "subject_1")
        res1 = propose_from_candidate(
            c1, log=log, run_replay=_fake_replay_equivalent, cap=1
        )
        assert isinstance(res1, RefusedAtCapacity)
        report_text1 = res1.report_path.read_text(encoding="utf-8")

    # Delete the report and re-run with same parameters to verify byte-stable output
    res1.report_path.unlink()
    with patch("teaching.proposals._current_revision", return_value="f00ba2"):
        res2 = propose_from_candidate(
            c1, log=log, run_replay=_fake_replay_equivalent, cap=1
        )
        assert isinstance(res2, RefusedAtCapacity)
        report_text2 = res2.report_path.read_text(encoding="utf-8")

    # The JSON string must be exactly identical
    assert report_text1 == report_text2

    # Check key ordering
    parsed = json.loads(report_text1)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def snapshot_dir(directory: Path) -> dict[Path, bytes]:
    snapshot = {}
    if not directory.exists():
        return snapshot
    for path in directory.glob("**/*"):
        if path.is_file():
            snapshot[path] = path.read_bytes()
    return snapshot


def test_capacity_refusal_does_not_mutate_system():
    """Verify capacity refusal does not mutate packs, corpus, or recognizer registry."""
    project_root = Path(__file__).resolve().parent.parent
    dirs = [
        project_root / "teaching" / "cognition_chains",
        project_root / "packs",
        project_root / "language_packs" / "data",
    ]

    before_snapshots = {}
    for d in dirs:
        before_snapshots[d] = snapshot_dir(d)

    # Trigger a capacity refusal
    tmp_log = ProposalLog(project_root / "teaching" / "proposals" / "temp_proposals.jsonl")
    c = make_candidate("cand_x", "subject_x")
    res = propose_from_candidate(
        c, log=tmp_log, run_replay=_fake_replay_equivalent, cap=0
    )
    assert isinstance(res, RefusedAtCapacity)

    # Clean up temp files if created in the directory
    if tmp_log.path.exists():
        tmp_log.path.unlink()
    # Clean up generated runs file
    if res.report_path.exists():
        res.report_path.unlink()

    # Assert no mutations occurred in system folders
    for d in dirs:
        after_snapshot = snapshot_dir(d)
        assert after_snapshot == before_snapshots[d], f"Directory {d} was mutated!"
