"""ADR-0055 Phase B — DiscoveryCandidate emission from the turn loop.

A ``DiscoveryCandidate`` is **structured evidence** — never a
mutation.  When a turn's audit trail satisfies a deterministic
predicate, an entry is emitted to the discovery candidate stream.
Candidates **never** load into the active teaching corpus; the only
path to corpus extension is the review-gated
``TeachingChainProposal`` (Phase C, not yet built).

Trigger set (Phase B lands the first; the others are stubbed in the
``Literal`` so the structure is stable when later phases add them):

  - ``would_have_grounded`` — the turn fell through to the universal
    "insufficient grounding" disclosure, the classified intent was
    ``CAUSE`` or ``VERIFICATION``, the subject lemma is in the
    ratified cognition pack, and no active chain matched
    ``(subject, intent)``.  A reviewed chain of that subject/intent
    would have grounded the turn.

  - ``successful_comparison`` — open question §5 in ADR-0055; not
    fired in Phase B.

  - ``hedge_acknowledged`` — open question §5 in ADR-0055; not
    fired in Phase B.

  - ``oov_resolved_via_decomp`` — not fired in Phase B.

Determinism contract:

  - ``extract_discovery_candidates`` is a pure function of its
    inputs.
  - ``candidate_id`` is a SHA-256 hash of a canonical JSON encoding
    of the candidate's load-bearing fields; identical inputs always
    produce the identical id.
  - No LLM, no stochastic sampling, no clock-time read.

Trust boundary:

  - This module reads pack + corpus indices and a ``TurnEvent``.
    It never writes to the corpus, the pack, or runtime state.
  - The ``source_turn_trace`` is the upstream ``TurnEvent.trace_hash``
    when present; absent that, the empty string.  Tying every
    candidate to a replayable turn is the load-bearing audit
    property.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Literal

from generate.intent import IntentTag

# ``chat.pack_grounding`` and ``chat.teaching_grounding`` are
# imported lazily inside ``extract_discovery_candidates`` to break a
# circular import chain when an entry-point (e.g. the CLI) imports
# ``teaching.proposals`` → ``teaching.discovery`` before ``chat``
# has been fully initialized.


DiscoveryTrigger = Literal[
    "would_have_grounded",
    "successful_comparison",
    "hedge_acknowledged",
    "oov_resolved_via_decomp",
]


# ADR-0056 Phase C1: typed claim domain for the contemplation loop.
ClaimDomain = Literal["factual", "relational", "evaluative"]


@dataclass(frozen=True, slots=True)
class EvidencePointer:
    """One unit of admissible evidence used by the contemplation loop.

    Only three source families admit a pointer: reviewed teaching
    corpus chains, ratified pack atoms, and vault entries stamped
    ``EpistemicStatus.COHERENT``.  SPECULATIVE / CONTESTED / FALSIFIED
    vault entries contest but do not contribute as evidence.
    """

    source: Literal["corpus", "pack", "vault_coherent"]
    ref: str
    polarity: Literal["affirms", "falsifies"]
    epistemic_status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ref": self.ref,
            "polarity": self.polarity,
            "epistemic_status": self.epistemic_status,
        }


@dataclass(frozen=True, slots=True)
class SubQuestion:
    """One decomposed sub-question + its outcome (ADR-0056 §SubQuestion).

    ``outcome="gap_recorded"`` is the load-bearing case from Call 1
    in ADR-0056: the sub-question could not be decomposed further so
    the system records the gap and stops.
    """

    sub_id: str
    proposed_subject: str
    proposed_intent: str
    outcome: Literal["grounded", "gap_recorded", "depth_failsafe"]
    evidence: tuple[EvidencePointer, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "sub_id": self.sub_id,
            "proposed_subject": self.proposed_subject,
            "proposed_intent": self.proposed_intent,
            "outcome": self.outcome,
            "evidence": [e.as_dict() for e in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class DiscoveryCandidate:
    """Structured evidence that a reviewed chain would have helped.

    Phase B emits the Phase-B fields only.  ADR-0056 Phase C1 adds
    typed contemplation fields (``polarity``, ``claim_domain``,
    ``evidence``, ``sub_questions``, ``contemplation_depth``,
    ``recursion_overflow``).  Defaults make a freshly-emitted Phase B
    candidate a trivially-valid un-contemplated C1 candidate.
    """

    candidate_id: str
    proposed_chain: dict[str, Any]
    trigger: DiscoveryTrigger
    source_turn_trace: str
    pack_consistent: bool
    boundary_clean: bool
    review_state: Literal["unreviewed"] = "unreviewed"
    # Phase C1 fields.  Defaults preserve byte-equality with Phase B
    # ``as_dict`` output when the candidate has not been contemplated.
    polarity: Literal["affirms", "falsifies", "undetermined"] = "undetermined"
    claim_domain: ClaimDomain = "factual"
    evidence: tuple[EvidencePointer, ...] = ()
    sub_questions: tuple[SubQuestion, ...] = ()
    contemplation_depth: int = 0
    recursion_overflow: bool = False

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "proposed_chain": self.proposed_chain,
            "trigger": self.trigger,
            "source_turn_trace": self.source_turn_trace,
            "pack_consistent": self.pack_consistent,
            "boundary_clean": self.boundary_clean,
            "review_state": self.review_state,
        }
        # Phase C1 fields are emitted only when contemplation has
        # produced non-default content.  This keeps a freshly-emitted
        # Phase B candidate's JSONL line byte-identical to the pre-C1
        # encoding.
        if (
            self.polarity != "undetermined"
            or self.claim_domain != "factual"
            or self.evidence
            or self.sub_questions
            or self.contemplation_depth != 0
            or self.recursion_overflow
        ):
            out["polarity"] = self.polarity
            out["claim_domain"] = self.claim_domain
            out["evidence"] = [e.as_dict() for e in self.evidence]
            out["sub_questions"] = [s.as_dict() for s in self.sub_questions]
            out["contemplation_depth"] = self.contemplation_depth
            out["recursion_overflow"] = self.recursion_overflow
        return out


_TEACHING_INTENT_NAME: dict[IntentTag, str] = {
    IntentTag.CAUSE: "cause",
    IntentTag.VERIFICATION: "verification",
}


def _hash_candidate_id(payload: dict[str, Any]) -> str:
    """Deterministic SHA-256 over a canonical JSON encoding.

    Sorted keys + tight separators keep the hash stable across
    Python runtimes and dict-insertion order.  This is the
    ``candidate_id`` — used both as the on-disk JSONL line key and
    by Phase C to look up the originating candidate.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _boundary_clean(turn_event: Any) -> bool:
    """Return True iff the source turn produced no safety/ethics
    refusal and no hedge injection.

    Tolerates events that pre-date the bundled-verdicts era (ADR-0039
    onward) by reading the canonical fields directly.
    """
    refusal_emitted = bool(getattr(turn_event, "refusal_emitted", False) or False)
    hedge_injected = bool(getattr(turn_event, "hedge_injected", False) or False)
    if refusal_emitted or hedge_injected:
        return False
    verdicts = getattr(turn_event, "verdicts", None)
    if verdicts is not None:
        if bool(getattr(verdicts, "refusal_emitted", False) or False):
            return False
        if bool(getattr(verdicts, "hedge_injected", False) or False):
            return False
    return True


def _trace_hash(turn_event: Any) -> str:
    value = getattr(turn_event, "trace_hash", "") or ""
    return str(value)


def extract_discovery_candidates(
    turn_event: Any,
    intent_tag: IntentTag | None,
    intent_subject_lemma: str | None,
    *,
    grounding_source: str | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    """Return zero or more DiscoveryCandidates for a single turn.

    Phase B only fires the ``would_have_grounded`` trigger.  All
    other triggers in the ``DiscoveryTrigger`` Literal are reserved
    for later phases.

    Fires when **every** condition holds (deterministic predicate):

      1. ``grounding_source`` is ``"none"`` or absent — the turn
         fell through to the universal disclosure.
      2. ``intent_tag`` is ``CAUSE`` or ``VERIFICATION`` — the
         intent set the teaching-grounded surface answers.
      3. ``intent_subject_lemma`` is a non-empty pack lemma in the
         ratified cognition pack.
      4. ``(subject_lemma, intent_name)`` is **not** in the active
         corpus — a chain of that shape would have grounded the
         turn but does not exist.

    Order of conditions matters for tests: short-circuit on the
    cheapest predicate first.
    """
    source = (grounding_source or getattr(turn_event, "grounding_source", "none") or "none").lower()
    if source != "none":
        return ()
    if intent_tag is None or intent_tag not in _TEACHING_INTENT_NAME:
        return ()
    if not intent_subject_lemma or not isinstance(intent_subject_lemma, str):
        return ()
    lemma = intent_subject_lemma.strip().lower()
    if not lemma:
        return ()

    from chat.pack_grounding import _pack_index
    from chat.teaching_grounding import _corpus_index

    pack = _pack_index()
    if lemma not in pack:
        return ()

    intent_name = _TEACHING_INTENT_NAME[intent_tag]
    if (lemma, intent_name) in _corpus_index():
        return ()

    # The candidate's proposed_chain is intentionally partial: Phase B
    # can only assert that a chain of this (subject, intent) would
    # have helped.  Connective and object remain null; Phase C is
    # where a complete proposed entry is constructed and review-gated.
    proposed_chain = {
        "subject": lemma,
        "intent": intent_name,
        "connective": None,
        "object": None,
    }

    trace_hash = _trace_hash(turn_event)
    boundary_clean = _boundary_clean(turn_event)
    trigger: DiscoveryTrigger = "would_have_grounded"

    hash_payload = {
        "proposed_chain": proposed_chain,
        "trigger": trigger,
        "source_turn_trace": trace_hash,
    }
    candidate_id = _hash_candidate_id(hash_payload)

    candidate = DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain=proposed_chain,
        trigger=trigger,
        source_turn_trace=trace_hash,
        pack_consistent=True,  # subject is in pack; object is null pending Phase C
        boundary_clean=boundary_clean,
        review_state="unreviewed",
    )
    return (candidate,)


def format_candidate_jsonl(candidate: DiscoveryCandidate) -> str:
    """Serialise to one JSONL line (sorted keys, no trailing newline)."""
    return json.dumps(candidate.as_dict(), sort_keys=True, separators=(",", ":"))


__all__ = [
    "ClaimDomain",
    "DiscoveryCandidate",
    "DiscoveryTrigger",
    "EvidencePointer",
    "SubQuestion",
    "extract_discovery_candidates",
    "format_candidate_jsonl",
]
