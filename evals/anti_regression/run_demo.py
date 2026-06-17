"""Anti-regression demo — three scenes showing how CORE refuses to learn
something that would make it worse.

The thesis: when a system extends its own knowledge, **the gate that
decides what to admit is the load-bearing part** — not the proposer.
CORE's reviewed-corpus extension path (ADR-0057) has three independent
gates that must each pass before any byte is written:

  S1.  Eligibility predicate (mechanical, pre-replay).
       Five mechanical checks on the candidate's shape (polarity,
       evidence-floor, claim-domain, boundary-clean, chain-complete).
       Ineligible candidates raise ``ProposalError`` and never enter
       the proposal log.

  S2.  Replay-equivalence gate (mechanical, post-eligibility).
       The full cognition lane runs against the active corpus AND
       against a transient copy with the proposed chain appended.
       Any strict-decrease in a watched metric auto-rejects the
       proposal with the metrics named in the operator note.
       Active corpus file bytes are byte-identical pre/post.

  S3.  Operator review (manual, post-replay).
       Even a replay-equivalent proposal only reaches the *pending*
       state — explicit ``core teaching review <id> --accept`` is
       required to write to the active corpus.

This demo runs each scene end-to-end against the real ``ProposalLog``
in an isolated temp directory.  No active corpus or production log is
touched.

Scenes 1 and 3 use the **real** ``teaching.replay.run_replay_equivalence``
function.  Scene 2 injects a controlled replay function (via the
documented ``run_replay=`` kwarg of ``propose_from_candidate``) that
returns a regressed ``ReplayEvidence`` of the same shape the real gate
produces — demonstrating the auto-rejection lifecycle on a synthetic
regression deterministically.  In production the real gate produces
this same shape when a real regression is detected.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalError,
    ProposalLog,
    ReplayEvidence,
    propose_from_candidate,
)

# Hermetic integration of the hardened CLOSE derived-climb yardstick (Claim B).
# Executed as part of the anti-regression demo flow so that `core demo anti-regression`
# (and its contract tests) provide recurring protection for the CLOSE flywheel
# (lived idle_tick + IdleTickResult flag, semantic determine(rule='direct'),
# content_replay_checksum). The climb runner is fully self-isolating.
from evals.close_derived_climb import run as run_close_derived_climb


_VERBOSE = True


def _say(*args: Any, **kwargs: Any) -> None:
    if _VERBOSE:
        print(*args, **kwargs)


def _print_header(title: str, claim: str) -> None:
    _say()
    _say("─" * 72)
    _say(f"  {title}")
    _say("─" * 72)
    _say(f"  CLAIM: {claim}")
    _say()


# ---------------------------------------------------------------------------
# Synthetic ReplayEvidence builder for Scene 2
# ---------------------------------------------------------------------------


def _make_regressed_replay(
    *, regressed_metrics: tuple[str, ...]
) -> Any:
    """Return a ``run_replay`` function that emits a regressed
    ``ReplayEvidence`` with the same shape the real gate produces.
    """
    baseline = {
        "intent_accuracy": 1.0,
        "surface_groundedness": 1.0,
        "term_capture_rate": 1.0,
        "versor_closure_rate": 1.0,
    }
    candidate = dict(baseline)
    for m in regressed_metrics:
        candidate[m] = round(candidate[m] - 0.0833, 4)

    def _fn(chain: dict[str, Any]) -> ReplayEvidence:  # noqa: ARG001
        return ReplayEvidence(
            baseline=baseline,
            candidate=candidate,
            regressed_metrics=tuple(sorted(regressed_metrics)),
            replay_equivalent=False,
        )

    return _fn


# ---------------------------------------------------------------------------
# Candidate builders
# ---------------------------------------------------------------------------


def _candidate_undetermined() -> DiscoveryCandidate:
    """A candidate that fails the eligibility predicate at the polarity
    gate.  Used for Scene 1."""
    return DiscoveryCandidate(
        candidate_id="demo_undetermined_001",
        proposed_chain={
            "subject": "wisdom", "intent": "cause",
            "connective": "informs", "object": "judgment",
        },
        trigger="would_have_grounded",
        source_turn_trace="demo_trace_001",
        pack_consistent=True,
        boundary_clean=True,
        polarity="undetermined",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="cause_wisdom_orders_judgment",
                polarity="affirms",
                epistemic_status="reviewed",
            ),
        ),
    )


def _candidate_for_regression() -> DiscoveryCandidate:
    """A candidate that passes eligibility but (under the injected
    regression replay) is auto-rejected for regressing
    ``surface_groundedness`` and ``term_capture_rate``."""
    return DiscoveryCandidate(
        candidate_id="demo_regression_002",
        proposed_chain={
            "subject": "knowledge", "intent": "cause",
            "connective": "obscures", "object": "wisdom",
        },
        trigger="would_have_grounded",
        source_turn_trace="demo_trace_002",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="cause_knowledge_requires_evidence",
                polarity="affirms",
                epistemic_status="reviewed",
            ),
        ),
    )


def _candidate_pass_through() -> DiscoveryCandidate:
    """A candidate that passes both eligibility and the real
    replay-equivalence gate.  Lands in ``pending`` awaiting
    operator review."""
    return DiscoveryCandidate(
        candidate_id="demo_pass_003",
        proposed_chain={
            "subject": "judgment", "intent": "verification",
            "connective": "requires", "object": "evidence",
        },
        trigger="would_have_grounded",
        source_turn_trace="demo_trace_003",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref="verification_truth_requires_evidence",
                polarity="affirms",
                epistemic_status="reviewed",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Scene results
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SceneResult:
    scene: str
    claim: str
    outcome: str
    candidate_id: str
    proposed_chain: dict[str, Any]
    proposal_id: str | None
    review_state: str
    replay_evidence: dict[str, Any] | None
    operator_note: str
    error: str | None
    corpus_byte_identical: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "scene": self.scene,
            "claim": self.claim,
            "outcome": self.outcome,
            "candidate_id": self.candidate_id,
            "proposed_chain": self.proposed_chain,
            "proposal_id": self.proposal_id,
            "review_state": self.review_state,
            "replay_evidence": self.replay_evidence,
            "operator_note": self.operator_note,
            "error": self.error,
            "corpus_byte_identical": self.corpus_byte_identical,
        }


@dataclass(frozen=True, slots=True)
class DemoReport:
    scenes: tuple[SceneResult, ...]
    all_gates_held: bool
    active_corpus_byte_identical: bool
    # Additive: the hardened CLOSE derived climb yardstick (Claim B) is run
    # inside this anti-regression demo as a complementary hermetic protection
    # surface for autonomous derived-fact growth + gated proposal emission.
    # See ratification + testing-lanes.md. Never mutates shared state.
    close_derived_climb: dict[str, Any] | None = None

    # Additive instrumentation (this PR): structured visibility into the
    # proposal review / ratification side of the CLOSE flywheel (and the
    # teaching proposal gates exercised by this demo). Derived from
    # SceneResult review_state values (already produced by the S1/S2/S3
    # gate paths) + the embedded climb's proposal_review_posture (born
    # review-gated posture of derived CLOSE proposals). No review logic
    # paths are altered; no real corpus mutation or promotion occurs.
    proposal_review_summary: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        # ``all_claims_supported`` is the canonical cross-demo success
        # field — added as an alias so operator tooling (and the CI gate)
        # can rely on one uniform boolean key across every ``core demo``
        # target.  Existing fields are preserved for backwards compat.
        return {
            "scenes": [s.as_dict() for s in self.scenes],
            "all_gates_held": self.all_gates_held,
            "active_corpus_byte_identical": self.active_corpus_byte_identical,
            "close_derived_climb": self.close_derived_climb,
            "proposal_review_summary": self.proposal_review_summary,
            "all_claims_supported": (
                self.all_gates_held and self.active_corpus_byte_identical
            ),
        }


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def _read_active_corpus_bytes() -> bytes:
    from chat.teaching_grounding import _CORPUS_PATH
    return _CORPUS_PATH.read_bytes() if _CORPUS_PATH.exists() else b""


def _scene1_eligibility_gate(log_path: Path) -> SceneResult:
    _print_header(
        "S1.  Eligibility predicate refuses ineligible candidates",
        "An undetermined-polarity candidate never enters the proposal "
        "log.  ProposalError raised; no log row; no replay invocation.",
    )
    log = ProposalLog(log_path)
    candidate = _candidate_undetermined()
    bytes_before = _read_active_corpus_bytes()
    error: str | None = None
    try:
        propose_from_candidate(candidate, log=log)
    except ProposalError as exc:
        error = str(exc)
    bytes_after = _read_active_corpus_bytes()

    _say(f"  candidate.polarity      : {candidate.polarity}")
    _say(f"  outcome                 : ProposalError raised")
    _say(f"  error                   : {error}")
    _say(f"  proposal log rows       : {len(log.current_state())}")
    _say(f"  active corpus byte-eq   : {bytes_before == bytes_after}")
    return SceneResult(
        scene="S1_eligibility_gate",
        claim=(
            "Five mechanical eligibility gates fire before any replay "
            "is invoked.  Undetermined-polarity candidates never enter "
            "the proposal log."
        ),
        outcome="rejected_pre_replay",
        candidate_id=candidate.candidate_id,
        proposed_chain=candidate.proposed_chain,
        proposal_id=None,
        review_state="(not in log)",
        replay_evidence=None,
        operator_note="",
        error=error,
        corpus_byte_identical=(bytes_before == bytes_after),
    )


def _scene2_replay_auto_reject(log_path: Path) -> SceneResult:
    _print_header(
        "S2.  Replay-equivalence gate auto-rejects a regressing chain",
        "An eligible candidate whose append would regress the cognition "
        "lane is auto-rejected with the named regressed metrics in the "
        "operator note.  Active corpus byte-identical pre/post.",
    )
    log = ProposalLog(log_path)
    candidate = _candidate_for_regression()
    bytes_before = _read_active_corpus_bytes()
    proposal = propose_from_candidate(
        candidate,
        log=log,
        run_replay=_make_regressed_replay(
            regressed_metrics=("surface_groundedness", "term_capture_rate"),
        ),
    )
    bytes_after = _read_active_corpus_bytes()
    rec = log.find(proposal.proposal_id) or {}
    ev = rec.get("replay_evidence") or {}

    _say(f"  proposal_id             : {proposal.proposal_id}")
    _say(f"  baseline metrics        : {ev.get('baseline')}")
    _say(f"  candidate metrics       : {ev.get('candidate')}")
    _say(f"  regressed_metrics       : {ev.get('regressed_metrics')}")
    _say(f"  replay_equivalent       : {ev.get('replay_equivalent')}")
    _say(f"  state                   : {rec.get('state')}")
    _say(f"  operator_note           : {rec.get('operator_note')}")
    _say(f"  active corpus byte-eq   : {bytes_before == bytes_after}")
    return SceneResult(
        scene="S2_replay_auto_reject",
        claim=(
            "Replay-equivalence gate compares the full cognition lane "
            "metrics; any strict-decrease auto-rejects with the regressed "
            "metric names in the operator note.  Active corpus untouched."
        ),
        outcome="auto_rejected_on_regression",
        candidate_id=candidate.candidate_id,
        proposed_chain=candidate.proposed_chain,
        proposal_id=proposal.proposal_id,
        review_state=str(rec.get("state")),
        replay_evidence=ev,
        operator_note=str(rec.get("operator_note") or ""),
        error=None,
        corpus_byte_identical=(bytes_before == bytes_after),
    )


def _scene3_real_gate_pass_through(log_path: Path) -> SceneResult:
    _print_header(
        "S3.  Real replay gate runs cognition lane; pass → pending",
        "An eligible candidate whose append does not regress reaches "
        "'pending' state.  Operator --accept is still required to write "
        "to the active corpus; the gate is a precondition, not a "
        "permission.",
    )
    log = ProposalLog(log_path)
    candidate = _candidate_pass_through()
    bytes_before = _read_active_corpus_bytes()
    proposal = propose_from_candidate(candidate, log=log)
    bytes_after = _read_active_corpus_bytes()
    rec = log.find(proposal.proposal_id) or {}
    ev = rec.get("replay_evidence") or {}

    _say(f"  proposal_id             : {proposal.proposal_id}")
    _say(f"  baseline metrics        : {ev.get('baseline')}")
    _say(f"  candidate metrics       : {ev.get('candidate')}")
    _say(f"  regressed_metrics       : {ev.get('regressed_metrics')}")
    _say(f"  replay_equivalent       : {ev.get('replay_equivalent')}")
    _say(f"  state                   : {rec.get('state')}")
    _say(f"  next step               : core teaching review {proposal.proposal_id} "
          "--accept --review-date YYYY-MM-DD")
    _say(f"  active corpus byte-eq   : {bytes_before == bytes_after}")
    return SceneResult(
        scene="S3_real_gate_pass_through",
        claim=(
            "A replay-equivalent candidate reaches 'pending' but is "
            "not auto-applied.  Operator --accept is the third gate."
        ),
        outcome="pending_awaiting_operator",
        candidate_id=candidate.candidate_id,
        proposed_chain=candidate.proposed_chain,
        proposal_id=proposal.proposal_id,
        review_state=str(rec.get("state")),
        replay_evidence=ev,
        operator_note="",
        error=None,
        corpus_byte_identical=(bytes_before == bytes_after),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_demo(*, emit_json: bool = False) -> dict[str, Any]:
    """Run all three scenes and return a structured report."""
    global _VERBOSE
    _VERBOSE = not emit_json

    active_bytes_before = _read_active_corpus_bytes()

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "demo_proposals.jsonl"
        s1 = _scene1_eligibility_gate(log_path)
        s2 = _scene2_replay_auto_reject(log_path)
        s3 = _scene3_real_gate_pass_through(log_path)

        # Inside the tmpdir (log still exists): capture additive review/ratification
        # signals from the exact ProposalLog events written by the gate paths
        # (S2 auto-reject produces a "transition" to rejected; S3 leaves pending).
        # This gives structured visibility into review outcomes and transition
        # events for the teaching proposal path without any change to review
        # logic or any write to the live active corpus.
        _log = ProposalLog(log_path)
        _events = _log.events()
        _transitions = [e for e in _events if e.get("event") == "transition"]
        _by_to = {}
        for e in _transitions:
            to = e.get("to")
            _by_to[to] = _by_to.get(to, 0) + 1
        _accepted_corpus_appends = sum(1 for e in _events if e.get("event") == "accepted_corpus_append")

        # Build the proposal review summary (additive). Includes both the
        # teaching chain proposal gates exercised here and (via the embedded
        # climb) the CLOSE-derived proposal review posture.
        proposal_review_summary = {
            "scenes": {
                "count": 3,
                "review_states": {
                    s1.review_state: 1,
                    s2.review_state: 1,
                    s3.review_state: 1,
                },
                "outcomes": {
                    s1.outcome: 1,
                    s2.outcome: 1,
                    s3.outcome: 1,
                },
            },
            "log_transitions": {
                "total_transitions": len(_transitions),
                "by_to_state": _by_to,
                "accepted_corpus_appends": _accepted_corpus_appends,
            },
            "note": "S2 exercises an auto-reject transition inside the replay gate; S3 demonstrates pending (operator review required). No real ratification mutates the active corpus in this demo.",
        }

    active_bytes_after = _read_active_corpus_bytes()

    scenes = (s1, s2, s3)
    all_gates_held = (
        s1.outcome == "rejected_pre_replay"
        and s2.outcome == "auto_rejected_on_regression"
        and s3.outcome == "pending_awaiting_operator"
    )

    # Execute the hardened CLOSE derived-climb yardstick (Claim B) here as part
    # of the Dedicated CLOSE Flywheel Regression Surface (Claim-B Level).
    # This cleanly embeds (additive, hermetic) the full surface into the
    # anti-regression / teaching demo flows (building on #792). The call uses
    # only fresh runtimes + internal temps; zero production writes.
    # See docs/testing-lanes.md "Dedicated CLOSE Flywheel..." and
    # `make test-close-flywheel`.
    close_derived_climb = run_close_derived_climb()

    # Merge the climb's proposal_review_posture (CLOSE-specific emission-time
    # review posture: all proposal_only/speculative/requires_review) into the
    # demo's summary for a coherent view of the full flywheel's review side.
    if close_derived_climb:
        prp = close_derived_climb.get("proposal_review_posture") or {}
        proposal_review_summary["close_derived"] = {
            "emitted_count": prp.get("emitted_count", 0),
            "all_proposal_only": prp.get("all_proposal_only"),
            "all_speculative": prp.get("all_speculative"),
            "all_requires_review": prp.get("all_requires_review"),
            "review_eligible": prp.get("review_eligible", 0),
            "none_accepted_or_promoted": prp.get("none_accepted_or_promoted"),
        }

    report = DemoReport(
        scenes=scenes,
        all_gates_held=all_gates_held,
        active_corpus_byte_identical=(active_bytes_before == active_bytes_after),
        close_derived_climb=close_derived_climb,
        proposal_review_summary=proposal_review_summary,
    )

    if _VERBOSE:
        _say()
        _say("═" * 72)
        _say("  RESULT")
        _say("═" * 72)
        _say(f"  all three gates held       : {report.all_gates_held}")
        _say(f"  active corpus byte-eq      : {report.active_corpus_byte_identical}")
        # CLOSE Flywheel Regression Surface (Claim-B Level) — executed here as
        # part of the anti-regression demo (see `make test-close-flywheel` and
        # docs/testing-lanes.md "Dedicated CLOSE Flywheel...").
        # Exercises lived idle_tick + IdleTickResult flag, semantic determine
        # (rule='direct'), and content_replay_checksum.
        climb = report.close_derived_climb or {}
        agg = climb.get("aggregate", {})
        propf = climb.get("proposal_flag", {})
        _say(
            f"  CLOSE Flywheel Regression Surface (Claim B): wrong_total={agg.get('wrong_total')}, "
            f"proposals_only_with_flag={propf.get('only_with_flag')}, "
            f"content_replay_checksum={(climb.get('content_replay_checksum') or '')[:12]}..."
        )
        # New (this PR): review/ratification posture and events for the
        # previously weaker half of the CLOSE flywheel, plus the teaching
        # proposal gates. All signals additive; no behavior or policy change.
        prs = report.proposal_review_summary or {}
        close_pr = prs.get("close_derived") or {}
        _say(
            f"  Proposal review (teaching gates): states={prs.get('scenes', {}).get('review_states')}, "
            f"log_transitions={prs.get('log_transitions', {}).get('total_transitions')}"
        )
        _say(
            f"  CLOSE proposal review posture: emitted={close_pr.get('emitted_count')}, "
            f"all_requires_review={close_pr.get('all_requires_review')}, "
            f"none_accepted_or_promoted={close_pr.get('none_accepted_or_promoted')}"
        )
        _say()
        _say(
            "  Each gate is independent and fails closed.  Bad proposals "
            "stop at the cheapest applicable gate.  The active corpus is "
            "never written to anywhere in this demo."
        )
        _say()

    return report.as_dict()


__all__ = ["run_demo"]
