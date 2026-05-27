"""ADR-0057 Phase C2 — TeachingChainProposal eligibility, replay-
equivalence gate, append-only proposal log, and operator review
state machine.

Pinned contracts:
  - Eligibility predicate raises on every failing gate.
  - Idempotent proposal_id derivation.
  - Replay-equivalence gate never mutates the active corpus.
  - Regression auto-transitions proposal to rejected.
  - --accept only legal when state==pending AND replay_equivalent.
  - Append-only log: replaying the log reconstructs the same state.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from chat.teaching_grounding import _CORPUS_PATH
from teaching.discovery import (
    DiscoveryCandidate,
    EvidencePointer,
)
from teaching.proposals import (
    ProposalError,
    ProposalLog,
    ReplayEvidence,
    accept_proposal,
    append_chain_to_corpus,
    build_proposal,
    check_eligibility,
    propose_from_candidate,
    reject_proposal,
    withdraw_proposal,
)
from teaching.provenance import Provenance


CORPUS_BYTES_BEFORE = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""


def _enriched(*, polarity="affirms", claim_domain="factual",
              connective="reveals", obj="truth", subject="light",
              evidence=None, boundary_clean=True, domain="cognition"):
    if evidence is None:
        evidence = (
            EvidencePointer(
                source="corpus", ref="some_chain",
                polarity=polarity, epistemic_status="coherent",
            ),
        )
    return DiscoveryCandidate(
        candidate_id="cand_xyz",
        proposed_chain={
            "subject": subject, "intent": "cause",
            "connective": connective, "object": obj,
        },
        trigger="would_have_grounded",
        source_turn_trace="trace_1",
        pack_consistent=True,
        boundary_clean=boundary_clean,
        domain=domain,
        polarity=polarity,
        claim_domain=claim_domain,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Eligibility gates
# ---------------------------------------------------------------------------


def test_undetermined_polarity_rejected():
    c = _enriched()
    bad = replace(c, polarity="undetermined")
    with pytest.raises(ProposalError, match="polarity"):
        check_eligibility(bad)


def test_missing_corpus_evidence_rejected():
    c = _enriched(evidence=(
        EvidencePointer(
            source="pack", ref="light",
            polarity="affirms", epistemic_status="coherent",
        ),
    ))
    with pytest.raises(ProposalError, match="corpus"):
        check_eligibility(c)


def test_evaluative_requires_explicit_flag():
    c = _enriched(claim_domain="evaluative")
    with pytest.raises(ProposalError, match="evaluative"):
        check_eligibility(c)
    check_eligibility(c, allow_evaluative=True)  # no raise


def test_boundary_unclean_rejected():
    c = _enriched(boundary_clean=False)
    with pytest.raises(ProposalError, match="boundary"):
        check_eligibility(c)


def test_incomplete_chain_rejected():
    base = _enriched()
    incomplete = replace(base, proposed_chain={
        "subject": "light", "intent": "cause",
        "connective": None, "object": None,
    })
    with pytest.raises(ProposalError, match="subject/intent/connective/object"):
        check_eligibility(incomplete)


# ---------------------------------------------------------------------------
# Proposal id idempotency
# ---------------------------------------------------------------------------


def test_proposal_id_is_deterministic():
    c = _enriched()
    p1 = build_proposal(c)
    p2 = build_proposal(c)
    assert p1.proposal_id == p2.proposal_id


# ---------------------------------------------------------------------------
# Append-only log
# ---------------------------------------------------------------------------


def test_log_append_only_state_machine(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    c = _enriched()
    p = build_proposal(c)
    log.record_created(p)
    assert log.find(p.proposal_id)["state"] == "pending"

    log.record_transition(p.proposal_id, "rejected", "test note")
    assert log.find(p.proposal_id)["state"] == "rejected"

    # File is append-only: byte-count grows monotonically.
    size_a = (tmp_path / "proposals.jsonl").stat().st_size
    log.record_transition(p.proposal_id, "withdrawn", "no-op test")
    size_b = (tmp_path / "proposals.jsonl").stat().st_size
    assert size_b > size_a


# ---------------------------------------------------------------------------
# Replay gate (with fake replay to avoid running cognition lane)
# ---------------------------------------------------------------------------


def _fake_replay_equivalent(chain):
    return ReplayEvidence(
        baseline={"intent_accuracy": 1.0, "surface_groundedness": 1.0},
        candidate={"intent_accuracy": 1.0, "surface_groundedness": 1.0},
        regressed_metrics=(),
        replay_equivalent=True,
    )


def _fake_replay_regression(chain):
    return ReplayEvidence(
        baseline={"intent_accuracy": 1.0, "surface_groundedness": 1.0},
        candidate={"intent_accuracy": 1.0, "surface_groundedness": 0.85},
        regressed_metrics=("surface_groundedness",),
        replay_equivalent=False,
    )


def test_propose_from_candidate_pending_on_equivalent(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    c = _enriched()
    proposal = propose_from_candidate(c, log=log, run_replay=_fake_replay_equivalent)
    rec = log.find(proposal.proposal_id)
    assert rec["state"] == "pending"
    assert rec["replay_evidence"]["replay_equivalent"] is True


def test_propose_from_candidate_auto_rejects_on_regression(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    c = _enriched()
    proposal = propose_from_candidate(c, log=log, run_replay=_fake_replay_regression)
    rec = log.find(proposal.proposal_id)
    assert rec["state"] == "rejected"
    assert "auto_rollback_regression" in rec["operator_note"]
    assert "surface_groundedness" in rec["operator_note"]


def test_propose_selects_replay_gate_by_candidate_domain(monkeypatch, tmp_path: Path):
    calls: list[str] = []

    def fake_cognition_gate(chain):
        calls.append("cognition")
        return _fake_replay_equivalent(chain)

    def fake_math_gate(chain):
        calls.append("math")
        return _fake_replay_equivalent(chain)

    monkeypatch.setattr(
        "teaching.replay.run_replay_equivalence",
        fake_cognition_gate,
    )
    monkeypatch.setattr(
        "teaching.replay.run_admissibility_replay_gate",
        fake_math_gate,
    )

    log_cognition = ProposalLog(tmp_path / "cognition" / "proposals.jsonl")
    propose_from_candidate(_enriched(domain="cognition"), log=log_cognition)

    log_math = ProposalLog(tmp_path / "math" / "proposals.jsonl")
    propose_from_candidate(
        _enriched(domain="math", subject="sees", connective="recognizes", obj="drain"),
        log=log_math,
    )

    assert calls == ["cognition", "math"]


def test_explicit_replay_override_wins_over_domain(monkeypatch, tmp_path: Path):
    calls: list[str] = []

    def forbidden_math_gate(chain):
        raise AssertionError("domain-selected math gate should not run")

    def override_gate(chain):
        calls.append("override")
        return _fake_replay_equivalent(chain)

    monkeypatch.setattr(
        "teaching.replay.run_admissibility_replay_gate",
        forbidden_math_gate,
    )

    log = ProposalLog(tmp_path / "proposals.jsonl")
    propose_from_candidate(
        _enriched(domain="math", subject="sees", connective="recognizes", obj="drain"),
        log=log,
        run_replay=override_gate,
    )

    assert calls == ["override"]


def test_propose_is_idempotent(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    c = _enriched()
    propose_from_candidate(c, log=log, run_replay=_fake_replay_equivalent)
    size_a = (tmp_path / "proposals.jsonl").stat().st_size
    propose_from_candidate(c, log=log, run_replay=_fake_replay_equivalent)
    size_b = (tmp_path / "proposals.jsonl").stat().st_size
    # Idempotency: second proposal is a no-op; log size unchanged.
    assert size_a == size_b


# ---------------------------------------------------------------------------
# Accept / reject / withdraw state machine
# ---------------------------------------------------------------------------


def test_accept_appends_to_corpus(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")
    c = _enriched()
    proposal = propose_from_candidate(c, log=log, run_replay=_fake_replay_equivalent)

    chain_id = accept_proposal(
        proposal.proposal_id,
        log=log,
        corpus_path=corpus,
        review_date="2026-05-18",
        operator_note="looks good",
    )
    assert chain_id

    lines = [ln for ln in corpus.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["subject"] == "light"
    assert payload["connective"] == "reveals"
    assert "discovery_promoted" in payload["provenance"]

    rec = log.find(proposal.proposal_id)
    assert rec["state"] == "accepted"
    assert rec["accepted_chain_id"] == chain_id


def test_accept_refused_on_regression(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")
    c = _enriched()
    proposal = propose_from_candidate(c, log=log, run_replay=_fake_replay_regression)
    with pytest.raises(ProposalError):
        accept_proposal(
            proposal.proposal_id, log=log,
            corpus_path=corpus, review_date="2026-05-18",
        )


def test_reject_and_withdraw_transitions(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    c = _enriched()
    p1 = propose_from_candidate(c, log=log, run_replay=_fake_replay_equivalent)
    reject_proposal(p1.proposal_id, log=log, operator_note="off doctrine")
    assert log.find(p1.proposal_id)["state"] == "rejected"

    # Cannot transition from rejected.
    with pytest.raises(ProposalError):
        withdraw_proposal(p1.proposal_id, log=log)


def test_accept_idempotency_blocked_by_state_machine(tmp_path: Path):
    log = ProposalLog(tmp_path / "proposals.jsonl")
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("", encoding="utf-8")
    c = _enriched()
    proposal = propose_from_candidate(c, log=log, run_replay=_fake_replay_equivalent)
    accept_proposal(
        proposal.proposal_id, log=log,
        corpus_path=corpus, review_date="2026-05-18",
    )
    with pytest.raises(ProposalError):
        accept_proposal(
            proposal.proposal_id, log=log,
            corpus_path=corpus, review_date="2026-05-18",
        )


# ---------------------------------------------------------------------------
# Trust boundary: replay gate does not touch active corpus
# ---------------------------------------------------------------------------


def test_replay_gate_does_not_mutate_active_corpus():
    """The real replay-equivalence gate runs the cognition lane;
    that's slow, so this test runs it once and asserts byte-equality
    on the active corpus.  Marked separately so the rest of the
    suite stays fast."""
    from teaching.replay import run_replay_equivalence

    chain = {
        "subject": "judgment", "intent": "verification",
        "connective": "requires", "object": "evidence",
    }
    before = _CORPUS_PATH.read_bytes()
    evidence = run_replay_equivalence(chain)
    after = _CORPUS_PATH.read_bytes()
    assert before == after
    assert isinstance(evidence.replay_equivalent, bool)


# ---------------------------------------------------------------------------
# append_chain_to_corpus — direct unit
# ---------------------------------------------------------------------------


def test_append_chain_writes_one_line(tmp_path: Path):
    corpus = tmp_path / "c.jsonl"
    corpus.write_text("", encoding="utf-8")
    prov = Provenance(
        adr_id="adr-0057", source="discovery_promoted",
        review_date="2026-05-18", raw="adr-0057:discovery_promoted:2026-05-18",
    )
    chain_id = append_chain_to_corpus(
        {"subject": "knowledge", "intent": "cause",
         "connective": "requires", "object": "evidence"},
        corpus_path=corpus, provenance=prov,
    )
    payload = json.loads(corpus.read_text().splitlines()[0])
    assert payload["chain_id"] == chain_id
    assert payload["provenance"] == prov.raw
