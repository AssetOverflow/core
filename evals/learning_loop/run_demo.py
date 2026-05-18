"""Learning-loop demo — CORE learning a new chain from a cold turn.

The thesis (the demo's headline claim):

  > CORE, asked a question it cannot ground, emits structured evidence
  > that a reviewed chain would have helped.  An operator authors a
  > proposal from that evidence.  The replay-equivalence gate confirms
  > the chain would not regress the cognition lane.  The operator
  > accepts.  The **same prompt now produces a deterministic
  > teaching-grounded surface** — and CORE will produce that same
  > surface for that prompt every time, replayably, with full
  > provenance back to the operator's accept.

No LLM provider has this loop.  Continuous pre-training is the
nearest analog and is fundamentally different: opaque gradient
updates over uncurated data without per-fact provenance, without
operator review, without a replay-equivalence gate, without an
audit trail that lets you ask "why did the model say this today
that it would not have said yesterday?"

Five scenes, each on a real ``ChatRuntime`` against the live active
corpus.  The active corpus file bytes are byte-identical pre/post —
the demo writes only to a transient corpus, then swaps ``_CORPUS_PATH``
to that transient for the "after" turn.  The same swap pattern the
replay-equivalence gate uses (``teaching.replay._swap_corpus_path``).

  S1.  Cold turn.  The runtime cannot ground the prompt.
  S2.  Discovery emission.  A ``DiscoveryCandidate`` is emitted to the
       attached sink — structured evidence, not a mutation.
  S3.  Operator-authored proposal.  A complete proposal is built from
       the candidate's structure plus operator-provided connective /
       object / corpus-evidence pointer.  The replay-equivalence gate
       runs (real ``teaching.replay.run_replay_equivalence``) and
       confirms no regression.
  S4.  Operator accept against a *transient* corpus.  The active corpus
       on disk is untouched; the accepted chain is written to a tmp
       file.  Audit + runtime both honour the transient corpus.
  S5.  Same prompt, now teaching-grounded.  The deterministic
       teaching-grounded surface contains the new chain's subject /
       connective / object.  Identical for any replay of the same
       prompt against the same corpus state.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chat import teaching_grounding as _tg
from chat.runtime import ChatRuntime
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalLog,
    accept_proposal,
    propose_from_candidate,
)


# The single prompt that drives every scene.  CAUSE intent, subject
# ``narrative`` — pack-resident lemma but no ``(narrative, cause)``
# chain in the active corpus today, guaranteeing the cold-turn path.
#
# History: the original demo used ``thought`` as the cold subject; the
# cognition saturation v2 curriculum unit (commit ``a0edbb4``) added
# ``cause_thought_reveals_meaning`` to the active corpus, so the
# (thought, cause) cell is no longer cold.  ``narrative`` is the new
# cold exemplar — same thematic shape, same connective + object.
_DEMO_PROMPT: str = "Why does narrative exist?"
_DEMO_SUBJECT: str = "narrative"

# Operator-authored proposal payload.  The (narrative, cause) cell is
# unoccupied; the operator proposes the chain
#   narrative reveals meaning
# affirming evidence is the existing corpus chain
#   cause_creation_reveals_meaning   (creation reveals meaning)
# both endpoints are pack-resident.
_OPERATOR_CONNECTIVE: str = "reveals"
_OPERATOR_OBJECT: str = "meaning"
_OPERATOR_EVIDENCE_REF: str = "cause_creation_reveals_meaning"


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
# Sinks + helpers
# ---------------------------------------------------------------------------


class _BufferSink:
    """Discovery candidate sink that retains every emitted line."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def emit(self, line: str) -> None:
        self.lines.append(line)


def _active_bytes() -> bytes:
    return _tg._CORPUS_PATH.read_bytes() if _tg._CORPUS_PATH.exists() else b""


# ---------------------------------------------------------------------------
# Scene outputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SceneResult:
    scene: str
    claim: str
    detail: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"scene": self.scene, "claim": self.claim, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class DemoReport:
    prompt: str
    before_surface: str
    before_grounding_source: str
    after_surface: str
    after_grounding_source: str
    scenes: tuple[SceneResult, ...]
    learning_loop_closed: bool
    active_corpus_byte_identical: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "before": {
                "surface": self.before_surface,
                "grounding_source": self.before_grounding_source,
            },
            "after": {
                "surface": self.after_surface,
                "grounding_source": self.after_grounding_source,
            },
            "scenes": [s.as_dict() for s in self.scenes],
            "learning_loop_closed": self.learning_loop_closed,
            "active_corpus_byte_identical": self.active_corpus_byte_identical,
        }


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def _scene1_cold_turn(rt: ChatRuntime, sink: _BufferSink) -> tuple[SceneResult, Any]:
    _print_header(
        "S1.  Cold turn — runtime cannot ground the prompt",
        "Active corpus has no (thought, cause) chain.  The runtime "
        "falls through to the universal insufficient-grounding "
        "disclosure.  Identity / safety / ethics gates still run.",
    )
    response = rt.chat(_DEMO_PROMPT)
    _say(f"  prompt                  : {_DEMO_PROMPT}")
    _say(f"  surface                 : {response.surface}")
    _say(f"  grounding_source        : {response.grounding_source}")
    _say(f"  discovery candidates    : {len(sink.lines)}  (emitted post-turn)")
    return SceneResult(
        scene="S1_cold_turn",
        claim="No teaching chain for (thought, cause) — runtime returns the disclosure.",
        detail={
            "prompt": _DEMO_PROMPT,
            "surface": response.surface,
            "grounding_source": response.grounding_source,
            "discovery_candidates_emitted": len(sink.lines),
        },
    ), response


def _scene2_discovery_emission(sink: _BufferSink) -> tuple[SceneResult, dict[str, Any]]:
    _print_header(
        "S2.  Discovery candidate — structured evidence, not a mutation",
        "The runtime emits a DiscoveryCandidate (ADR-0055 Phase B) "
        "documenting that a reviewed (thought, cause) chain WOULD have "
        "grounded this turn.  Contemplation (ADR-0056 Phase C1) "
        "enriches with pack/corpus evidence pointers.  Active corpus "
        "is byte-identical — emission writes to the sink only.",
    )
    if not sink.lines:
        raise RuntimeError("expected at least one discovery candidate from S1")
    import json as _json
    payload = _json.loads(sink.lines[0])
    _say(f"  candidate_id            : {payload['candidate_id'][:16]}…")
    _say(f"  trigger                 : {payload['trigger']}")
    _say(f"  proposed_chain          : {payload['proposed_chain']}")
    _say(f"  polarity                : {payload['polarity']}")
    _say(f"  claim_domain            : {payload['claim_domain']}")
    _say(f"  pack_consistent         : {payload['pack_consistent']}")
    _say(f"  boundary_clean          : {payload['boundary_clean']}")
    _say(f"  evidence (pack-only)    : "
         f"{[e for e in payload['evidence']]}")
    return SceneResult(
        scene="S2_discovery_emission",
        claim=(
            "DiscoveryCandidate is structured evidence: it never mutates "
            "the active corpus.  Phase C is the only path to mutation."
        ),
        detail={
            "candidate_id": payload["candidate_id"],
            "proposed_chain": payload["proposed_chain"],
            "polarity": payload["polarity"],
            "evidence": payload["evidence"],
        },
    ), payload


def _scene3_propose(log_path: Path, candidate_id: str) -> tuple[SceneResult, Any]:
    _print_header(
        "S3.  Operator-authored proposal — replay-equivalence gate runs",
        "From the discovery candidate's evidence, the operator authors "
        "a complete chain: narrative reveals meaning.  Affirming evidence "
        "is the existing corpus chain cause_creation_reveals_meaning. "
        "The real replay gate (teaching.replay.run_replay_equivalence) "
        "runs the cognition public split twice — active corpus vs. "
        "transient-with-appended-chain — and reports no regression.",
    )
    # Construct the operator-augmented candidate.  This is the operator
    # contribution: connective, object, and an affirming-source evidence
    # pointer to a corpus chain that already encodes the relevant
    # semantic shape.
    augmented = DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain={
            "subject": _DEMO_SUBJECT, "intent": "cause",
            "connective": _OPERATOR_CONNECTIVE,
            "object": _OPERATOR_OBJECT,
        },
        trigger="would_have_grounded",
        source_turn_trace="",
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref=_OPERATOR_EVIDENCE_REF,
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )
    log = ProposalLog(log_path)
    proposal = propose_from_candidate(augmented, log=log)
    rec = log.find(proposal.proposal_id) or {}
    ev = rec.get("replay_evidence") or {}
    _say(f"  proposal_id             : {proposal.proposal_id}")
    _say(f"  proposed_chain          : {proposal.proposed_chain}")
    _say(f"  evidence (corpus ref)   : {_OPERATOR_EVIDENCE_REF}")
    _say(f"  replay baseline         : {ev.get('baseline')}")
    _say(f"  replay candidate        : {ev.get('candidate')}")
    _say(f"  regressed_metrics       : {ev.get('regressed_metrics')}")
    _say(f"  replay_equivalent       : {ev.get('replay_equivalent')}")
    _say(f"  state                   : {rec.get('state')}")
    if rec.get("state") != "pending":
        raise RuntimeError(
            f"expected pending state but got {rec.get('state')!r}; "
            f"regressed metrics: {ev.get('regressed_metrics')}"
        )
    return SceneResult(
        scene="S3_propose_replay_pass",
        claim=(
            "Real replay gate confirms no metric regression — the "
            "proposal moves to pending.  Operator --accept still required."
        ),
        detail={
            "proposal_id": proposal.proposal_id,
            "proposed_chain": proposal.proposed_chain,
            "replay_evidence": ev,
            "state": rec.get("state"),
        },
    ), proposal


def _scene4_accept_against_transient(
    log_path: Path,
    proposal_id: str,
) -> tuple[SceneResult, Path]:
    _print_header(
        "S4.  Operator accept — transient corpus, active corpus untouched",
        "accept_proposal writes one JSONL line to a TRANSIENT corpus "
        "(copy of active + new chain).  The active corpus file bytes "
        "are byte-identical pre/post.  Provenance on the new entry: "
        "adr-0057:discovery_promoted:<review_date>.",
    )
    log = ProposalLog(log_path)
    tmp_dir = Path(tempfile.mkdtemp(prefix="learning_loop_demo_"))
    transient = tmp_dir / "cognition_chains_v1.jsonl"
    if _tg._CORPUS_PATH.exists():
        shutil.copyfile(_tg._CORPUS_PATH, transient)
    else:
        transient.write_text("", encoding="utf-8")

    active_before = _active_bytes()
    transient_lines_before = len(transient.read_text(encoding="utf-8").splitlines())

    chain_id = accept_proposal(
        proposal_id,
        log=log,
        corpus_path=transient,
        review_date="2026-05-18",
        operator_note="learning-loop demo (transient corpus only)",
    )
    active_after = _active_bytes()
    transient_lines_after = len(transient.read_text(encoding="utf-8").splitlines())

    _say(f"  appended chain_id       : {chain_id}")
    _say(f"  transient corpus path   : {transient}")
    _say(f"  transient lines  before : {transient_lines_before}")
    _say(f"  transient lines  after  : {transient_lines_after}")
    _say(f"  active corpus byte-eq   : {active_before == active_after}")
    if active_before != active_after:
        raise RuntimeError(
            "demo invariant broken: accept_proposal mutated the active corpus"
        )
    return SceneResult(
        scene="S4_accept_against_transient",
        claim=(
            "accept_proposal is the sole corpus-write surface.  Pointing "
            "it at a transient path leaves the active corpus byte-identical."
        ),
        detail={
            "chain_id": chain_id,
            "transient_corpus": str(transient),
            "transient_lines_before": transient_lines_before,
            "transient_lines_after": transient_lines_after,
            "active_corpus_byte_identical": active_before == active_after,
        },
    ), transient


def _scene5_replay_now_grounded(transient: Path) -> SceneResult:
    _print_header(
        "S5.  Same prompt — now deterministically teaching-grounded",
        "With the runtime's corpus path swapped to the transient corpus, "
        "the same prompt now returns a teaching-grounded surface "
        "containing the operator-accepted chain: "
        "narrative reveals meaning.  Identical bytes for any replay of "
        "the same prompt against this corpus state.",
    )
    # ADR-0064 — the cognition corpus is one of several registered
    # teaching corpora; surface composers now consult
    # ``_all_chains_index`` instead of ``_corpus_index`` alone.  We
    # rewrite the registry entry's path for the duration of the swap
    # and clear every teaching cache so the aggregator re-reads the
    # transient corpus.
    real_path = _tg._CORPUS_PATH
    original_specs = _tg.TEACHING_CORPORA
    swapped_specs = tuple(
        _tg.TeachingCorpusSpec(
            corpus_id=s.corpus_id,
            path=transient if s.corpus_id == _tg.TEACHING_CORPUS_ID else s.path,
            pack_id=s.pack_id,
        )
        for s in original_specs
    )
    try:
        _tg._CORPUS_PATH = transient  # type: ignore[assignment]
        _tg.TEACHING_CORPORA = swapped_specs  # type: ignore[misc]
        _tg.clear_teaching_caches()
        rt2 = ChatRuntime()
        response = rt2.chat(_DEMO_PROMPT)
    finally:
        _tg._CORPUS_PATH = real_path  # type: ignore[assignment]
        _tg.TEACHING_CORPORA = original_specs  # type: ignore[misc]
        _tg.clear_teaching_caches()

    surface = response.surface
    grounding = response.grounding_source
    _say(f"  prompt                  : {_DEMO_PROMPT}")
    _say(f"  surface                 : {surface}")
    _say(f"  grounding_source        : {grounding}")

    # Falsifiable assertions for the demo's headline claim.
    contains_subject = _DEMO_SUBJECT in surface.lower()
    contains_connective = "reveal" in surface.lower()  # humanised
    contains_object = "meaning" in surface.lower()
    is_teaching_grounded = grounding == "teaching"

    if not (contains_subject and contains_connective and contains_object and is_teaching_grounded):
        raise RuntimeError(
            f"demo invariant broken: same-prompt surface did not become "
            f"teaching-grounded (surface={surface!r}, grounding={grounding!r})"
        )

    return SceneResult(
        scene="S5_replay_now_grounded",
        claim=(
            "The same prompt now produces a deterministic teaching-"
            "grounded surface containing the accepted chain's "
            "subject / connective / object."
        ),
        detail={
            "surface": surface,
            "grounding_source": grounding,
            "contains_subject": contains_subject,
            "contains_connective_reveals": contains_connective,
            "contains_object_meaning": contains_object,
        },
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_demo(*, emit_json: bool = False) -> dict[str, Any]:
    """Run all five scenes and return a structured report."""
    global _VERBOSE
    _VERBOSE = not emit_json

    active_bytes_before = _active_bytes()
    rt = ChatRuntime()
    sink = _BufferSink()
    rt.attach_discovery_sink(sink)
    rt.attach_contemplation(enabled=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = Path(tmpdir) / "demo_proposals.jsonl"
        s1, _before_response = _scene1_cold_turn(rt, sink)
        s2, candidate_payload = _scene2_discovery_emission(sink)
        s3, proposal = _scene3_propose(log_path, candidate_payload["candidate_id"])
        s4, transient = _scene4_accept_against_transient(log_path, proposal.proposal_id)
        s5 = _scene5_replay_now_grounded(transient)

    active_bytes_after = _active_bytes()
    report = DemoReport(
        prompt=_DEMO_PROMPT,
        before_surface=s1.detail["surface"],
        before_grounding_source=s1.detail["grounding_source"],
        after_surface=s5.detail["surface"],
        after_grounding_source=s5.detail["grounding_source"],
        scenes=(s1, s2, s3, s4, s5),
        learning_loop_closed=(
            s1.detail["grounding_source"] == "none"
            and s5.detail["grounding_source"] == "teaching"
        ),
        active_corpus_byte_identical=(active_bytes_before == active_bytes_after),
    )

    if _VERBOSE:
        _say()
        _say("═" * 72)
        _say("  BEFORE / AFTER  (single deterministic prompt, one accept between)")
        _say("═" * 72)
        _say(f"  prompt   : {report.prompt}")
        _say(f"  before   : [{report.before_grounding_source}] {report.before_surface}")
        _say(f"  after    : [{report.after_grounding_source}] {report.after_surface}")
        _say()
        _say(f"  learning_loop_closed         : {report.learning_loop_closed}")
        _say(f"  active corpus byte-identical : {report.active_corpus_byte_identical}")
        _say()

    return report.as_dict()


__all__ = ["run_demo"]
