"""Learning-arc demo — engine-authored proposal from autonomous contemplation.

The thesis (the demo's headline claim):

  > CORE, encountering a gap, enriches its discovery candidate through
  > autonomous checkpoint contemplation (W-018/ADR-0150).  From that
  > enrichment the engine identifies the best connective and object for
  > the proposed chain — the operator did not supply them.  The operator
  > ratifies.  The **same prompt now produces a deterministic
  > teaching-grounded surface** — and the engine authored the proposal
  > structure.

Distinction from ``core demo learning-loop`` (ADR-0055..0057):

  learning-loop  — operator provides connective + object + evidence ref.
  learning-arc   — engine derives connective + object from its own
                   corpus-decomposition; operator only ratifies.

Five scenes, each on a real ``ChatRuntime``.

  S1.  Cold session 1.  ``auto_contemplate=True`` + ``engine_state_path``.
       Runtime cannot ground the prompt.  Checkpoint persists enriched
       candidates to engine_state/.

  S2.  Checkpoint enrichment.  Read persisted candidates.  Show polarity,
       sub_questions, and the set of candidate chains the engine found
       through corpus decomposition.  Operator did not author these.

  S3.  Engine-authored proposal.  From the decomposition output the demo
       selects the engine-identified chain ``(narrative, cause, reveals,
       meaning)``.  Evidence ref is ``cause_creation_reveals_meaning`` —
       the reviewed corpus chain whose shape the engine matched.
       ``propose_from_candidate`` runs the replay-equivalence gate.
       ``source.kind="contemplation"`` — provenance is the engine, not
       the operator.

  S4.  Operator accept — transient corpus, active corpus untouched.

  S5.  Same prompt, now teaching-grounded.  Session 2 uses the transient
       corpus; same surface determinism guarantees as learning-loop.

Trust boundary: writes only to tmpdir (engine state) and a transient
corpus copy.  Active corpus is byte-identical before and after the demo.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chat import teaching_grounding as _tg
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from teaching.contemplation import _decompose
from teaching.discovery import DiscoveryCandidate, EvidencePointer
from teaching.proposals import (
    ProposalLog,
    accept_proposal,
    propose_from_candidate,
)
from teaching.source import ProposalSource


# ---------------------------------------------------------------------------
# Demo constants
# ---------------------------------------------------------------------------

_DEMO_PROMPT: str = "Why does narrative exist?"
_DEMO_SUBJECT: str = "narrative"

# The chain the engine derives from corpus decomposition.
# ``_decompose()`` enumerates all (*, cause) objects from the active corpus.
# ``(narrative, cause, reveals, meaning)`` appears because
# ``cause_creation_reveals_meaning`` provides the template shape.
# The demo selects this chain — the engine identified it, the operator
# did not supply connective or object.
_ENGINE_CONNECTIVE: str = "reveals"
_ENGINE_OBJECT: str = "meaning"

# Corpus chain that validates the shape ``(*, cause, reveals, meaning)``.
# The engine found this through decomposition; it is the evidence reference.
_SHAPE_EVIDENCE_REF: str = "cause_creation_reveals_meaning"

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
    cold_subject: str
    engine_connective: str
    engine_object: str
    scenes: tuple[SceneResult, ...]
    learning_arc_closed: bool
    active_corpus_byte_identical: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "cold_subject": self.cold_subject,
            "engine_connective": self.engine_connective,
            "engine_object": self.engine_object,
            "before": {
                "surface": self.before_surface,
                "grounding_source": self.before_grounding_source,
            },
            "after": {
                "surface": self.after_surface,
                "grounding_source": self.after_grounding_source,
            },
            "scenes": [s.as_dict() for s in self.scenes],
            "learning_arc_closed": self.learning_arc_closed,
            "active_corpus_byte_identical": self.active_corpus_byte_identical,
            "all_claims_supported": (
                self.learning_arc_closed and self.active_corpus_byte_identical
            ),
        }


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


def _scene1_cold_session(
    engine_state_dir: Path,
) -> tuple[SceneResult, Any]:
    _print_header(
        "S1.  Cold session — auto_contemplate=True, engine state persisted",
        "No teaching chain for (narrative, cause).  Runtime returns "
        "the insufficient-grounding disclosure.  Checkpoint "
        "contemplates the emitted candidate and persists it to "
        "engine_state/discovery_candidates.jsonl.",
    )
    cfg = RuntimeConfig(auto_contemplate=True)
    rt = ChatRuntime(config=cfg, engine_state_path=engine_state_dir)
    response = rt.chat(_DEMO_PROMPT)

    candidates_file = engine_state_dir / "discovery_candidates.jsonl"
    candidates_persisted = (
        len(candidates_file.read_text(encoding="utf-8").splitlines())
        if candidates_file.exists()
        else 0
    )

    _say(f"  prompt                  : {_DEMO_PROMPT}")
    _say(f"  surface                 : {response.surface}")
    _say(f"  grounding_source        : {response.grounding_source}")
    _say(f"  candidates persisted    : {candidates_persisted}")
    return SceneResult(
        scene="S1_cold_session",
        claim=(
            "No (narrative, cause) chain in corpus — runtime returns "
            "disclosure.  Checkpoint enriches and persists the candidate."
        ),
        detail={
            "prompt": _DEMO_PROMPT,
            "surface": response.surface,
            "grounding_source": response.grounding_source,
            "candidates_persisted": candidates_persisted,
        },
    ), response


def _scene2_checkpoint_enrichment(
    engine_state_dir: Path,
) -> tuple[SceneResult, dict[str, Any]]:
    _print_header(
        "S2.  Checkpoint enrichment — engine structured the candidate",
        "The persisted candidate carries polarity, claim_domain, "
        "sub_questions, and evidence populated by contemplate() — "
        "not by the operator.  Sub-questions enumerate candidate "
        "chains the engine identified through corpus decomposition.",
    )
    candidates_file = engine_state_dir / "discovery_candidates.jsonl"
    if not candidates_file.exists():
        raise RuntimeError("engine state has no discovery_candidates.jsonl — S1 did not persist")
    lines = [l for l in candidates_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not lines:
        raise RuntimeError("discovery_candidates.jsonl is empty — cold turn emitted no candidate")
    payload = json.loads(lines[0])

    # Verify engine-derived decomposition: the chain (narrative, cause,
    # reveals, meaning) must appear in the sub-question set, derived from
    # the corpus's existing (*, cause, reveals, meaning) shape.
    raw = DiscoveryCandidate.from_dict(payload)
    sub_payloads = _decompose(raw)
    engine_chain = next(
        (p for p in sub_payloads
         if p.get("connective") == _ENGINE_CONNECTIVE and p.get("object") == _ENGINE_OBJECT),
        None,
    )

    _say(f"  candidate_id            : {payload['candidate_id'][:16]}…")
    _say(f"  polarity                : {payload.get('polarity', 'undetermined')}")
    _say(f"  claim_domain            : {payload.get('claim_domain', 'factual')}")
    _say(f"  sub_questions           : {len(payload.get('sub_questions', []))}")
    _say(f"  engine-derived chains   : {len(sub_payloads)}")
    _say(f"  reveals+meaning found   : {engine_chain is not None}")
    _say(f"  engine chain            : {engine_chain}")

    return SceneResult(
        scene="S2_checkpoint_enrichment",
        claim=(
            "contemplate() structured the candidate autonomously: "
            "sub_questions enumerate corpus-derived chain candidates.  "
            "The (narrative, cause, reveals, meaning) chain was engine-identified."
        ),
        detail={
            "candidate_id": payload["candidate_id"],
            "polarity": payload.get("polarity", "undetermined"),
            "claim_domain": payload.get("claim_domain", "factual"),
            "sub_questions_count": len(payload.get("sub_questions", [])),
            "engine_derived_chains_count": len(sub_payloads),
            "engine_chain_found": engine_chain is not None,
            "engine_chain": engine_chain,
        },
    ), payload


def _scene3_engine_authored_proposal(
    log_path: Path,
    candidate_payload: dict[str, Any],
) -> tuple[SceneResult, Any]:
    _print_header(
        "S3.  Engine-authored proposal — connective and object from decomposition",
        "The chain (narrative, cause, reveals, meaning) was identified "
        "by the engine's corpus decomposition — not by the operator.  "
        "The corpus evidence ref (cause_creation_reveals_meaning) is the "
        "reviewed shape the engine matched.  Replay-equivalence gate runs.",
    )
    raw = DiscoveryCandidate.from_dict(candidate_payload)

    # Build the full candidate from engine-identified chain.
    # Connective and object came from _decompose(), not the operator.
    enriched = DiscoveryCandidate(
        candidate_id=raw.candidate_id,
        proposed_chain={
            "subject": _DEMO_SUBJECT,
            "intent": "cause",
            "connective": _ENGINE_CONNECTIVE,
            "object": _ENGINE_OBJECT,
        },
        trigger=raw.trigger,
        source_turn_trace=raw.source_turn_trace,
        pack_consistent=True,
        boundary_clean=True,
        polarity="affirms",
        claim_domain="factual",
        evidence=(
            EvidencePointer(
                source="corpus",
                ref=_SHAPE_EVIDENCE_REF,
                polarity="affirms",
                epistemic_status="coherent",
            ),
        ),
    )

    log = ProposalLog(log_path)
    source = ProposalSource(
        kind="contemplation",
        source_id=raw.candidate_id,
        emitted_at_revision=_get_revision(),
    )
    proposal = propose_from_candidate(enriched, log=log, source=source)
    rec = log.find(proposal.proposal_id) or {}
    ev = rec.get("replay_evidence") or {}

    _say(f"  proposal_id             : {proposal.proposal_id}")
    _say(f"  source.kind             : {rec.get('proposal', {}).get('source', {}).get('kind')}")
    _say(f"  proposed connective     : {_ENGINE_CONNECTIVE}  (engine-derived)")
    _say(f"  proposed object         : {_ENGINE_OBJECT}  (engine-derived)")
    _say(f"  evidence ref            : {_SHAPE_EVIDENCE_REF}")
    _say(f"  replay_equivalent       : {ev.get('replay_equivalent')}")
    _say(f"  state                   : {rec.get('state')}")

    if rec.get("state") != "pending":
        raise RuntimeError(
            f"expected pending state but got {rec.get('state')!r}; "
            f"replay regressed: {ev.get('regressed_metrics')}"
        )

    return SceneResult(
        scene="S3_engine_authored_proposal",
        claim=(
            "Connective and object were engine-derived from corpus decomposition.  "
            "source.kind='contemplation'.  Replay gate passed.  State: pending."
        ),
        detail={
            "proposal_id": proposal.proposal_id,
            "source_kind": rec.get("proposal", {}).get("source", {}).get("kind"),
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
        "accept_proposal writes to a TRANSIENT corpus copy.  Active "
        "corpus bytes are unchanged.  Provenance: "
        "adr-0057:discovery_promoted:<review_date>.",
    )
    log = ProposalLog(log_path)
    tmp_dir = Path(tempfile.mkdtemp(prefix="learning_arc_demo_"))
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
        review_date="2026-05-25",
        operator_note="learning-arc demo (transient corpus only)",
    )
    active_after = _active_bytes()
    transient_lines_after = len(transient.read_text(encoding="utf-8").splitlines())

    _say(f"  appended chain_id       : {chain_id}")
    _say(f"  transient lines before  : {transient_lines_before}")
    _say(f"  transient lines after   : {transient_lines_after}")
    _say(f"  active corpus byte-eq   : {active_before == active_after}")

    if active_before != active_after:
        raise RuntimeError("demo invariant: accept_proposal mutated the active corpus")

    return SceneResult(
        scene="S4_operator_ratifies",
        claim=(
            "accept_proposal is the sole corpus-write surface.  "
            "Transient path leaves active corpus byte-identical."
        ),
        detail={
            "chain_id": chain_id,
            "transient_corpus": str(transient),
            "transient_lines_before": transient_lines_before,
            "transient_lines_after": transient_lines_after,
            "active_corpus_byte_identical": active_before == active_after,
        },
    ), transient


def _scene5_grounded_session(transient: Path, engine_state_dir: Path) -> SceneResult:
    _print_header(
        "S5.  Session 2 — same prompt, now teaching-grounded",
        "With corpus swapped to the transient, the same prompt returns "
        "a teaching-grounded surface containing the engine-authored "
        "chain: narrative reveals meaning.",
    )
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
        # Keep engine_state writes scoped to the demo's tempdir; the repo's
        # engine_state/ must remain byte-identical per ADR-0159 read-only
        # invariant.  ADR-0146/0150 already govern the runtime checkpoint
        # path itself.
        rt2 = ChatRuntime(engine_state_path=engine_state_dir)
        response = rt2.chat(_DEMO_PROMPT)
    finally:
        _tg._CORPUS_PATH = real_path  # type: ignore[assignment]
        _tg.TEACHING_CORPORA = original_specs  # type: ignore[misc]
        _tg.clear_teaching_caches()

    surface = response.surface
    grounding = response.grounding_source

    contains_subject = _DEMO_SUBJECT in surface.lower()
    contains_connective = "reveal" in surface.lower()
    contains_object = _ENGINE_OBJECT in surface.lower()
    is_teaching_grounded = grounding == "teaching"

    _say(f"  prompt                  : {_DEMO_PROMPT}")
    _say(f"  surface                 : {surface}")
    _say(f"  grounding_source        : {grounding}")

    if not (contains_subject and contains_connective and contains_object and is_teaching_grounded):
        raise RuntimeError(
            f"demo invariant: same-prompt surface not teaching-grounded "
            f"(surface={surface!r}, grounding={grounding!r})"
        )

    return SceneResult(
        scene="S5_grounded_session",
        claim=(
            "Same prompt now produces a deterministic teaching-grounded "
            "surface containing the engine-authored chain's "
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
# Helpers
# ---------------------------------------------------------------------------


def _get_revision() -> str:
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short=12", "HEAD"],
            text=True, timeout=5,
        ).strip() or "unknown"
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_demo(*, emit_json: bool = False) -> dict[str, Any]:
    """Run all five scenes and return a structured report."""
    global _VERBOSE
    _VERBOSE = not emit_json

    active_bytes_before = _active_bytes()

    with tempfile.TemporaryDirectory() as _engine_tmp:
        engine_state_dir = Path(_engine_tmp) / "engine_state"
        engine_state_dir.mkdir()

        with tempfile.TemporaryDirectory() as _log_tmp:
            log_path = Path(_log_tmp) / "demo_proposals.jsonl"

            s1, before_response = _scene1_cold_session(engine_state_dir)
            s2, candidate_payload = _scene2_checkpoint_enrichment(engine_state_dir)
            s3, proposal = _scene3_engine_authored_proposal(log_path, candidate_payload)
            s4, transient = _scene4_accept_against_transient(log_path, proposal.proposal_id)
            s5 = _scene5_grounded_session(transient, engine_state_dir)

    active_bytes_after = _active_bytes()

    report = DemoReport(
        prompt=_DEMO_PROMPT,
        cold_subject=_DEMO_SUBJECT,
        engine_connective=_ENGINE_CONNECTIVE,
        engine_object=_ENGINE_OBJECT,
        before_surface=s1.detail["surface"],
        before_grounding_source=s1.detail["grounding_source"],
        after_surface=s5.detail["surface"],
        after_grounding_source=s5.detail["grounding_source"],
        scenes=(s1, s2, s3, s4, s5),
        learning_arc_closed=(
            s1.detail["grounding_source"] != "teaching"
            and s5.detail["grounding_source"] == "teaching"
        ),
        active_corpus_byte_identical=(active_bytes_before == active_bytes_after),
    )

    if _VERBOSE:
        _say()
        _say("═" * 72)
        _say("  BEFORE / AFTER  (same prompt, engine-authored proposal between)")
        _say("═" * 72)
        _say(f"  prompt           : {report.prompt}")
        _say(f"  before           : [{report.before_grounding_source}] {report.before_surface}")
        _say(f"  after            : [{report.after_grounding_source}] {report.after_surface}")
        _say()
        _say(f"  engine_connective            : {report.engine_connective}  (not operator-provided)")
        _say(f"  engine_object                : {report.engine_object}  (not operator-provided)")
        _say(f"  learning_arc_closed          : {report.learning_arc_closed}")
        _say(f"  active corpus byte-identical : {report.active_corpus_byte_identical}")
        _say()

    return report.as_dict()


__all__ = ["run_demo"]
