"""teaching/oov_promotion.py — Phase 2.3: auto-promote high-frequency
OOV tokens to operator-visible PackMutationProposal candidates.

Sibling to :mod:`teaching.promotion`.  Where chain-gap promotion says
"author a chain for this (subject, intent) cell", OOV promotion says
"add this token to a lexicon pack".

Trust boundary — same as :mod:`teaching.promotion`:

  - Pure derivation from :class:`OOVGap` records.  No persistent
    queue.  Re-running ``promote_oov_gaps`` on the same sink contents
    produces the same result deterministically.
  - **No domain inference.**  The promotion does NOT recommend a
    target pack — that would require a stochastic classifier.  It
    surfaces the mounted-pack list and lets the operator decide
    which pack the token belongs in.
  - The ratified-pack-mutation path (ADR-0027 + ADR-0033 +
    :mod:`teaching.proposals`) is the only way an OOV promotion
    becomes a real pack change.  Auto-promotion never writes a
    pack file directly.
  - Boundary-clean filter on by default (matches
    :func:`teaching.promotion.promote_gaps`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS
from teaching.oov_gaps import OOVGap


@dataclass(frozen=True, slots=True)
class OOVPromotion:
    """An OOV token whose emission count met the threshold.

    Operator surface signal: "this vocabulary item has been asked
    about N times across these intent shapes; add it to one of the
    mounted packs."
    """

    token: str
    intents: tuple[str, ...]
    count: int
    boundary_clean_count: int
    sample_candidate_ids: tuple[str, ...]
    months_seen: tuple[str, ...]
    threshold: int
    suggested_packs: tuple[str, ...]

    @property
    def queue_id(self) -> str:
        """Stable, deterministic identifier — diffable across runs."""
        return f"oov:{self.token}@{self.threshold}"

    def as_dict(self) -> dict[str, object]:
        return {
            "queue_id": self.queue_id,
            "token": self.token,
            "intents": list(self.intents),
            "count": self.count,
            "boundary_clean_count": self.boundary_clean_count,
            "sample_candidate_ids": list(self.sample_candidate_ids),
            "months_seen": list(self.months_seen),
            "threshold": self.threshold,
            "suggested_packs": list(self.suggested_packs),
        }


def promote_oov_gaps(
    gaps: Iterable[OOVGap],
    *,
    threshold: int = 3,
    include_tainted: bool = False,
    suggested_packs: tuple[str, ...] = DEFAULT_RESOLVABLE_PACK_IDS,
) -> tuple[OOVPromotion, ...]:
    """Return the subset of *gaps* whose effective count meets *threshold*.

    Effective count:
      - ``include_tainted=False`` (default): boundary_clean_count gates
        the promotion.
      - ``include_tainted=True``: every emission counts.

    ``suggested_packs`` is the list of mounted-pack ids that operators
    can mutate via the reviewed-proposal path.  Defaults to the
    cross-pack resolver's mounted set; operators can pass a narrower
    list when they want the queue surface to recommend a subset.
    """
    if threshold < 1:
        raise ValueError(f"threshold must be >= 1 (got {threshold!r})")

    promoted: list[OOVPromotion] = []
    for gap in gaps:
        effective_count = gap.count if include_tainted else gap.boundary_clean_count
        if effective_count < threshold:
            continue
        promoted.append(
            OOVPromotion(
                token=gap.token,
                intents=gap.intents,
                count=gap.count,
                boundary_clean_count=gap.boundary_clean_count,
                sample_candidate_ids=gap.sample_candidate_ids,
                months_seen=gap.months_seen,
                threshold=threshold,
                suggested_packs=suggested_packs,
            )
        )
    promoted.sort(
        key=lambda p: (
            -(p.count if include_tainted else p.boundary_clean_count),
            p.token,
        )
    )
    return tuple(promoted)


__all__ = ["OOVPromotion", "promote_oov_gaps"]
