"""Provenance — back-pointers from a cognitive turn to its grounding sources.

Every articulated claim must trace to at least one of:

- **pack** — the intent classifier matched a pack-defined intent rule, so the
  proposition graph is grounded in axiomatic vocabulary.
- **vault** — exact CGA recall returned one or more stored versors that
  influenced the field state during the turn.
- **teaching** — a reviewed teaching example (and its mutation proposal)
  captured a correction that shaped this turn.

A turn with no provenance is a free-floating articulation and is a structural
failure.

The Provenance object is derived from a ``CognitiveTurnResult``; it does not
mutate the result and never invents sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from generate.intent import IntentTag

if TYPE_CHECKING:
    from core.cognition.result import CognitiveTurnResult

# The three valid source kinds. Tuple (not set) so iteration order is stable.
SOURCE_KINDS: tuple[str, ...] = ("pack", "vault", "teaching")


@dataclass(frozen=True, slots=True)
class ProvenanceSource:
    """A single back-pointer to a grounding source.

    - kind: one of "pack", "vault", "teaching"
    - ref: stable string identifier (intent tag value, vault hit index,
      teaching proposal id). Stable across replay.
    """

    kind: str
    ref: str


@dataclass(frozen=True, slots=True)
class Provenance:
    """The full set of source back-pointers for one cognitive turn."""

    turn_trace_hash: str
    sources: tuple[ProvenanceSource, ...]

    @property
    def is_empty(self) -> bool:
        return not self.sources

    def kinds(self) -> tuple[str, ...]:
        """Return the sorted, deduplicated set of source kinds present."""
        return tuple(sorted({s.kind for s in self.sources}))

    def has_kind(self, kind: str) -> bool:
        return any(s.kind == kind for s in self.sources)

    def refs(self, kind: str) -> tuple[str, ...]:
        """Return all refs for a given kind, in insertion order."""
        return tuple(s.ref for s in self.sources if s.kind == kind)


def compute_provenance(result: "CognitiveTurnResult") -> Provenance:
    """Derive a Provenance record from a CognitiveTurnResult.

    Pack source: intent classifier mapped the input to a known IntentTag
                 (anything other than UNKNOWN means a pack rule matched).
    Vault source: any vault_hits indicate exact recall fired during the turn.
                  vault_hits is an int count; refs are synthetic indices
                  ("vault_hit_0", "vault_hit_1", ...) — stable because the
                  pipeline is deterministic.
    Teaching source: a reviewed teaching example produced a mutation proposal,
                     whose proposal_id is the stable back-pointer.
    """
    sources: list[ProvenanceSource] = []

    if result.intent is not None and result.intent.tag is not IntentTag.UNKNOWN:
        sources.append(ProvenanceSource(kind="pack", ref=result.intent.tag.value))

    if result.vault_hits > 0:
        for i in range(int(result.vault_hits)):
            sources.append(ProvenanceSource(kind="vault", ref=f"vault_hit_{i}"))

    if result.pack_mutation_proposal is not None:
        sources.append(
            ProvenanceSource(
                kind="teaching",
                ref=result.pack_mutation_proposal.proposal_id,
            )
        )

    return Provenance(
        turn_trace_hash=result.trace_hash,
        sources=tuple(sources),
    )
