"""
Alignment graph — cross-language resonance edges.

AlignmentEdge records live in a pack's alignment.jsonl alongside its
lexicon.jsonl. This module loads them into a queryable in-memory graph.

Design constraints:
  - No numpy, no algebra imports. The graph is pure schema + stdlib.
    Geometric verification belongs in tests or holonomy proofs, not here.
  - load_alignment() is the single entry point. It reads bytes, not strings,
    so the caller can checksum if needed.
  - AlignmentGraph is immutable after construction (frozen edges tuple).
"""

from __future__ import annotations

import json
from pathlib import Path

from language_packs.schema import AlignmentEdge

_DATA_DIR = Path(__file__).parent.parent / "language_packs" / "data"


class AlignmentGraph:
    """Immutable in-memory graph of AlignmentEdge records for one pack."""

    def __init__(self, edges: list[AlignmentEdge]) -> None:
        self._edges: tuple[AlignmentEdge, ...] = tuple(edges)
        # Index by source_id for O(1) lookup on hot path
        self._by_source: dict[str, list[AlignmentEdge]] = {}
        for edge in self._edges:
            self._by_source.setdefault(edge.source_id, []).append(edge)

    def __len__(self) -> int:
        return len(self._edges)

    def edges_from(self, source_id: str) -> list[AlignmentEdge]:
        """Return all edges originating from source_id."""
        return list(self._by_source.get(source_id, []))

    def aligned_pairs(self, relation_prefix: str) -> list[AlignmentEdge]:
        """Return all edges whose relation starts with relation_prefix."""
        return [
            e for e in self._edges
            if e.relation.startswith(relation_prefix)
        ]

    def get_edge(self, source_id: str, target_id: str) -> AlignmentEdge | None:
        """Return the edge between source and target, or None."""
        for edge in self._by_source.get(source_id, []):
            if edge.target_id == target_id:
                return edge
        return None

    @property
    def edges(self) -> tuple[AlignmentEdge, ...]:
        return self._edges


def _parse_edge(payload: dict) -> AlignmentEdge:
    return AlignmentEdge(
        source_id=payload["source_id"],
        target_id=payload["target_id"],
        relation=payload["relation"],
        weight=float(payload["weight"]),
        evidence_ids=tuple(payload.get("evidence_ids", [])),
    )


def load_alignment(
    pack_id: str, *, data_root: Path | None = None
) -> AlignmentGraph:
    """
    Load AlignmentEdge records from <data_root>/<pack_id>/alignment.jsonl.

    ``data_root`` defaults to the committed ``language_packs/data`` tree; pass
    an alternate root (e.g. a test-fixture copy) to read packs from elsewhere
    without forking the parser.

    Returns an empty AlignmentGraph if the file does not exist.
    This is intentional: operational_base packs (en_minimal_v1) do not
    currently carry cross-language alignment edges.
    """
    alignment_path = (data_root or _DATA_DIR) / pack_id / "alignment.jsonl"
    if not alignment_path.exists():
        return AlignmentGraph([])

    edges: list[AlignmentEdge] = []
    for line in alignment_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            edges.append(_parse_edge(json.loads(line)))
    return AlignmentGraph(edges)
