"""REALIZE R1c — a comprehended arithmetic structure becomes a realized vault entry.

The quantitative comprehension path (``generate/quantitative_comprehension.py``)
reads arithmetic prose into a ``SemanticSymbolicBindingGraph`` whose equations were
already admissibility-checked (unreadable input short-circuits to a ``Refusal``
upstream). This realizes that binding_graph as a SPECULATIVE, structurally-recallable
vault entry — the SECOND substrate behind the shared ``structure_kind`` record (the
first is the meaning_graph relation, R0/R1).

Correctness rests on the STRUCTURAL key, never the field versor: the binding_graph
entities (``alice``, the synthesized ``total``) are symbolic/OOV, so the placement
versor is deterministic-GIVEN-session-state (and ``total`` is a maximally-colliding
OOV name) — distinctness is carried by ``structure_key`` / ``content_hash`` +
structural recall (``recall.py``), and reboot-stability by the Shape B+ snapshot of
these exact bytes, not by re-deriving the versor.
"""

from __future__ import annotations

import numpy as np

from formation.hashing import sha256_of
from generate.binding_graph.model import SemanticSymbolicBindingGraph
from generate.meaning_graph.reader import Refusal
from generate.quantitative_comprehension import QuantComprehension
from session.context import SessionContext
from teaching.epistemic import EpistemicStatus

from .realize import _GROUNDING_FAILURES, NotRealized, Realized, _realize_structured

_STRUCTURE_KIND_BINDING_GRAPH = "binding_graph"


def _binding_graph_structure_key(bg: SemanticSymbolicBindingGraph) -> str:
    """Span-FREE structural identity of a binding graph: symbols, facts, and
    equations with source offsets stripped (the quantitative reader's spans are
    name-derived constants, so this is also source-stable). Sorted at every level
    for a canonical, order-independent key."""
    return sha256_of(
        {
            "structure_kind": _STRUCTURE_KIND_BINDING_GRAPH,
            "symbols": sorted(
                [s.symbol_id, s.semantic_role, s.unit or ""] for s in bg.symbols
            ),
            "facts": sorted([f.symbol_id, f.value, f.unit or ""] for f in bg.facts),
            "equations": sorted(
                [e.lhs_symbol_id, e.rhs_canonical, e.operation_kind, sorted(e.dependencies)]
                for e in bg.equations
            ),
        }
    )


def realize_quantitative(
    comprehension: QuantComprehension | Refusal, ctx: SessionContext
) -> Realized | NotRealized:
    """Realize an arithmetic comprehension's binding_graph into ``ctx``'s vault.

    Eligibility: a ``QuantComprehension`` (not a ``Refusal``) whose every equation is
    ``admitted``. Every ``QuantComprehension`` PRODUCED BY ``comprehend_quantitative``
    carries an admissibility-checked graph (real ``check_admissibility``; a ``Refusal``
    short-circuits unreadable input) — but the type does NOT enforce it, so this
    function RE-ASSERTS admitted-status defensively, keeping the wrong=0 floor
    independent of the caller. SPECULATIVE always (COHERENT is never a default); dedup
    by the span-free structure_key.
    """
    if isinstance(comprehension, Refusal):
        return NotRealized("refusal")
    if not isinstance(comprehension, QuantComprehension):
        return NotRealized("not_a_quant_comprehension")

    bg = comprehension.binding_graph
    if not bg.facts:
        return NotRealized("no_bound_fact")  # defensive — the reader guarantees >=1 fact
    # wrong=0 defense: realize ONLY a fully-admitted binding graph. The model permits a
    # structurally-valid graph to carry a 'pending'/'refused' equation, so re-assert
    # admitted-status here — a future non-reader constructor cannot slip a
    # dimensionally-incoherent equation into the held self (it would otherwise be
    # surfaced as-told by DETERMINE).
    if any(e.admissibility_status != "admitted" for e in bg.equations):
        return NotRealized("unadmitted_equation")

    # Placement: the asked entity's field point. Symbolic/OOV, so deterministic-
    # GIVEN-session-state, NOT subject-determined; the structural key carries
    # correctness. ``probe_ingest`` of an OOV token mutates the shared vocab via
    # insert_transient (session-scoped, excluded from the snapshot); a non-versor
    # construction raises and is caught → NotRealized.
    try:
        field_state = ctx.probe_ingest([comprehension.query.entity])
    except _GROUNDING_FAILURES:
        return NotRealized("grounding_failed")
    versor = np.asarray(field_state.F, dtype=np.float32)

    structure_canonical = bg.to_canonical_string()
    # ``sha256_of`` rejects floats (canonical-JSON contract). The binding-graph fields
    # fed here are str by the model's contract today; wrap defensively so a future
    # numeric field is a clean refusal, never an uncaught TypeError mid-write.
    try:
        content_hash = sha256_of(structure_canonical)
        structure_key = _binding_graph_structure_key(bg)
    except (TypeError, ValueError):
        return NotRealized("unhashable_structure")
    status = EpistemicStatus.SPECULATIVE
    source_spans = [f.source_span.to_canonical_string() for f in bg.facts] or [
        s.source_span.to_canonical_string() for s in bg.symbols
    ]
    source_span = ";".join(sorted(source_spans))
    replay_hash = sha256_of(
        {
            "content_hash": content_hash,
            "source_span": source_span,
            "epistemic_status": status.value,
        }
    )
    entity_names = tuple(sorted(s.name for s in bg.symbols))

    return _realize_structured(
        ctx,
        structure_kind=_STRUCTURE_KIND_BINDING_GRAPH,
        structure_canonical=structure_canonical,
        relation_predicate="",  # meaning_graph-specific; binding graphs are multi-relation
        relation_arguments=(),
        entity_names=entity_names,
        source_span=source_span,
        content_hash=content_hash,
        structure_key=structure_key,
        versor=versor,
        replay_hash=replay_hash,
        status=status,
    )
