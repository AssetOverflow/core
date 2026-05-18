"""teaching/promotion.py — Phase 1.2: auto-promote high-frequency
discovery cells into an operator-visible review queue.

The discovery aggregator (:mod:`teaching.gaps`) ranks
``(subject, intent)`` cells by how many DiscoveryCandidate emissions
they accumulated.  ADR-0055 emits structured evidence; the
aggregator surfaces frequency; **this module closes the loop**:
when a cell's emission count crosses a threshold, it becomes a
:class:`GapPromotion` — an explicit "author a chain for me" signal
that operators can act on without grepping raw aggregation tables.

Design constraints:

  - **Pure function of the aggregator output.**  Promotion is derived
    state — no separate persistent queue, no double-bookkeeping.
    Re-running ``promote_gaps`` on the same sink contents produces
    the same result deterministically.
  - **Threshold is explicit.**  No magic defaults.  Operators pick
    a threshold appropriate to their workload (3 is the v1 baseline:
    "three independent cold-start prompts hit this cell; author the
    chain").
  - **No content synthesis.**  A promotion records that authorship is
    *needed*; it never invents connective or object.  Only an
    operator can author a complete chain — the trust boundary that
    prevents stochastic chain-generation is preserved.
  - **Boundary-clean filter on by default.**  A gap whose only
    contributing candidates carry ``boundary_clean=False`` (refusal-
    or hedge-tainted) does not promote, since those signals may
    indicate the prompt itself violated a safety/ethics axis rather
    than a curriculum gap.  The operator can opt in to including
    tainted cells via ``include_tainted=True``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from teaching.gaps import Gap


@dataclass(frozen=True, slots=True)
class GapPromotion:
    """A ``(subject, intent)`` cell whose emission count met the
    auto-promotion threshold.

    Fields mirror :class:`teaching.gaps.Gap` for traceability, plus
    ``threshold`` so the operator can see *why* this cell promoted
    (a count of 7 at threshold 3 reads differently than 7 at 7).
    """

    subject: str
    intent: str
    count: int
    boundary_clean_count: int
    sample_candidate_ids: tuple[str, ...]
    months_seen: tuple[str, ...]
    threshold: int

    @property
    def queue_id(self) -> str:
        """Stable, deterministic identifier for this cell promotion.

        The same cell at the same threshold always produces the same
        ``queue_id`` so operators can diff queue states across
        invocations.
        """
        return f"gap:{self.intent}:{self.subject}@{self.threshold}"

    def as_dict(self) -> dict[str, object]:
        return {
            "queue_id": self.queue_id,
            "subject": self.subject,
            "intent": self.intent,
            "count": self.count,
            "boundary_clean_count": self.boundary_clean_count,
            "sample_candidate_ids": list(self.sample_candidate_ids),
            "months_seen": list(self.months_seen),
            "threshold": self.threshold,
        }


def promote_gaps(
    gaps: Iterable[Gap],
    *,
    threshold: int = 3,
    include_tainted: bool = False,
) -> tuple[GapPromotion, ...]:
    """Return the subset of *gaps* whose effective count meets *threshold*.

    Effective count:
      - When ``include_tainted=True`` (default False), the comparison
        uses :attr:`Gap.count` (every emission counts).
      - When ``include_tainted=False`` (default), the comparison uses
        :attr:`Gap.boundary_clean_count` (refusal/hedge-tainted
        emissions are excluded from the promotion decision).

    Threshold must be ``>= 1``; a threshold of zero would promote
    every observed cell and defeats the purpose of a priority queue.
    """
    if threshold < 1:
        raise ValueError(f"threshold must be >= 1 (got {threshold!r})")

    promoted: list[GapPromotion] = []
    for gap in gaps:
        effective_count = gap.count if include_tainted else gap.boundary_clean_count
        if effective_count < threshold:
            continue
        promoted.append(
            GapPromotion(
                subject=gap.subject,
                intent=gap.intent,
                count=gap.count,
                boundary_clean_count=gap.boundary_clean_count,
                sample_candidate_ids=gap.sample_candidate_ids,
                months_seen=gap.months_seen,
                threshold=threshold,
            )
        )
    # Deterministic order: highest effective count first, ties broken
    # by subject then intent — mirrors :func:`aggregate_gaps`.
    promoted.sort(
        key=lambda p: (
            -(p.count if include_tainted else p.boundary_clean_count),
            p.subject,
            p.intent,
        )
    )
    return tuple(promoted)


__all__ = ["GapPromotion", "promote_gaps"]
