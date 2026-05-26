"""Tests for ADR-0161 Step 3: submission-time invariants.

Covers duplicate + dependent_on_pending auto-rejection checks that fire
BEFORE the replay gate, in the order: capacity → duplicate → dependent.
"""

from __future__ import annotations

from pathlib import Path

from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalLog,
    RefusedAsDependent,
    RefusedAsDuplicate,
    RefusedAtCapacity,
    ReplayEvidence,
    TeachingChainProposal,
    build_proposal,
    propose_from_candidate,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_candidate(
    candidate_id: str,
    subject: str,
    obj: str = "truth",
    intent: str = "cause",
    connective: str = "reveals",
) -> DiscoveryCandidate:
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain={
            "subject": subject,
            "intent": intent,
            "connective": connective,
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


def _fake_replay_ok(_chain):  # noqa: ANN001
    return ReplayEvidence(
        baseline={"intent_accuracy": 1.0},
        candidate={"intent_accuracy": 1.0},
        regressed_metrics=(),
        replay_equivalent=True,
    )


def _write_pending_proposal(
    log: ProposalLog,
    candidate_id: str,
    subject: str,
    obj: str = "truth",
) -> str:
    """Inject a pending proposal directly into the log; returns proposal_id."""
    candidate = _make_candidate(candidate_id, subject, obj)
    proposal = build_proposal(candidate)
    log.record_created(proposal)
    return proposal.proposal_id


def _write_accepted_proposal(
    log: ProposalLog,
    candidate_id: str,
    subject: str,
    obj: str = "truth",
) -> str:
    """Inject a proposal in accepted state; returns proposal_id."""
    pid = _write_pending_proposal(log, candidate_id, subject, obj)
    log.record_transition(pid, "accepted", "accepted in test")
    return pid


# ---------------------------------------------------------------------------
# Duplicate: pending state
# ---------------------------------------------------------------------------


def test_duplicate_pending(tmp_path: Path) -> None:
    """Re-submitting a candidate whose proposal_id is already pending → RefusedAsDuplicate."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # First submission lands successfully.
    c1 = _make_candidate("cand-1", "light")
    result1 = propose_from_candidate(c1, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(result1, TeachingChainProposal)

    # Second submission of identical content → RefusedAsDuplicate.
    c1_again = _make_candidate("cand-1", "light")
    result2 = propose_from_candidate(c1_again, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(result2, RefusedAsDuplicate)
    assert result2.proposal_id == result1.proposal_id
    assert result2.existing_state == "pending"
    assert result2.reason == "duplicate"


# ---------------------------------------------------------------------------
# Duplicate: accepted state
# ---------------------------------------------------------------------------


def test_duplicate_after_accept(tmp_path: Path) -> None:
    """proposal_id in accepted state → RefusedAsDuplicate (idempotent for all states)."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    pid = _write_accepted_proposal(log, "cand-accept", "memory")

    candidate = _make_candidate("cand-accept", "memory")
    result = propose_from_candidate(candidate, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(result, RefusedAsDuplicate)
    assert result.proposal_id == pid
    assert result.existing_state == "accepted"
    assert result.reason == "duplicate"


# ---------------------------------------------------------------------------
# Dependent_on_pending: subject overlap
# ---------------------------------------------------------------------------


def test_dependent_on_pending_subject_overlap(tmp_path: Path) -> None:
    """Candidate whose chain subject matches a pending proposal's subject → RefusedAsDependent."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Proposal A is pending with subject="light".
    pid_a = _write_pending_proposal(log, "cand-A", "light", "order")

    # Candidate B shares subject="light".
    c_b = _make_candidate("cand-B", "light", "truth")
    result = propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)

    assert isinstance(result, RefusedAsDependent)
    assert pid_a in result.dependent_on
    assert "light" in result.overlapping_lemmas
    assert result.reason == "dependent_on_pending"


def test_dependent_on_pending_object_overlap(tmp_path: Path) -> None:
    """Candidate whose chain object matches a pending proposal's object → RefusedAsDependent."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Proposal A: object="knowledge"
    pid_a = _write_pending_proposal(log, "cand-A", "thought", "knowledge")

    # Candidate B: object="knowledge" (from different subject)
    c_b = _make_candidate("cand-B", "reason", "knowledge")
    result = propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)

    assert isinstance(result, RefusedAsDependent)
    assert pid_a in result.dependent_on
    assert "knowledge" in result.overlapping_lemmas


def test_dependent_on_pending_cross_overlap(tmp_path: Path) -> None:
    """Candidate whose subject matches pending item's object → RefusedAsDependent."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Proposal A: subject="perception", object="light"
    pid_a = _write_pending_proposal(log, "cand-A", "perception", "light")

    # Candidate B: subject="light" (same as A's object)
    c_b = _make_candidate("cand-B", "light", "clarity")
    result = propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)

    assert isinstance(result, RefusedAsDependent)
    assert pid_a in result.dependent_on
    assert "light" in result.overlapping_lemmas


# ---------------------------------------------------------------------------
# Dependent_on_pending: accepted state does NOT block
# ---------------------------------------------------------------------------


def test_no_block_when_dependency_accepted(tmp_path: Path) -> None:
    """Accepted proposal does not trigger dependent_on_pending check."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Proposal A is accepted (not pending).
    _write_accepted_proposal(log, "cand-A", "light", "order")

    # Candidate B with overlapping lemma should land.
    c_b = _make_candidate("cand-B", "light", "truth")
    result = propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)

    assert isinstance(result, TeachingChainProposal)


# ---------------------------------------------------------------------------
# No false positives: disjoint lemmas
# ---------------------------------------------------------------------------


def test_no_false_positives_disjoint_lemmas(tmp_path: Path) -> None:
    """Two candidates with completely disjoint lemmas both submit successfully."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    c1 = _make_candidate("cand-1", "fire", "heat")
    r1 = propose_from_candidate(c1, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(r1, TeachingChainProposal)

    c2 = _make_candidate("cand-2", "water", "flow")
    r2 = propose_from_candidate(c2, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(r2, TeachingChainProposal)


# ---------------------------------------------------------------------------
# Case-insensitive overlap
# ---------------------------------------------------------------------------


def test_case_insensitive_overlap(tmp_path: Path) -> None:
    """Lemma matching is case-insensitive."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Proposal A with subject="Light" (mixed case).
    pid_a = _write_pending_proposal(log, "cand-A", "Light", "order")

    # Candidate B with subject="LIGHT".
    c_b = _make_candidate("cand-B", "LIGHT", "clarity")
    result = propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)

    assert isinstance(result, RefusedAsDependent)
    assert pid_a in result.dependent_on


# ---------------------------------------------------------------------------
# cap-then-duplicate ordering: capacity refusal wins
# ---------------------------------------------------------------------------


def test_cap_beats_duplicate_ordering(tmp_path: Path) -> None:
    """When queue is full AND proposal is a duplicate, capacity refusal wins."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # Pre-populate log with 3 pending proposals to fill a cap=3 queue.
    for i in range(3):
        _write_pending_proposal(log, f"pre-{i}", f"subject_{i}", f"object_{i}")

    # First submission of "cand-dup" lands (cap=4, so it fits).
    c_first = _make_candidate("cand-dup", "unique_subject_x", "unique_object_x")
    r_first = propose_from_candidate(c_first, log=log, run_replay=_fake_replay_ok, cap=4)
    assert isinstance(r_first, TeachingChainProposal)

    # Now queue has 4 pending items. Re-submit same candidate with cap=4 still full.
    c_dup = _make_candidate("cand-dup", "unique_subject_x", "unique_object_x")
    result = propose_from_candidate(c_dup, log=log, run_replay=_fake_replay_ok, cap=4)
    # Cap fires first: 4 pending >= cap 4.
    assert isinstance(result, RefusedAtCapacity)


# ---------------------------------------------------------------------------
# Empty log: both checks pass, first proposal lands
# ---------------------------------------------------------------------------


def test_empty_log_first_proposal_lands(tmp_path: Path) -> None:
    """With an empty log, duplicate and dependency checks both pass cleanly."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    candidate = _make_candidate("cand-first", "thought", "form")
    result = propose_from_candidate(candidate, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(result, TeachingChainProposal)
    assert result.proposal_id is not None


# ---------------------------------------------------------------------------
# Append-only invariant: no log entry written on refusal
# ---------------------------------------------------------------------------


def test_duplicate_refusal_writes_no_log_entry(tmp_path: Path) -> None:
    """RefusedAsDuplicate must not append anything to proposals.jsonl."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    c = _make_candidate("cand-x", "entropy")
    propose_from_candidate(c, log=log, run_replay=_fake_replay_ok, cap=100)
    count_before = len(log.events())

    c_again = _make_candidate("cand-x", "entropy")
    result = propose_from_candidate(c_again, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(result, RefusedAsDuplicate)
    assert len(log.events()) == count_before


def test_dependent_refusal_writes_no_log_entry(tmp_path: Path) -> None:
    """RefusedAsDependent must not append anything to proposals.jsonl."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    _write_pending_proposal(log, "cand-A", "wave", "particle")
    count_before = len(log.events())

    c_b = _make_candidate("cand-B", "wave", "energy")
    result = propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)
    assert isinstance(result, RefusedAsDependent)
    assert len(log.events()) == count_before


# ---------------------------------------------------------------------------
# Determinism: same log + same candidate → same outcome
# ---------------------------------------------------------------------------


def test_determinism_duplicate_check(tmp_path: Path) -> None:
    """Duplicate check is deterministic: same inputs produce same outcome."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    c = _make_candidate("cand-det", "determinism")
    propose_from_candidate(c, log=log, run_replay=_fake_replay_ok, cap=100)

    results = []
    for _ in range(3):
        c_again = _make_candidate("cand-det", "determinism")
        results.append(
            propose_from_candidate(c_again, log=log, run_replay=_fake_replay_ok, cap=100)
        )
    assert all(isinstance(r, RefusedAsDuplicate) for r in results)
    assert len({r.proposal_id for r in results}) == 1


def test_determinism_dependency_check(tmp_path: Path) -> None:
    """Dependency check is deterministic: same log + same candidate → same outcome."""
    log = ProposalLog(tmp_path / "proposals.jsonl")
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    pid_a = _write_pending_proposal(log, "cand-A", "chaos", "order")

    results = []
    for i in range(3):
        c_b = _make_candidate(f"cand-B-{i}", "chaos", "clarity")
        results.append(
            propose_from_candidate(c_b, log=log, run_replay=_fake_replay_ok, cap=100)
        )
    assert all(isinstance(r, RefusedAsDependent) for r in results)
    assert all(pid_a in r.dependent_on for r in results)
