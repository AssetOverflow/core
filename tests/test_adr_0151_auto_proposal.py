from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from chat.runtime import ChatRuntime
from chat.teaching_grounding import _CORPUS_PATH
from core.config import RuntimeConfig
from engine_state import EngineStateStore
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalLog,
    ReplayEvidence,
    build_proposal,
    propose_from_candidate,
)
from teaching.source import ProposalSource


def _replay_equivalent(_chain: dict) -> ReplayEvidence:
    return ReplayEvidence(
        baseline={"intent_accuracy": 1.0},
        candidate={"intent_accuracy": 1.0},
        regressed_metrics=(),
        replay_equivalent=True,
    )


def _candidate(
    *,
    candidate_id: str = "cand-auto-1",
    polarity: str = "affirms",
    claim_domain: str = "factual",
    evidence: tuple[EvidencePointer, ...] | None = None,
) -> DiscoveryCandidate:
    if evidence is None:
        evidence = (
            EvidencePointer(
                source="corpus",
                ref="light_reveals_truth",
                polarity="affirms",
                epistemic_status="coherent",
            ),
        )
    return DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain={
            "subject": "light",
            "intent": "verification",
            "connective": "reveals",
            "object": "truth",
        },
        trigger="would_have_grounded",
        source_turn_trace="trace-auto-1",
        pack_consistent=True,
        boundary_clean=True,
        polarity=polarity,  # type: ignore[arg-type]
        claim_domain=claim_domain,  # type: ignore[arg-type]
        evidence=evidence,
        contemplation_depth=1,
    )


def _write_engine_state(path: Path, candidates: list[DiscoveryCandidate]) -> None:
    store = EngineStateStore(path)
    store.save_discovery_candidates(candidates)
    store.save_manifest(0)


def _install_proposal_log(monkeypatch, path: Path) -> Path:
    import teaching.proposals as proposals

    proposal_path = path / "proposals.jsonl"
    monkeypatch.setattr(proposals, "DEFAULT_PROPOSAL_LOG_PATH", proposal_path)
    monkeypatch.setattr(
        "teaching.replay.run_replay_equivalence",
        _replay_equivalent,
    )
    return proposal_path


def test_auto_proposal_off_does_not_generate_proposals(tmp_path: Path, monkeypatch) -> None:
    proposal_path = _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    _write_engine_state(state_path, [_candidate()])

    ChatRuntime(
        config=RuntimeConfig(auto_proposal_enabled=False),
        engine_state_path=state_path,
    )

    assert not proposal_path.exists()


def test_auto_proposal_generates_pending_proposal_from_enriched_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal_path = _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    candidate = _candidate()
    _write_engine_state(state_path, [candidate])

    ChatRuntime(
        config=RuntimeConfig(auto_proposal_enabled=True),
        engine_state_path=state_path,
    )

    proposal = build_proposal(candidate)
    record = ProposalLog(proposal_path).find(proposal.proposal_id)
    assert record is not None
    assert record["state"] == "pending"
    assert record["source"]["kind"] == "contemplation"


def test_unenriched_candidate_skipped_silently(tmp_path: Path, monkeypatch) -> None:
    proposal_path = _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    candidate = replace(_candidate(), polarity="undetermined", evidence=())
    _write_engine_state(state_path, [candidate])

    ChatRuntime(
        config=RuntimeConfig(auto_proposal_enabled=True),
        engine_state_path=state_path,
    )

    assert ProposalLog(proposal_path).current_state() == {}


def test_evaluative_candidate_skipped(tmp_path: Path, monkeypatch) -> None:
    proposal_path = _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    _write_engine_state(state_path, [_candidate(claim_domain="evaluative")])

    ChatRuntime(
        config=RuntimeConfig(auto_proposal_enabled=True),
        engine_state_path=state_path,
    )

    assert ProposalLog(proposal_path).current_state() == {}


def test_proposal_source_kind_is_contemplation(tmp_path: Path, monkeypatch) -> None:
    proposal_path = _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    candidate = _candidate(candidate_id="cand-source-1")
    _write_engine_state(state_path, [candidate])

    ChatRuntime(
        config=RuntimeConfig(auto_proposal_enabled=True),
        engine_state_path=state_path,
    )

    proposal = build_proposal(candidate)
    record = ProposalLog(proposal_path).find(proposal.proposal_id)
    assert record is not None
    assert record["source"]["kind"] == "contemplation"
    assert record["source"]["source_id"] == candidate.candidate_id


def test_propose_from_candidate_accepts_source_kwarg(tmp_path: Path) -> None:
    log = ProposalLog(tmp_path / "proposals.jsonl")
    source = ProposalSource(
        kind="contemplation",
        source_id="cand-direct-1",
        emitted_at_revision="test-revision",
    )

    proposal = propose_from_candidate(
        _candidate(candidate_id="cand-direct-1"),
        log=log,
        run_replay=_replay_equivalent,
        source=source,
    )

    record = log.find(proposal.proposal_id)
    assert record is not None
    assert record["source"] == source.as_dict()


def test_idempotent_reload_does_not_duplicate(tmp_path: Path, monkeypatch) -> None:
    proposal_path = _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    _write_engine_state(state_path, [_candidate()])

    config = RuntimeConfig(auto_proposal_enabled=True)
    ChatRuntime(config=config, engine_state_path=state_path)
    ChatRuntime(config=config, engine_state_path=state_path)

    created_events = [
        line
        for line in proposal_path.read_text(encoding="utf-8").splitlines()
        if '"event":"created"' in line
    ]
    assert len(created_events) == 1
    assert len(ProposalLog(proposal_path).current_state()) == 1


def test_auto_proposal_does_not_write_corpus(tmp_path: Path, monkeypatch) -> None:
    _install_proposal_log(monkeypatch, tmp_path)
    state_path = tmp_path / "engine_state"
    _write_engine_state(state_path, [_candidate()])
    before = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""

    ChatRuntime(
        config=RuntimeConfig(auto_proposal_enabled=True),
        engine_state_path=state_path,
    )

    after = _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""
    assert after == before
