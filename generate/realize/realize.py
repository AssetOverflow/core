"""REALIZE slice R0 — one told fact becomes a realized vault entry.

The boundary that turns comprehension from an EVAL ARTIFACT into accumulating living
knowledge: a comprehended declarative fact is integrated into the held self as a
SPECULATIVE, provenance-rich vault entry that survives reboot and recalls exactly.

A realized record is NOT a new store — it is a structured vault entry
``(versor, metadata)`` so it inherits exact ``cga_inner`` recall, ``EpistemicStatus``
stamping, and bit-exact Shape B+ persistence for free (see
``docs/analysis/REALIZE-scope-2026-06-06.md``).

Slice R0 deliberately boring (everything else grows from this without corrupting the
field): one told fact, SPECULATIVE only, in-vocab subject only, single non-negated
declarative relation, dedup by content hash. Explicitly OUT of R0: COHERENT
promotion, teaching-loop proposals, the quantitative ``binding_graph`` path,
trace-folding, and relation-space recall.

wrong=0 at this layer: a ``Refusal`` (or any ineligible / ungrounded input) realizes
NOTHING — it is returned as ``NotRealized(reason)``, never coerced into a vault entry.
"""

from __future__ import annotations

from dataclasses import dataclass

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
class RealizedRecord:
    """The realized-knowledge record (mirrors the stored vault metadata)."""

    structure_kind: str
    structure_canonical: str
    relation_predicate: str
    entity_names: tuple[str, ...]
    source_span: str
    content_hash: str
    replay_hash: str
    epistemic_status: str
    tier: str
    vault_index: int


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

    subject_id = rel.arguments[0]
    entity = next((e for e in graph.entities if e.entity_id == subject_id), None)
    if entity is None:
        return NotRealized("ungrounded_subject")  # defensive — graph invariant

    subject_token = entity.name
    # In-vocab gate: OOV grounding is NOT reproducible across reboots, so an OOV
    # subject cannot be realized deterministically yet (R0 scope; a substrate gap).
    try:
        ctx.vocab.index_of(subject_token)
    except (KeyError, IndexError):
        return NotRealized("oov_subject")

    # Side-effect-free embedding (no state/vault/referent mutation). Closure stays
    # algebra/versor.py's job — REALIZE adds no normalization. NOTE: the field point
    # composes with the CURRENT session state, so placement is deterministic for a
    # GIVEN session state (the fact is realized at the held self's current field
    # position), not purely subject-determined.
    try:
        field_state = ctx.probe_ingest([subject_token])
    except _GROUNDING_FAILURES:
        return NotRealized("grounding_failed")
    versor = np.asarray(field_state.F, dtype=np.float32)

    structure_canonical = graph.to_canonical_string()
    source_span = rel.span.to_canonical_string()
    content_hash = sha256_of(structure_canonical)
    status = EpistemicStatus.SPECULATIVE  # COHERENT is never a default (ADR-0021)
    replay_hash = sha256_of(
        {
            "content_hash": content_hash,
            "source_span": source_span,
            "epistemic_status": status.value,
        }
    )
    entity_names = tuple(sorted(e.name for e in graph.entities))

    # Idempotency: a re-told fact (same content_hash) does not grow the vault. Dedup
    # is exact-canonical (the content_hash is span-INCLUSIVE), so the SAFE direction
    # only — it never drops a genuinely distinct fact; it may fail to collapse the
    # same fact re-stated at a different offset (a span-free key is a later R1 option).
    # ``vault._metadata`` is read directly here (no public iterator exists yet);
    # this is the established project pattern and an intentional boundary for R0.
    for idx, meta in enumerate(ctx.vault._metadata):
        if meta.get("kind") == "realized" and meta.get("content_hash") == content_hash:
            return Realized(record=_record_from_metadata(meta, idx), created=False)

    metadata = {
        "kind": "realized",
        "structure_kind": _STRUCTURE_KIND_MEANING_GRAPH,
        "structure_canonical": structure_canonical,
        "relation_predicate": rel.predicate,
        "entity_names": list(entity_names),
        "source_span": source_span,
        "content_hash": content_hash,
        "replay_hash": replay_hash,
        "tier": "session",
    }
    vault_index = ctx.vault.store(versor, metadata, epistemic_status=status)
    return Realized(
        record=RealizedRecord(
            structure_kind=_STRUCTURE_KIND_MEANING_GRAPH,
            structure_canonical=structure_canonical,
            relation_predicate=rel.predicate,
            entity_names=entity_names,
            source_span=source_span,
            content_hash=content_hash,
            replay_hash=replay_hash,
            epistemic_status=status.value,
            tier="session",
            vault_index=vault_index,
        ),
        created=True,
    )


def _record_from_metadata(meta: dict, idx: int) -> RealizedRecord:
    """Reconstruct a RealizedRecord from a stored vault metadata dict."""
    return RealizedRecord(
        structure_kind=meta.get("structure_kind", _STRUCTURE_KIND_MEANING_GRAPH),
        structure_canonical=meta.get("structure_canonical", ""),
        relation_predicate=meta.get("relation_predicate", ""),
        entity_names=tuple(meta.get("entity_names", [])),
        source_span=meta.get("source_span", ""),
        content_hash=meta.get("content_hash", ""),
        replay_hash=meta.get("replay_hash", ""),
        epistemic_status=meta.get("epistemic_status", "speculative"),
        tier=meta.get("tier", "session"),
        vault_index=idx,
    )
