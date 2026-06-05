"""Continuous learning in idle time — CL-1/2/3.

``ChatRuntime.idle_tick()`` advances the reviewed-learning flywheel BETWEEN turns
(no user input): it contemplates the pending discovery backlog and runs the
replay-gated, PROPOSAL-ONLY ``propose_from_candidate`` into a persistent proposal
log. The engine "learns while it lives", and that progress survives reboot.

Teaching safety (CLAUDE.md): an idle tick never ratifies. Raw cold-start
candidates are ``undetermined`` and the eligibility gate refuses them outright;
even a determined candidate only reaches ``pending`` — moving to ``accepted`` and
appending to the corpus stays HITL via ``teaching/review``. No idle tick ever
emits an ``accepted`` / ``accepted_corpus_append`` event.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from chat.runtime import ChatRuntime
from core.cognition.pipeline import CognitiveTurnPipeline
from core.config import RuntimeConfig
from teaching.discovery import EvidencePointer


def _drive_backlog(state_dir: Path) -> ChatRuntime:
    """Run cold-cause turns that emit (undetermined) discovery candidates."""
    runtime = ChatRuntime(config=RuntimeConfig(), engine_state_path=state_dir)
    pipe = CognitiveTurnPipeline(runtime=runtime)
    for subject in ("principle", "narrative", "judgment"):
        pipe.run(f"What causes {subject}?")
    return runtime


def _make_determined(candidate):
    """Promote a real discovery candidate to a fully-eligible, determined one."""
    chain = dict(candidate.proposed_chain)
    chain.update({"connective": "because", "object": "light"})
    return replace(
        candidate,
        proposed_chain=chain,
        polarity="affirms",
        boundary_clean=True,
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="en_core_cognition_v1:principle",
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )


def test_idle_tick_is_noop_on_empty_backlog(tmp_path: Path) -> None:
    rt = ChatRuntime(config=RuntimeConfig(), engine_state_path=tmp_path / "es")
    result = rt.idle_tick()
    assert result.candidates_contemplated == 0
    assert result.proposals_created == 0
    assert result.pending_proposals == 0


def test_idle_tick_contemplates_the_pending_backlog(tmp_path: Path) -> None:
    rt = _drive_backlog(tmp_path / "es")
    n_backlog = len(rt._pending_candidates)
    assert n_backlog >= 1  # cold-cause turns produced a backlog
    result = rt.idle_tick()
    assert result.candidates_contemplated == n_backlog


def test_idle_tick_refuses_undetermined_candidates(tmp_path: Path) -> None:
    # Cold-start candidates are undetermined: the engine has not decided whether
    # they are true, so it must NOT propose them.
    rt = _drive_backlog(tmp_path / "es")
    assert all(c.polarity == "undetermined" for c in rt._pending_candidates)
    result = rt.idle_tick()
    assert result.proposals_created == 0


def test_idle_tick_proposes_determined_candidate_but_never_ratifies(
    tmp_path: Path,
) -> None:
    rt = _drive_backlog(tmp_path / "es")
    # Inject a fully-determined, eligible candidate (as if the engine had
    # determined polarity through grounding/review).
    rt._pending_candidates = [_make_determined(rt._pending_candidates[0])]
    rt.idle_tick()

    assert rt._proposal_log is not None
    events = rt._proposal_log.events()
    # The proposal path was exercised, but NOTHING was ratified.
    assert not any(
        ev.get("event") == "transition" and ev.get("to") == "accepted" for ev in events
    )
    assert not any(ev.get("event") == "accepted_corpus_append" for ev in events)
    # Any proposal that exists is pending (HITL review not bypassed).
    state = rt._proposal_log.current_state()
    assert all(v.get("state") == "pending" for v in state.values())


def test_idle_learning_persists_across_reboot(tmp_path: Path) -> None:
    state_dir = tmp_path / "es"
    rt_a = _drive_backlog(state_dir)
    rt_a._pending_candidates = [_make_determined(rt_a._pending_candidates[0])]
    rt_a.idle_tick()
    pending_before = rt_a._count_pending_proposals()
    backlog_before = len(rt_a._pending_candidates)

    # Reboot: a fresh runtime over the same engine-state dir.
    rt_b = ChatRuntime(config=RuntimeConfig(), engine_state_path=state_dir)
    # The proposal log and the candidate backlog both survived.
    assert rt_b._count_pending_proposals() == pending_before
    assert len(rt_b._pending_candidates) == backlog_before
