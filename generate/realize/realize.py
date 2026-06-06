"""REALIZE slice R0 — one told fact becomes a realized vault entry.

The boundary that turns comprehension from an EVAL ARTIFACT into accumulating living
knowledge: a comprehended declarative fact is integrated into the held self as a
SPECULATIVE, provenance-rich vault entry that survives reboot and recalls exactly.

A realized record is NOT a new store — it is a structured vault entry
``(versor, metadata)`` so it inherits exact ``cga_inner`` recall, ``EpistemicStatus``
stamping, and bit-exact Shape B+ persistence for free (see
``docs/analysis/REALIZE-scope-2026-06-06.md``).

Slice R0 was deliberately boring: one told fact, SPECULATIVE only, in-vocab subject
only, single non-negated declarative relation. The in-vocab restriction is now LIFTED
(OOV subjects realize too): OOV grounding is deterministic, reboot-stable, and injective
(#591), and correctness rests on the structural key, not the versor. Slice R1 (this
module + ``recall.py``) adds the relation-space KEY R0 lacked: ordered
``relation_arguments`` + a span-free ``structure_key`` so
distinct facts about one subject stay distinct (they collide on the field versor), and
``recall_realized`` retrieves them by exact structural metadata. Dedup is now span-free
(``structure_key``), guarded by an ambiguous-entity-name refusal (wrong=0). Explicitly
still OUT: COHERENT promotion, teaching-loop proposals, the quantitative
``binding_graph`` path (R1c), trace-folding (see
``docs/analysis/REALIZE-R1-DETERMINE-scope-2026-06-06.md``).

wrong=0 at this layer: a ``Refusal`` (or any ineligible / ungrounded input) realizes
NOTHING — it is returned as ``NotRealized(reason)``, never coerced into a vault entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from formation.hashing import sha256_of
from generate.meaning_graph.reader import Comprehension, Refusal
from session.context import SessionContext
from teaching.epistemic import EpistemicStatus

# The known failure modes of the session embedding path (probe_ingest):
# RuntimeError on cross-turn versor-condition violation; Key/Index/ValueError on a
# degenerate grounding. Any of them is a clean no-op, never a crashed turn.
_GROUNDING_FAILURES = (RuntimeError, KeyError, IndexError, ValueError)

#: R0 realizes only the neutral MeaningGraph substrate. The record shape already
#: admits a second substrate (the quantitative binding-graph) via ``structure_kind``.
_STRUCTURE_KIND_MEANING_GRAPH = "meaning_graph"


@dataclass(frozen=True, slots=True)
class Derivation:
    """Provenance of a DERIVED realized fact (Step D consolidation).

    A derived fact is the conclusion of a SOUND is-a rule (``member_subset`` or
    ``subset_subset``) over premises that were themselves realized (told or previously
    consolidated), confirmed by the sound+complete proof_chain ROBDD. ``rule`` names
    the inference; ``premise_structure_keys`` are the span-free identities of the
    premise records (so a replay re-fetches them and re-verifies the chain);
    ``verdict`` is the decider's outcome — always ``"entailed"`` (a non-entailed
    candidate is never consolidated). This makes the soundness claim MEANINGFULLY FAIL
    on replay (Schema-Defined Proof Obligations): re-deriving from the recorded
    premises must still entail the fact.
    """

    rule: str
    premise_structure_keys: tuple[str, ...]
    verdict: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule,
            "premise_structure_keys": list(self.premise_structure_keys),
            "verdict": self.verdict,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Derivation":
        return cls(
            rule=payload["rule"],
            premise_structure_keys=tuple(payload.get("premise_structure_keys", [])),
            verdict=payload.get("verdict", ""),
        )


@dataclass(frozen=True, slots=True)
class RealizedRecord:
    """The realized-knowledge record (mirrors the stored vault metadata)."""

    structure_kind: str
    structure_canonical: str
    relation_predicate: str
    #: Ordered argument identities (subject first) — the relation-space key R0's
    #: sorted ``entity_names`` discards. Distinct facts about one subject differ
    #: here even though they collide on the field versor.
    relation_arguments: tuple[str, ...]
    entity_names: tuple[str, ...]
    source_span: str
    content_hash: str
    #: Span-FREE structural identity (predicate + negated + ordered argument
    #: ids). Idempotency dedups on this, so the same proposition told from a
    #: different source/offset collapses (which the span-inclusive ``content_hash``
    #: could not). ``content_hash`` is retained for provenance + ``replay_hash``.
    structure_key: str
    replay_hash: str
    epistemic_status: str
    tier: str
    #: LIVE deque position at recall/write time — authoritative in the unbounded
    #: session tier; provenance-only under bounded-vault eviction.
    vault_index: int
    #: Step D — a TOLD fact is ``derived=False`` (``derivation=None``). A consolidated
    #: fact (the conclusion of a sound is-a rule, proof_chain-verified) is
    #: ``derived=True`` with a :class:`Derivation`. Defaults preserve the told-record
    #: shape (and bit-exact persistence) for every pre-D caller.
    derived: bool = False
    derivation: "Derivation | None" = None


@dataclass(frozen=True, slots=True)
class Realized:
    """The fact is realized. ``created`` is False on an idempotent dedup hit
    (the fact was already realized this session — no new vault entry written)."""

    record: RealizedRecord
    created: bool


@dataclass(frozen=True, slots=True)
class NotRealized:
    """Nothing was realized (no vault write). ``reason`` is for audit, not control."""

    reason: str


def realize_comprehension(
    comprehension: Comprehension | Refusal, ctx: SessionContext
) -> Realized | NotRealized:
    """Realize a comprehended declarative fact into ``ctx``'s vault, or decline.

    Eligibility (R0): a ``Comprehension`` (not a ``Refusal``) with NO queries and
    EXACTLY ONE non-negated relation whose subject argument grounds in-vocabulary.
    Everything else is a typed ``NotRealized`` — no vault write (wrong=0).
    """
    if isinstance(comprehension, Refusal):
        return NotRealized("refusal")
    if not isinstance(comprehension, Comprehension):
        return NotRealized("not_a_comprehension")
    if comprehension.queries:
        return NotRealized("query_bearing")  # a question is recall, not intake

    graph = comprehension.meaning_graph
    if len(graph.relations) != 1:
        return NotRealized("not_single_relation")  # multi-relation intake is ambiguous in R0
    rel = graph.relations[0]
    if rel.negated:
        return NotRealized("negated_relation")
    if not rel.arguments:
        return NotRealized("empty_relation")  # defensive — arity>=1 by construction

    # wrong=0 defense (R1b): the MeaningGraph model permits distinct entities to
    # share a name (only ``entity_id`` is enforced unique; today the reader sets
    # entity_id == name, so this is latent, not live). A name-keyed structural
    # identity would collapse a converse/homonym fact, dropping a genuinely
    # distinct proposition — so refuse the ambiguous input now, before a future
    # reader makes it load-bearing.
    names = [e.name for e in graph.entities]
    if len(set(names)) != len(names):
        return NotRealized("ambiguous_entity_names")

    subject_id = rel.arguments[0]
    entity = next((e for e in graph.entities if e.entity_id == subject_id), None)
    if entity is None:
        return NotRealized("ungrounded_subject")  # defensive — graph invariant

    subject_token = entity.name
    # OOV subjects ARE realizable (R0's in-vocab gate is lifted). OOV grounding is
    # deterministic and reboot-stable, and #591 makes it injective (distinct token
    # content -> distinct field point, closure-by-construction). Correctness does not
    # rest on the versor anyway: distinct facts stay distinct by their structural key
    # + structural recall (recall.py), and reboot-stability rests on the Shape B+
    # snapshot of the exact stored bytes — so even a colliding placement never
    # confuses recall.
    #
    # probe_ingest is side-effect-free for an IN-VOCAB token, but for an OOV token it
    # mutates the shared vocab via insert_transient — a SESSION-SCOPED transient that
    # is NOT serialized into the snapshot (session/context.py: vocab is a shared
    # ratified surface, not session state), so it is re-derived deterministically on
    # reboot and never affects reboot stability. The field point still composes with
    # the CURRENT session state (deterministic GIVEN that state, not purely
    # subject-determined). Closure stays algebra/versor.py's job — REALIZE adds none.
    # A degenerate construction raises and is caught below -> NotRealized.
    try:
        field_state = ctx.probe_ingest([subject_token])
    except _GROUNDING_FAILURES:
        return NotRealized("grounding_failed")
    versor = np.asarray(field_state.F, dtype=np.float32)

    # Ordered argument identities (subject first). entity_id == name in today's
    # reader; the map keeps this correct if a future reader separates them.
    name_of = {e.entity_id: e.name for e in graph.entities}
    relation_arguments = tuple(name_of.get(a, a) for a in rel.arguments)

    structure_canonical = graph.to_canonical_string()
    source_span = rel.span.to_canonical_string()
    content_hash = sha256_of(structure_canonical)  # span-INCLUSIVE: provenance
    # Span-FREE structural identity: the asserted proposition, free of source
    # offsets. Idempotency dedups on this, so the same fact told from a different
    # source/offset collapses (the span-inclusive content_hash could not).
    structure_key = sha256_of(
        {
            "structure_kind": _STRUCTURE_KIND_MEANING_GRAPH,
            "predicate": rel.predicate,
            "negated": rel.negated,
            "arguments": list(relation_arguments),
        }
    )
    status = EpistemicStatus.SPECULATIVE  # COHERENT is never a default (ADR-0021)
    replay_hash = sha256_of(
        {
            "content_hash": content_hash,
            "source_span": source_span,
            "epistemic_status": status.value,
        }
    )
    entity_names = tuple(sorted(e.name for e in graph.entities))

    return _realize_structured(
        ctx,
        structure_kind=_STRUCTURE_KIND_MEANING_GRAPH,
        structure_canonical=structure_canonical,
        relation_predicate=rel.predicate,
        relation_arguments=relation_arguments,
        entity_names=entity_names,
        source_span=source_span,
        content_hash=content_hash,
        structure_key=structure_key,
        replay_hash=replay_hash,
        versor=versor,
        status=status,
    )


def _realize_structured(
    ctx: SessionContext,
    *,
    structure_kind: str,
    structure_canonical: str,
    relation_predicate: str,
    relation_arguments: tuple[str, ...],
    entity_names: tuple[str, ...],
    source_span: str,
    content_hash: str,
    structure_key: str,
    replay_hash: str,
    versor: np.ndarray,
    status: EpistemicStatus,
    derivation: "Derivation | None" = None,
) -> Realized:
    """Dedup-or-store a realized record — the single wrong=0 write path shared by
    every substrate (meaning_graph relations, binding_graph quantities, and Step D
    derived facts).

    Idempotency dedups exactly on the span-free ``structure_key`` (callers refuse
    ambiguous identity before getting here, so a hit is always the genuinely-same
    proposition, never a distinct one). The ``vault.store`` call is the only
    mutation; ``iter_metadata`` is the public read-only accessor and ``idx`` is the
    LIVE deque position. The epistemic status is whatever the caller declared —
    SPECULATIVE, never COHERENT by default (ADR-0021). A ``derivation`` marks a
    consolidated (derived) fact; ``None`` is a told fact (the historical shape).
    """
    for idx, meta in ctx.vault.iter_metadata():
        if meta.get("kind") == "realized" and meta.get("structure_key") == structure_key:
            return Realized(record=_record_from_metadata(meta, idx), created=False)

    metadata: dict[str, Any] = {
        "kind": "realized",
        "structure_kind": structure_kind,
        "structure_canonical": structure_canonical,
        "relation_predicate": relation_predicate,
        "relation_arguments": list(relation_arguments),
        "entity_names": list(entity_names),
        "source_span": source_span,
        "content_hash": content_hash,
        "structure_key": structure_key,
        "replay_hash": replay_hash,
        "tier": "session",
    }
    if derivation is not None:
        # Derived-fact provenance is additive — a told fact omits both keys, so its
        # on-disk metadata stays byte-identical to the pre-D encoding.
        metadata["derived"] = True
        metadata["derivation"] = derivation.as_dict()
    vault_index = ctx.vault.store(versor, metadata, epistemic_status=status)
    return Realized(
        record=RealizedRecord(
            structure_kind=structure_kind,
            structure_canonical=structure_canonical,
            relation_predicate=relation_predicate,
            relation_arguments=relation_arguments,
            entity_names=entity_names,
            source_span=source_span,
            content_hash=content_hash,
            structure_key=structure_key,
            replay_hash=replay_hash,
            epistemic_status=status.value,
            tier="session",
            vault_index=vault_index,
            derived=derivation is not None,
            derivation=derivation,
        ),
        created=True,
    )


def realize_derived(
    ctx: SessionContext,
    *,
    predicate: str,
    subject: str,
    obj: str,
    rule: str,
    premise_structure_keys: tuple[str, ...],
) -> Realized | NotRealized:
    """Consolidate a SOUNDLY-DERIVED fact into the held self (Step D — CLOSE).

    The caller (``generate.determine.consolidate``) has already found and
    proof_chain-VERIFIED the is-a chain that entails ``predicate(subject, obj)`` — this
    only writes the conclusion as a realized record so the next ``determine`` reaches it
    directly. The record is:

      - SPECULATIVE / ``as_told`` — a sound INFERENCE never upgrades the STANDING of its
        (SPECULATIVE) premises; COHERENT is never minted here (ADR-0021 honesty).
      - SESSION memory (immediate) — NOT reviewed/corpus learning; nothing is proposed,
        the teaching/review HITL path is untouched (no parallel learning path).
      - keyed by the SAME span-free ``structure_key`` a told ``predicate(subject, obj)``
        would carry, so it dedups against / is found by the told path identically, and
        is recalled by ``recall_realized`` like any other realized fact.
      - provenance-rich (``Derivation``): the premise ``structure_key``s + rule + the
        ENTAILED verdict, so a replay re-derives and re-verifies (the soundness claim
        can MEANINGFULLY FAIL).

    Idempotent (dedups on ``structure_key``); returns ``NotRealized`` on any ineligible
    input or grounding failure — never a partial / coerced write (wrong=0).
    """
    subject = (subject or "").strip()
    obj = (obj or "").strip()
    predicate = (predicate or "").strip()
    if not subject or not obj or not predicate:
        return NotRealized("incomplete_derived_fact")

    # The derived fact embeds its subject identically to a told fact about that subject
    # (same probe_ingest placement). The versor is not the recall key (structural
    # metadata is), so a degenerate placement is a clean no-op, never a wrong write.
    try:
        field_state = ctx.probe_ingest([subject])
    except _GROUNDING_FAILURES:
        return NotRealized("grounding_failed")
    versor = np.asarray(field_state.F, dtype=np.float32)

    relation_arguments = (subject, obj)
    structure_canonical = f"derived:{predicate}({subject},{obj})"
    source_span = f"derived:{rule}"
    content_hash = sha256_of(structure_canonical)  # span-inclusive provenance
    structure_key = sha256_of(
        {
            "structure_kind": _STRUCTURE_KIND_MEANING_GRAPH,
            "predicate": predicate,
            "negated": False,
            "arguments": list(relation_arguments),
        }
    )
    status = EpistemicStatus.SPECULATIVE  # derived from SPECULATIVE premises — as-told
    replay_hash = sha256_of(
        {
            "content_hash": content_hash,
            "source_span": source_span,
            "epistemic_status": status.value,
        }
    )
    entity_names = tuple(sorted({subject, obj}))
    derivation = Derivation(
        rule=rule,
        premise_structure_keys=tuple(premise_structure_keys),
        verdict="entailed",
    )
    return _realize_structured(
        ctx,
        structure_kind=_STRUCTURE_KIND_MEANING_GRAPH,
        structure_canonical=structure_canonical,
        relation_predicate=predicate,
        relation_arguments=relation_arguments,
        entity_names=entity_names,
        source_span=source_span,
        content_hash=content_hash,
        structure_key=structure_key,
        replay_hash=replay_hash,
        versor=versor,
        status=status,
        derivation=derivation,
    )


def _record_from_metadata(meta: dict, idx: int) -> RealizedRecord:
    """Reconstruct a RealizedRecord from a stored vault metadata dict."""
    derivation_payload = meta.get("derivation")
    return RealizedRecord(
        structure_kind=meta.get("structure_kind", _STRUCTURE_KIND_MEANING_GRAPH),
        structure_canonical=meta.get("structure_canonical", ""),
        relation_predicate=meta.get("relation_predicate", ""),
        relation_arguments=tuple(meta.get("relation_arguments", [])),
        entity_names=tuple(meta.get("entity_names", [])),
        source_span=meta.get("source_span", ""),
        content_hash=meta.get("content_hash", ""),
        structure_key=meta.get("structure_key", ""),
        replay_hash=meta.get("replay_hash", ""),
        epistemic_status=meta.get("epistemic_status", "speculative"),
        tier=meta.get("tier", "session"),
        vault_index=idx,
        derived=bool(meta.get("derived", False)),
        derivation=(
            Derivation.from_dict(derivation_payload)
            if isinstance(derivation_payload, dict)
            else None
        ),
    )
