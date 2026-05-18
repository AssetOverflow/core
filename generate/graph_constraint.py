"""
generate/graph_constraint.py — PropositionGraph as forward AdmissibilityRegion.

This module closes the structural gap identified 2026-05-17:

  Before: PropositionGraph was built AFTER generate() ran, from
          the walk's nearest-node results.  It described what the
          field already produced.

  After:  PropositionGraph is converted into an AdmissibilityRegion
          BEFORE generate() runs.  The region constrains which vocab
          indices the walk may visit, derived purely from the CGA
          geometry of the graph's named nodes.

This is the Pillar 1 → Pillar 2 → Pillar 3 coupling:
  geometry (CGA versor neighbourhood) →
  structure (PropositionGraph nodes) →
  propagation (AdmissibilityRegion fed to generate())

Design constraints (matching the seven axioms):
  - Geometry-first: the allowed set is determined by CGA inner product
    against node versors, not by string matching or rule lists.
  - Propagation-over-mutation: the region is computed once before
    propagation begins; nothing inside generate() is mutated.
  - Dual-correction: an empty graph returns an unconstrained region
    (identity / pass-through) so the caller's fallback path is safe.
  - Reconstruction-over-storage: the region encodes the constraint
    lightly (an index set + label); it does not store every versor.
  - Compilation-last: no tensors, no kernels — the index set is a
    plain frozenset until AdmissibilityRegion wraps it.
"""

from __future__ import annotations

import numpy as np

from algebra.cga import cga_inner
from generate.admissibility import AdmissibilityRegion, RegionSource
from generate.graph_planner import PropositionGraph

_DEFAULT_TOP_K = 8


def _node_versors(
    graph: PropositionGraph,
    vocab,
) -> list[np.ndarray]:
    """Collect CGA versors for every named surface in the graph.

    Checks subject, predicate, and obj for each node.  Surfaces not in
    vocabulary are silently skipped — the constraint degrades gracefully
    rather than raising on OOV nodes.
    """
    versors: list[np.ndarray] = []
    seen: set[str] = set()
    for node in graph.nodes:
        for surface in (node.subject, node.predicate, node.obj):
            surface = surface.strip().casefold()
            if not surface or surface in seen or surface.startswith("<"):
                continue
            seen.add(surface)
            try:
                v = vocab.get_versor(surface)
                versors.append(np.asarray(v, dtype=np.float32))
            except KeyError:
                continue
    return versors


def _neighbourhood_indices(
    node_versors: list[np.ndarray],
    vocab,
    top_k: int,
) -> frozenset[int]:
    """Union the top-k CGA-nearest indices for each node versor.

    For each anchor versor, scan the vocabulary and collect the
    top_k indices with the highest cga_inner score.  Union all
    neighbourhoods — the region allows any index that is close to
    ANY named graph node.

    This is an exact scan (O(|vocab| * |nodes|)).  Vocab sizes in
    CORE are bounded (language packs, not embedding tables), so this
    is fast in practice.
    """
    indices: set[int] = set()
    n = len(vocab)
    for anchor in node_versors:
        scores: list[tuple[float, int]] = []
        for idx in range(n):
            v = vocab.get_versor_at(idx)
            score = float(cga_inner(np.asarray(v, dtype=np.float32), anchor))
            scores.append((score, idx))
        scores.sort(key=lambda x: -x[0])
        for score, idx in scores[:top_k]:
            if score > 0.0:
                indices.add(idx)
    return frozenset(indices)


def _constraint_label(graph: PropositionGraph) -> str:
    """Stable label encoding the graph's root node IDs."""
    roots = graph.roots()
    if not roots:
        roots = tuple(n.node_id for n in graph.nodes)
    return "graph:" + ",".join(sorted(roots))


def build_graph_constraint(
    graph: PropositionGraph,
    vocab,
    *,
    top_k: int = _DEFAULT_TOP_K,
) -> AdmissibilityRegion:
    """Convert a PropositionGraph into an AdmissibilityRegion.

    The region's allowed_indices is the union of the CGA top-k
    neighbourhoods of every named surface in the graph.  The walk
    is constrained to visit only indices in this set.

    Empty graph (no nodes, or all OOV nodes) → unconstrained region.
    This preserves the existing fallback contract: unknown-domain
    inputs that produce empty graphs get the full vocab walk, not
    a zero-index set that would trigger immediate exhaustion.

    Parameters
    ----------
    graph : PropositionGraph
        The graph whose named nodes define the constraint geometry.
    vocab : Vocabulary
        The vocabulary over which index neighbourhoods are computed.
    top_k : int
        Number of nearest vocab indices to admit per node versor.
        Default 8 — keeps the constraint meaningful (< full vocab)
        while allowing sufficient combinatorial freedom for fluent
        token sequences.
    """
    node_versors = _node_versors(graph, vocab)
    if not node_versors:
        # Empty or fully OOV graph → unconstrained (safe passthrough).
        return AdmissibilityRegion(
            allowed_indices=None,
            label="graph:unconstrained",
            source=RegionSource.INTENT,
        )

    allowed = _neighbourhood_indices(node_versors, vocab, top_k)
    if not allowed:
        return AdmissibilityRegion(
            allowed_indices=None,
            label="graph:unconstrained",
            source=RegionSource.INTENT,
        )

    return AdmissibilityRegion(
        allowed_indices=np.asarray(sorted(allowed), dtype=np.int64),
        label=_constraint_label(graph),
        source=RegionSource.INTENT,
    )
