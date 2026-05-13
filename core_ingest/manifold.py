"""
SegmentManifold — reconstruction index for pre-injection provenance.

Maps semantic_key -> list of SourceSpan positions in source documents.

Purpose: given a vault recall hit on a semantic_key, recover the exact
provenance spans in the original source documents. This extends
Reconstruction-over-Storage to the pre-injection layer — we do not store
full document copies; we store enough structured provenance to reconstruct
the relevant span on demand.

The manifold is append-only. Entries are never modified or deleted.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from core_ingest.types import CandidateGeometricPressure, SourceSpan


@dataclass(frozen=True, slots=True)
class ManifoldEntry:
    """
    A single provenance record in the SegmentManifold.

    semantic_key  — SHA-256 over semantic fields; shared by packets asserting
                    the same claim
    pressure_id   — SHA-256 over the full packet; unique per structural variant
    spans         — provenance spans from the packet
    instrument_id — identity of the proposing instrument
    """
    semantic_key:  str
    pressure_id:   str
    spans:         tuple[SourceSpan, ...]
    instrument_id: str

    def __getattr__(self, name: str):
        if name in {"byte_start", "byte_end", "source_sha256", "page", "region"} and self.spans:
            return getattr(self.spans[0], name)
        raise AttributeError(name)


class SegmentManifold:
    """
    Append-only index: semantic_key -> list[ManifoldEntry].

    Usage
    -----
    manifold = SegmentManifold()
    manifold.register(packets)          # register a batch after compilation
    entries = manifold.lookup(sk)       # retrieve all entries for a semantic_key
    spans   = manifold.spans_for(sk)    # retrieve all SourceSpans for a key
    """

    def __init__(self) -> None:
        self._index: dict[str, list[ManifoldEntry]] = defaultdict(list)

    def register(
        self,
        packets: Sequence[CandidateGeometricPressure],
    ) -> None:
        """
        Register a batch of packets into the manifold.

        Typically called with the accepted packets after IngestCompiler.compile().
        Can also be called with the full batch to index all attempted ingest;
        the caller decides the registration policy.
        """
        for packet in packets:
            entry = ManifoldEntry(
                semantic_key=packet.semantic_key,
                pressure_id=packet.pressure_id,
                spans=packet.provenance,
                instrument_id=packet.frontend.instrument_id,
            )
            self._index[packet.semantic_key].append(entry)

    def record(self, packet: CandidateGeometricPressure) -> None:
        """Register one packet into the manifold."""
        self.register([packet])

    def lookup(self, semantic_key: str) -> list[ManifoldEntry]:
        """
        Return all ManifoldEntry records for a given semantic_key.
        Returns an empty list if the key is not indexed.
        """
        return list(self._index.get(semantic_key, []))

    def spans_for(self, semantic_key: str) -> list[SourceSpan]:
        """
        Return all SourceSpan records for a given semantic_key,
        flattened across all ManifoldEntry records.
        """
        spans: list[SourceSpan] = []
        for entry in self._index.get(semantic_key, []):
            spans.extend(entry.spans)
        return spans

    def __len__(self) -> int:
        """Return the number of distinct semantic_keys indexed."""
        return len(self._index)

    def __contains__(self, semantic_key: str) -> bool:
        return semantic_key in self._index
