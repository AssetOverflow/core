"""MeaningGraph — the neutral general-meaning interlingua (Phase 2a, COMPREHEND).

The refusal-first, provenance-carrying structure that the field-decode produces
and the domain reasoners project from. Sibling of the binding-graph (ADR-0132):
where the binding-graph carries quantity/equation meaning, the MeaningGraph
carries GENERAL meaning — entities and n-ary named relations — and stays neutral
to the engine substrate (no algebra/field import) so two independent decodings
can meet there honestly.
"""

from __future__ import annotations

from generate.meaning_graph.model import (
    Entity,
    MeaningGraph,
    MeaningGraphError,
    MeaningSpan,
    Relation,
)

__all__ = [
    "Entity",
    "MeaningGraph",
    "MeaningGraphError",
    "MeaningSpan",
    "Relation",
]
