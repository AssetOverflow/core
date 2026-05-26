"""ADR-0056 Phase C1 — Contemplation loop.

``contemplate(candidate)`` takes a Phase B ``DiscoveryCandidate``
(a *posed question*: "would a chain of shape (subject, intent) have
grounded this turn?") and returns an *enriched* candidate with:

  - ``polarity ∈ {affirms, falsifies, undetermined}`` — what
    composed reviewed evidence says about the proposed relation.
  - ``claim_domain ∈ {factual, relational, evaluative}`` — the
    epistemic register the claim sits in.  Determines the evidence
    threshold the future C2 review gate will demand.
  - ``evidence`` — tuple of ``EvidencePointer`` from the canonical
    probe order (vault → pack → corpus).
  - ``sub_questions`` — decomposed sub-questions and their outcomes
    (``grounded``, ``gap_recorded``, ``depth_failsafe``).
  - ``contemplation_depth`` — recursion depth reached.
  - ``recursion_overflow`` — True iff the bounded-depth failsafe
    fired.  Hitting the ceiling is itself an audit event;
    contemplation never silently truncates.

The loop is a pure function of the candidate, the reviewed teaching
corpus, the ratified cognition pack, and an optional vault probe
hook.  No clock-time, no LLM, no stochastic sampling, no concurrency
— ADR-0056 Call 4 (sync, not async).

Trust boundary: this module reads ``_pack_index()`` and
``_corpus_index()`` only.  It NEVER writes to the corpus, the pack,
or runtime state.  Output enriched candidates flow back through the
same Phase B sink as JSONL lines.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from typing import Any, Callable, Literal

from chat.pack_grounding import _pack_index
from chat.teaching_grounding import _corpus_index
from teaching.discovery import (
    ClaimDomain,
    DiscoveryCandidate,
    EvidencePointer,
    SubQuestion,
)

# Frame-dependent connectives (open question §1 in ADR-0056).  v1
# list lives here as a small reviewed constant; the long-term home
# is versioned pack data so that refining the taxonomy doesn't
# require a code change.  Adding/removing entries here is a reviewed
# code change, same as any other reviewed surface.
_FRAME_DEPENDENT_CONNECTIVES: frozenset[str] = frozenset({
    "orders",
    "grounds",
    "informs",
    "constrains",
})

_VaultProbe = Callable[[str, str], tuple[EvidencePointer, ...]]
"""Optional injectable vault probe.

Signature: ``probe(subject_lemma, object_lemma) -> tuple[EvidencePointer, ...]``.
Implementations MUST return only ``vault_coherent`` pointers
(``EpistemicStatus.COHERENT``); SPECULATIVE / CONTESTED / FALSIFIED
vault entries are filtered out by the implementation, not by the
loop.  ``None`` means "no vault probe in this contemplation pass."
"""

_DEFAULT_MAX_DEPTH: int = 8


# ---------------------------------------------------------------------------
# Sub-question id derivation
# ---------------------------------------------------------------------------


def _sub_id(parent_candidate_id: str, index: int, payload: dict[str, Any]) -> str:
    """Deterministic sub-question id.

    SHA-256 over ``(parent_id, index, sorted_payload_json)`` keeps the
    id stable across runs and ties the sub-question's identity to
    both its parent and its content.
    """
    import json as _json
    blob = _json.dumps(
        {"parent": parent_candidate_id, "index": index, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Probing — vault → pack → corpus
# ---------------------------------------------------------------------------


def _probe_corpus_direct(
    subject: str, intent: str, connective: str | None, obj: str | None
) -> tuple[EvidencePointer, ...]:
    """Look in the active reviewed corpus for affirming/falsifying chains.

    - Exact match on ``(subject, intent, connective, object)`` is
      affirming evidence (the proposed chain already exists).
    - Same ``(subject, intent, object)`` but different connective is
      a same-pack contradiction → falsifying evidence.
    - ``(subject, intent)`` match with no object filter and any
      connective is weak affirming evidence (the *shape* exists in
      reviewed memory).
    """
    out: list[EvidencePointer] = []
    corpus = _corpus_index()
    chain = corpus.get((subject, intent))
    if chain is None:
        return ()
    if obj is None and connective is None:
        # Phase B shape: shape evidence only.  The exact (subject,
        # intent) cell is in the corpus — affirming.
        out.append(EvidencePointer(
            source="corpus",
            ref=chain.chain_id,
            polarity="affirms",
            epistemic_status="coherent",
        ))
        return tuple(out)
    if obj is not None and chain.object == obj:
        if connective is None or chain.connective == connective:
            out.append(EvidencePointer(
                source="corpus",
                ref=chain.chain_id,
                polarity="affirms",
                epistemic_status="coherent",
            ))
        else:
            # Same subject + intent + object, different connective.
            # Direct same-pack contradiction.
            out.append(EvidencePointer(
                source="corpus",
                ref=chain.chain_id,
                polarity="falsifies",
                epistemic_status="coherent",
            ))
    return tuple(out)


def _probe_pack(subject: str, obj: str | None) -> tuple[EvidencePointer, ...]:
    """Pack lemma residency is shape-level affirming evidence.

    A pack-resident subject means the subject is grounded; if both
    subject and object are pack-resident, the relation has both
    endpoints anchored in ratified memory.  Pack residency cannot
    falsify (pack ``semantic_domains`` don't express negation —
    Call 2 of ADR-0056).
    """
    pack = _pack_index()
    out: list[EvidencePointer] = []
    if subject in pack:
        out.append(EvidencePointer(
            source="pack",
            ref=subject,
            polarity="affirms",
            epistemic_status="coherent",
        ))
    if obj is not None and obj in pack:
        out.append(EvidencePointer(
            source="pack",
            ref=obj,
            polarity="affirms",
            epistemic_status="coherent",
        ))
    return tuple(out)


def _probe_vault(
    subject: str, obj: str | None, vault_probe: _VaultProbe | None
) -> tuple[EvidencePointer, ...]:
    if vault_probe is None or obj is None:
        return ()
    try:
        return tuple(vault_probe(subject, obj))
    except Exception:  # pragma: no cover — defensive: vault probe must not poison loop
        return ()


# ---------------------------------------------------------------------------
# Decomposition
# ---------------------------------------------------------------------------


def _decompose(
    candidate: DiscoveryCandidate,
) -> tuple[dict[str, Any], ...]:
    """Return decomposed sub-question payloads.

    For a Phase B partial chain ``(subject, intent, None, None)``,
    enumerate every reviewed object the corpus has used with the
    same ``intent`` and treat each as a candidate match for
    ``subject``.  This is the deterministic, pack-grounded analogue
    of "what could this relation be about?"

    Returns an empty tuple when no decomposition is possible — the
    parent records the gap (Call 1 of ADR-0056) and stops.
    """
    intent = str(candidate.proposed_chain.get("intent") or "")
    if not intent:
        return ()
    obj = candidate.proposed_chain.get("object")
    if obj is not None:
        # Already has a concrete object — no further decomposition.
        return ()
    corpus = _corpus_index()
    # Deterministic order: sort by object lemma.
    seen_objects: list[tuple[str, str]] = []
    for key, chain in corpus.items():
        if key[1] != intent:
            continue
        seen_objects.append((chain.object, chain.connective))
    if not seen_objects:
        return ()
    seen_objects.sort()
    subject = str(candidate.proposed_chain.get("subject") or "")
    out: list[dict[str, Any]] = []
    for cand_obj, cand_conn in seen_objects:
        out.append({
            "subject": subject,
            "intent": intent,
            "connective": cand_conn,
            "object": cand_obj,
        })
    return tuple(out)


# ---------------------------------------------------------------------------
# Classification + composition
# ---------------------------------------------------------------------------


def _classify_claim_domain(chain: dict[str, Any]) -> ClaimDomain:
    """Deterministic claim-domain classification.

    - ``relational`` if the connective is in the reviewed
      frame-dependent set (e.g. ``orders``, ``grounds``).
    - ``factual`` otherwise (the default for pack-resident
      cognition lemmas).
    - ``evaluative`` is NOT auto-assigned in C1 — open question §2
      in ADR-0056.  Operator-assignable only.
    """
    connective = str(chain.get("connective") or "").strip().lower()
    if connective and connective in _FRAME_DEPENDENT_CONNECTIVES:
        return "relational"
    return "factual"


_DOMAIN_TIER: dict[ClaimDomain, int] = {
    "factual": 0,
    "relational": 1,
    "evaluative": 2,
}
_DOMAIN_BY_TIER: dict[int, ClaimDomain] = {
    0: "factual",
    1: "relational",
    2: "evaluative",
}


def _upgrade_domain(domain: ClaimDomain) -> ClaimDomain:
    tier = _DOMAIN_TIER[domain]
    return _DOMAIN_BY_TIER[min(tier + 1, 2)]


def _compose_polarity(
    direct_evidence: tuple[EvidencePointer, ...],
    sub_questions: tuple[SubQuestion, ...],
) -> Literal["affirms", "falsifies", "undetermined"]:
    """Reduce evidence + sub-question outcomes to one polarity verdict.

    Rules (Call 1 + Call 2 of ADR-0056):

    - Any direct ``falsifies`` evidence on the parent → ``falsifies``.
      A same-pack contradiction overrides supporting sub-evidence
      because reviewed contradiction is the strongest signal.
    - All admissible evidence ``affirms`` and at least one direct
      reviewed pointer (corpus or vault_coherent) → ``affirms``.
    - Mixed (some affirm, some falsify, but no direct parent-level
      falsification) → ``undetermined``.
    - No admissible evidence at all → ``undetermined``.
    """
    # Direct same-pack contradiction is dispositive — but ONLY when
    # the falsifying pointer comes from the reviewed teaching corpus
    # (Call 2 of ADR-0056: reviewed evidence in the same pack family).
    # Vault and pack pointers cannot dispositively falsify; they
    # contest but compose into the mixed-evidence path below.
    if any(
        e.polarity == "falsifies" and e.source == "corpus"
        for e in direct_evidence
    ):
        return "falsifies"

    # Gather all evidence pointers (direct + sub-question contributions).
    all_evidence: list[EvidencePointer] = list(direct_evidence)
    for sq in sub_questions:
        all_evidence.extend(sq.evidence)

    if not all_evidence:
        return "undetermined"

    has_falsifies = any(e.polarity == "falsifies" for e in all_evidence)
    has_affirms = any(e.polarity == "affirms" for e in all_evidence)
    if has_falsifies and has_affirms:
        return "undetermined"
    if has_falsifies:
        return "falsifies"
    # Require at least one *reviewed* affirming pointer (corpus or
    # vault_coherent) before promoting to ``affirms`` — pack
    # residency alone is shape evidence, not relation evidence.
    has_reviewed_affirm = any(
        e.polarity == "affirms" and e.source in ("corpus", "vault_coherent")
        for e in all_evidence
    )
    if has_reviewed_affirm:
        return "affirms"
    return "undetermined"


# ---------------------------------------------------------------------------
# The loop itself
# ---------------------------------------------------------------------------


def _materialise_sub_candidate(
    parent: DiscoveryCandidate, sub_payload: dict[str, Any], index: int
) -> DiscoveryCandidate:
    """Build a sub-candidate from a decomposed payload.

    Sub-candidates inherit ``trigger`` and ``source_turn_trace`` from
    the parent.  The ``candidate_id`` is derived deterministically
    from parent + index + payload — same as ``_sub_id``.
    """
    sub_id = _sub_id(parent.candidate_id, index, sub_payload)
    return replace(
        parent,
        candidate_id=sub_id,
        proposed_chain=dict(sub_payload),
        contemplation_depth=parent.contemplation_depth + 1,
        evidence=(),
        sub_questions=(),
        polarity="undetermined",
        claim_domain="factual",
        recursion_overflow=False,
    )


def _probe(
    chain: dict[str, Any], vault_probe: _VaultProbe | None
) -> tuple[EvidencePointer, ...]:
    """Canonical probe order: vault → pack → corpus.

    The first source that grounds wins for *that* axis, but all
    admissible pointers contribute — composition reduces them.
    """
    subject = str(chain.get("subject") or "").strip().lower()
    intent = str(chain.get("intent") or "").strip().lower()
    connective_raw = chain.get("connective")
    connective = str(connective_raw).strip().lower() if connective_raw else None
    obj_raw = chain.get("object")
    obj = str(obj_raw).strip().lower() if obj_raw else None

    out: list[EvidencePointer] = []
    out.extend(_probe_vault(subject, obj, vault_probe))
    out.extend(_probe_pack(subject, obj))
    out.extend(_probe_corpus_direct(subject, intent, connective, obj))
    return tuple(out)


def _gap_subquestion(parent: DiscoveryCandidate) -> SubQuestion:
    subject = str(parent.proposed_chain.get("subject") or "")
    intent = str(parent.proposed_chain.get("intent") or "")
    payload = {"subject": subject, "intent": intent, "outcome": "gap_recorded"}
    return SubQuestion(
        sub_id=_sub_id(parent.candidate_id, -1, payload),
        proposed_subject=subject,
        proposed_intent=intent,
        outcome="gap_recorded",
        evidence=(),
    )


def _depth_failsafe_subquestion(parent: DiscoveryCandidate) -> SubQuestion:
    subject = str(parent.proposed_chain.get("subject") or "")
    intent = str(parent.proposed_chain.get("intent") or "")
    payload = {"subject": subject, "intent": intent, "outcome": "depth_failsafe"}
    return SubQuestion(
        sub_id=_sub_id(parent.candidate_id, -2, payload),
        proposed_subject=subject,
        proposed_intent=intent,
        outcome="depth_failsafe",
        evidence=(),
    )


def contemplate(
    candidate: DiscoveryCandidate,
    *,
    max_depth: int = _DEFAULT_MAX_DEPTH,
    vault_probe: _VaultProbe | None = None,
) -> DiscoveryCandidate:
    """Run the contemplation loop on a single candidate.

    Returns an *enriched* candidate (same id, populated C1 fields).
    Never mutates the corpus, the pack, or the input candidate
    (``DiscoveryCandidate`` is frozen).
    """
    # Failsafe (Call 1 of ADR-0056): bounded depth ceiling whose hit
    # is itself an audit event, not a silent truncation.
    if candidate.contemplation_depth >= max_depth:
        return replace(
            candidate,
            recursion_overflow=True,
            sub_questions=(_depth_failsafe_subquestion(candidate),),
        )

    # Direct probe on the parent chain.
    direct_evidence = _probe(candidate.proposed_chain, vault_probe)

    # Decompose into sub-questions.
    sub_payloads = _decompose(candidate)

    if not sub_payloads:
        # Terminal: cannot decompose further.  Record the gap.
        # Direct evidence (if any) still composes — a parent may be
        # directly groundable without sub-decomposition.
        if direct_evidence:
            polarity = _compose_polarity(direct_evidence, ())
            domain = _classify_claim_domain(candidate.proposed_chain)
            if polarity == "undetermined":
                has_aff = any(p.polarity == "affirms" for p in direct_evidence)
                has_fal = any(p.polarity == "falsifies" for p in direct_evidence)
                if has_aff and has_fal:
                    domain = _upgrade_domain(domain)
            return replace(
                candidate,
                polarity=polarity,
                claim_domain=domain,
                evidence=direct_evidence,
                sub_questions=(),
            )
        # No evidence and no decomposition → gap recorded.
        return replace(
            candidate,
            polarity="undetermined",
            claim_domain=_classify_claim_domain(candidate.proposed_chain),
            evidence=(),
            sub_questions=(_gap_subquestion(candidate),),
        )

    sub_results: list[SubQuestion] = []
    for index, payload in enumerate(sub_payloads):
        sub_candidate = _materialise_sub_candidate(candidate, payload, index)
        recursed = contemplate(
            sub_candidate, max_depth=max_depth, vault_probe=vault_probe
        )
        outcome: Literal["grounded", "gap_recorded", "depth_failsafe"]
        if recursed.recursion_overflow:
            outcome = "depth_failsafe"
        elif recursed.evidence and recursed.polarity != "undetermined":
            outcome = "grounded"
        elif recursed.evidence:
            # Has evidence but composed to undetermined: treat as
            # grounded (evidence exists) — the parent's compose step
            # will see the pointers and may still go undetermined.
            outcome = "grounded"
        else:
            outcome = "gap_recorded"
        sub_results.append(SubQuestion(
            sub_id=_sub_id(candidate.candidate_id, index, payload),
            proposed_subject=str(payload.get("subject") or ""),
            proposed_intent=str(payload.get("intent") or ""),
            outcome=outcome,
            evidence=recursed.evidence,
        ))

    sub_tuple = tuple(sub_results)
    polarity = _compose_polarity(direct_evidence, sub_tuple)
    domain = _classify_claim_domain(candidate.proposed_chain)
    # Composition rule from ADR-0056: mixed evidence ⇒
    # ``undetermined`` AND claim_domain upgrades one tier.
    if polarity == "undetermined":
        all_ptrs = list(direct_evidence) + [p for sq in sub_tuple for p in sq.evidence]
        has_aff = any(p.polarity == "affirms" for p in all_ptrs)
        has_fal = any(p.polarity == "falsifies" for p in all_ptrs)
        if has_aff and has_fal:
            domain = _upgrade_domain(domain)

    return replace(
        candidate,
        polarity=polarity,
        claim_domain=domain,
        evidence=direct_evidence,
        sub_questions=sub_tuple,
    )


# ---------------------------------------------------------------------------
# ADR-0163 Phase C — exemplar-corpus contemplation
# ---------------------------------------------------------------------------


def _exemplar_candidate_id(corpus_digest: str, spec_digest: str) -> str:
    """Deterministic candidate id for an exemplar-derived contemplation.

    Hash over the corpus digest + the spec digest: identical corpora
    yield identical specs yield identical candidate ids.  Re-running the
    contemplation pipeline against an unchanged corpus is a no-op for
    the proposal log (idempotency via ProposalLog.find).
    """
    blob = json.dumps(
        {"corpus_digest": corpus_digest, "spec_digest": spec_digest},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def contemplate_exemplar_corpus(corpus: Any) -> DiscoveryCandidate:
    """Return a :class:`DiscoveryCandidate` distilled from *corpus*.

    Ingests a single :class:`~teaching.exemplar_ingest.ExemplarCorpus`,
    synthesizes its :class:`~teaching.recognizer_synthesis.RecognizerSpec`,
    and serializes both into a complete-shape ``DiscoveryCandidate`` that
    the existing proposal pipeline can consume.

    Trust boundary
    - Pure: no filesystem writes, no global state, no LLM, no
      stochastic sampling.
    - The returned candidate carries ``polarity="affirms"`` — exemplars
      are reviewed-evidence-floor material under ADR-0163 §Phase B —
      and one ``EvidencePointer`` per ingested exemplar, sourced from
      the exemplar corpus itself.  ``ref`` strings carry the verbatim
      ``case_id`` (when present) or ``exemplar:<exemplar_id>`` so the
      proposal log records every seed cited.
    - Encodes the recognizer-shaped chain as a synthetic
      ``(shape_category, "admissibility", "recognizes", spec_digest)``
      tuple so ``proposed_chain`` satisfies the four-field completeness
      gate enforced by ``check_eligibility``.  The full
      :class:`RecognizerSpec` rides along as a ``recognizer_spec``
      sub-mapping on ``proposed_chain``.
    """
    # Deferred imports keep this module's import cost cheap for
    # callers that never trigger Phase C ingest.
    from teaching.exemplar_ingest import ExemplarCorpus
    from teaching.recognizer_synthesis import (
        RecognizerSpec,
        synthesize_recognizer,
    )

    if not isinstance(corpus, ExemplarCorpus):
        raise TypeError(
            f"contemplate_exemplar_corpus expects ExemplarCorpus; got "
            f"{type(corpus).__name__}"
        )

    spec: RecognizerSpec = synthesize_recognizer(corpus)
    spec_digest = spec.spec_digest()

    proposed_chain: dict[str, Any] = {
        "subject": spec.shape_category.value,
        "intent": "admissibility",
        "connective": "recognizes",
        "object": spec_digest,
        "recognizer_spec": spec.as_dict(),
    }

    evidence: tuple[EvidencePointer, ...] = tuple(
        EvidencePointer(
            source="corpus",
            ref=(
                f"exemplar:{ex.case_id}"
                if ex.case_id
                else f"exemplar:{ex.exemplar_id}"
            ),
            polarity="affirms",
            epistemic_status="coherent",
        )
        for ex in corpus.exemplars
    )

    candidate_id = _exemplar_candidate_id(corpus.corpus_digest, spec_digest)

    return DiscoveryCandidate(
        candidate_id=candidate_id,
        proposed_chain=proposed_chain,
        trigger="would_have_grounded",
        source_turn_trace=f"exemplar_corpus:{corpus.corpus_digest}",
        pack_consistent=True,
        boundary_clean=True,
        review_state="unreviewed",
        polarity="affirms",
        claim_domain="factual",
        evidence=evidence,
        sub_questions=(),
        contemplation_depth=0,
        recursion_overflow=False,
    )


__all__ = [
    "contemplate",
    "contemplate_exemplar_corpus",
]
