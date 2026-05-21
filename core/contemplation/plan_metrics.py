"""Phase 4 — per-plan articulation telemetry metrics.

Pure-function projection of a ``DiscoursePlan`` into structured
quantitative measurements.  Mirrors Phase 3's ``plan_preflight``
contemplation:

  Phase 3 (plan_preflight)  → typed SPECULATIVE *findings* (qualitative)
  Phase 4 (plan_metrics)    → typed *measurements* (quantitative)

Both run after the planner finishes; neither mutates anything.
Findings answer "what's wrong with this plan?".  Metrics answer
"what shape does this plan have?".  Together they give downstream
consumers (offline contemplation miner, operator dashboards) the
signal they need to score plan quality across many turns.

Why a separate dataclass and not just a dict
--------------------------------------------

* **Typed boundary.**  ``PlanMetrics`` field types make the
  serialization contract explicit; a downstream consumer can't
  silently break on a renamed key.
* **Deterministic identity.**  ``frozen=True`` + ``slots=True`` +
  positional ``as_dict()`` keys means two metrics objects built from
  byte-equal plans serialize identically.  This is what lets the
  offline miner aggregate over time without "is this the same
  metric?" ambiguity.
* **Cheap.**  Computation is O(moves); no allocation per move
  beyond the dataclass itself.

Doctrine notes
--------------

Metrics are pure measurements, not opinions.  They never mutate
the plan, the runtime state, or the memory tiers.  Promotion to
memory still flows through the existing proposal-review-ratify
chain.  Where Phase 3 emits SPECULATIVE *findings* (which downstream
review may accept), Phase 4 emits raw numbers (which downstream
analytics may aggregate).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from generate.discourse_planner import (
    DiscourseMoveKind,
    DiscoursePlan,
)


@dataclass(frozen=True, slots=True)
class PlanMetrics:
    """Quantitative measurements of one ``DiscoursePlan``.

    Every field is a pure function of the plan; same plan in →
    byte-identical metrics out.  Used by Phase 5 (offline miner)
    to aggregate plan-quality signal across many turns and surface
    deeper structural patterns that single-plan contemplation
    (Phase 3) cannot see.
    """

    # ------ Structure ------

    move_count: int
    """Total moves in the plan, including those without facts (e.g.
    bridge ``TRANSITION`` moves with ``fact=None`` and ``CLOSURE``
    moves without summary facts)."""

    fact_bearing_count: int
    """Moves with ``fact is not None`` — these are the moves the
    renderer actually emits clauses for.  ``fact_bearing_count``
    < ``move_count`` indicates structural moves (bridges, closures)
    the renderer elides."""

    # ------ Move-kind distribution ------

    anchor_count: int
    support_count: int
    relation_count: int
    transition_count: int
    closure_count: int

    # ------ Diversity ------

    unique_predicates: int
    """Number of distinct predicate strings across fact-bearing moves.
    Low absolute counts paired with high move_count signal predicate
    monotony (the WEAK_SURFACE finding from Phase 3)."""

    unique_subjects: int
    """Number of distinct subject lemmas across fact-bearing moves."""

    unique_sources: int
    """Number of distinct ``FactSource`` values across fact-bearing
    moves.  ``unique_sources == 1`` with multi-move plans signals
    the COVERAGE_GAP finding from Phase 3."""

    # ------ Topic dynamics ------

    topic_shift_count: int
    """Number of consecutive-move pairs where the fact subject
    changed.  Counts transitions across the visible focus channel
    that Phase 2 reflective rendering uses; ``topic_shift_count``
    + ``pronominalization_opportunities`` + 1 (for the anchor) sums
    to ``fact_bearing_count`` minus zero-fact moves."""

    pronominalization_opportunities: int
    """Number of consecutive-move pairs where the fact subject
    repeated.  Phase 2's reflective renderer takes each opportunity
    to swap the subject token to ``it``."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "move_count": self.move_count,
            "fact_bearing_count": self.fact_bearing_count,
            "anchor_count": self.anchor_count,
            "support_count": self.support_count,
            "relation_count": self.relation_count,
            "transition_count": self.transition_count,
            "closure_count": self.closure_count,
            "unique_predicates": self.unique_predicates,
            "unique_subjects": self.unique_subjects,
            "unique_sources": self.unique_sources,
            "topic_shift_count": self.topic_shift_count,
            "pronominalization_opportunities": (
                self.pronominalization_opportunities
            ),
            # Derived ratios — included in the wire format so consumers
            # don't recompute them inconsistently.  ``None`` when undefined
            # (e.g. empty plan, single-move plan with no pairs).
            "predicate_diversity_ratio": self.predicate_diversity_ratio,
            "subject_focus_ratio": self.subject_focus_ratio,
        }

    # ---- Derived ratios ----

    @property
    def predicate_diversity_ratio(self) -> float | None:
        """``unique_predicates / fact_bearing_count`` — ``None`` when
        no fact-bearing moves (nothing to divide by).

        1.0 = every fact-bearing move uses a distinct predicate (most
        diverse).  Trending toward 0 = predicates repeating (Phase 3
        ``WEAK_SURFACE`` candidate).
        """
        if self.fact_bearing_count == 0:
            return None
        return self.unique_predicates / self.fact_bearing_count

    @property
    def subject_focus_ratio(self) -> float | None:
        """Fraction of consecutive-move pairs that held subject focus
        (i.e. the inverse of topic-shift rate).  ``None`` when there
        are no consecutive pairs (< 2 fact-bearing moves).

        1.0 = perfectly stuck on one topic (every pronominalization
        opportunity engaged).  Trending toward 0 = topic shifts on
        every move (compound or wandering plan).
        """
        total_pairs = (
            self.pronominalization_opportunities + self.topic_shift_count
        )
        if total_pairs == 0:
            return None
        return self.pronominalization_opportunities / total_pairs


def compute_plan_metrics(plan: DiscoursePlan) -> PlanMetrics:
    """Project a :class:`DiscoursePlan` into a :class:`PlanMetrics`.

    Pure deterministic function: ``compute_plan_metrics(p) ==
    compute_plan_metrics(p)`` byte-identical for any plan ``p``.

    Empty plans yield a zero-valued ``PlanMetrics`` so downstream
    consumers can use the same shape regardless of plan engagement.
    """

    if plan.is_empty():
        return PlanMetrics(
            move_count=0,
            fact_bearing_count=0,
            anchor_count=0,
            support_count=0,
            relation_count=0,
            transition_count=0,
            closure_count=0,
            unique_predicates=0,
            unique_subjects=0,
            unique_sources=0,
            topic_shift_count=0,
            pronominalization_opportunities=0,
        )

    kind_counts: Counter[DiscourseMoveKind] = Counter()
    predicates: set[str] = set()
    subjects: set[str] = set()
    sources: set[Any] = set()
    fact_bearing = 0
    prior_subject: str | None = None
    topic_shifts = 0
    pronominalizations = 0

    for move in plan.moves:
        kind_counts[move.kind] += 1
        if move.fact is None:
            # Bridge / closure-without-summary moves don't carry a
            # subject focus — they reset the channel.  Track a topic
            # shift so the focus_ratio reflects the discontinuity but
            # do NOT update prior_subject (the next fact-bearing move
            # establishes new focus from scratch).
            if prior_subject is not None:
                topic_shifts += 1
                prior_subject = None
            continue
        fact_bearing += 1
        predicates.add(move.fact.predicate)
        subjects.add(move.fact.subject)
        sources.add(move.fact.source)
        if prior_subject is not None:
            if move.fact.subject == prior_subject:
                pronominalizations += 1
            else:
                topic_shifts += 1
        prior_subject = move.fact.subject

    return PlanMetrics(
        move_count=len(plan.moves),
        fact_bearing_count=fact_bearing,
        anchor_count=kind_counts.get(DiscourseMoveKind.ANCHOR, 0),
        support_count=kind_counts.get(DiscourseMoveKind.SUPPORT, 0),
        relation_count=kind_counts.get(DiscourseMoveKind.RELATION, 0),
        transition_count=kind_counts.get(DiscourseMoveKind.TRANSITION, 0),
        closure_count=kind_counts.get(DiscourseMoveKind.CLOSURE, 0),
        unique_predicates=len(predicates),
        unique_subjects=len(subjects),
        unique_sources=len(sources),
        topic_shift_count=topic_shifts,
        pronominalization_opportunities=pronominalizations,
    )


__all__ = [
    "PlanMetrics",
    "compute_plan_metrics",
]
