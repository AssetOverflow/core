"""Phase 3 — live contemplation pre-flight over a completed DiscoursePlan.

The Phase 1 planner (commit ``63ffd88``) builds a plan one move at a
time using local selectors (anchor → support → relation → transition
→ closure).  No selector sees the full plan; pattern-level issues
that emerge only from the *global* shape (predicate monotony, source
homogeneity, anchor-only depth on a non-BRIEF mode) slip past.

Phase 3 closes that gap with a deterministic read-only contemplation
pass that runs AFTER the planner finishes and BEFORE the renderer
fires.  Per ADR-0080 contemplation doctrine:

  * Read-only — never mutates the plan, packs, vault, teaching
    corpus, or runtime state.  Returns findings as a tuple; callers
    decide what to do with them.
  * SPECULATIVE-only — every emitted finding is stamped
    ``EpistemicStatus.SPECULATIVE`` by the schema's ``__post_init__``.
  * Deterministic replay — same plan → same findings, byte-for-byte.

The findings flow into the telemetry sink (see
``chat.telemetry``) so the offline contemplation miner (Phase 5
target) can aggregate them into reviewable evidence for pack /
teaching-corpus expansion proposals.  At no point does this module
auto-promote anything to memory — that path remains the existing
proposal-review-ratify chain.

Rules implemented in v1
-----------------------

* ``PLANNER_GAP`` — non-BRIEF mode produced a single-move plan.
  Anchor without support/relation/transition signals the substrate
  for that lemma is too thin: there are no qualifying teaching-chain
  or cross-pack facts the planner could surface.  Proposed action
  (operator-facing): widen the teaching corpus for that subject.

* ``WEAK_SURFACE`` — three or more moves in the plan share the
  same predicate.  Indicates rendered surface will repeat the same
  relational pattern (e.g. three ``belongs_to`` clauses in a row),
  which reads mechanical.  Proposed action: diversify the relation
  inventory for that subject.

* ``COVERAGE_GAP`` — every move in a multi-move plan draws from a
  single ``FactSource``.  Indicates the substrate is one-sided
  (e.g. pack-only with no teaching enrichment, or teaching-only
  with no pack anchor).  Proposed action: confirm whether the
  missing source actually has nothing on this subject, or whether
  the planner's selector ordering is leaving gold on the table.
"""

from __future__ import annotations

import hashlib
from collections import Counter

from core.contemplation.schema import (
    ContemplationEvidenceRef,
    ContemplationFinding,
    FindingKind,
)
from generate.discourse_planner import (
    DiscourseMoveKind,
    DiscoursePlan,
    ResponseMode,
)


_PREDICATE_MONOTONY_THRESHOLD = 3
"""Trigger ``WEAK_SURFACE`` when this many moves share a predicate.

Two moves with the same predicate read naturally (e.g. ``belongs_to``
twice for two domain memberships).  Three or more turns mechanical.
"""


def _plan_substrate_hash(plan: DiscoursePlan) -> str:
    """SHA-256-16 of the plan's canonical JSON.

    Used as the ``substrate_hash`` on every emitted finding so two
    contemplation passes over byte-equal plans produce byte-equal
    finding IDs.
    """
    return hashlib.sha256(plan.to_json().encode("utf-8")).hexdigest()[:16]


def _evidence_ref_for_plan(plan: DiscoursePlan) -> ContemplationEvidenceRef:
    """Single evidence ref pointing at the in-memory plan substrate."""
    return ContemplationEvidenceRef(
        source_type="discourse_plan",
        source_id="in_memory_plan",
        pointer=_plan_substrate_hash(plan),
        summary=(
            f"mode={plan.mode.value} "
            f"intent={plan.intent.tag.value} "
            f"subject={plan.intent.subject!r} "
            f"moves={len(plan.moves)}"
        ),
    )


def _rule_planner_gap(
    plan: DiscoursePlan, substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Detect anchor-only depth on a non-BRIEF mode plan.

    BRIEF mode is anchor-only by design (budget ``(1, 1)``) — no gap.
    EXPLAIN / PARAGRAPH / EXAMPLE / WALKTHROUGH plans that emit only
    an anchor signal the planner ran out of substrate for that lemma.
    """
    if plan.mode is ResponseMode.BRIEF:
        return ()
    if len(plan.moves) != 1:
        return ()
    anchor = plan.moves[0]
    if anchor.kind is not DiscourseMoveKind.ANCHOR:
        return ()
    if anchor.fact is None:
        return ()
    return (
        ContemplationFinding(
            kind=FindingKind.PLANNER_GAP,
            subject=anchor.fact.subject,
            predicate="anchor_only_depth",
            object=plan.mode.value,
            evidence_refs=(_evidence_ref_for_plan(plan),),
            proposed_action=(
                f"widen substrate for {anchor.fact.subject!r}: planner "
                f"under {plan.mode.value} mode could only surface an "
                f"anchor — no qualifying support/relation/transition "
                f"facts available.  Candidates: add teaching chains "
                f"rooted on this lemma, or add pack ``belongs_to`` "
                f"facts that the SUPPORT selector can pick up."
            ),
            substrate_hash=substrate_hash,
        ),
    )


def _rule_predicate_monotony(
    plan: DiscoursePlan, substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Detect ``>= _PREDICATE_MONOTONY_THRESHOLD`` moves sharing a predicate."""
    predicates = Counter(
        m.fact.predicate for m in plan.moves if m.fact is not None
    )
    findings: list[ContemplationFinding] = []
    for predicate, count in sorted(predicates.items()):
        if count < _PREDICATE_MONOTONY_THRESHOLD:
            continue
        # Subject for the finding is the anchor subject (or fall back
        # to the first move with a fact).  Predicate of the finding
        # itself names the issue ("predicate_repeats_in_plan"); the
        # object is the dominating predicate.
        anchor = plan.anchor()
        subject = (
            anchor.fact.subject
            if anchor is not None and anchor.fact is not None
            else next(
                (m.fact.subject for m in plan.moves if m.fact is not None),
                plan.intent.subject or "<unknown>",
            )
        )
        findings.append(
            ContemplationFinding(
                kind=FindingKind.WEAK_SURFACE,
                subject=subject,
                predicate="predicate_repeats_in_plan",
                object=predicate,
                evidence_refs=(_evidence_ref_for_plan(plan),),
                proposed_action=(
                    f"diversify relation inventory for {subject!r}: "
                    f"plan uses predicate {predicate!r} {count} times. "
                    f"Reader may perceive mechanical cadence. "
                    f"Candidates: add chains with different relations "
                    f"(grounds / requires / reveals / contrasts) so "
                    f"the planner's RELATION selector has more variety."
                ),
                substrate_hash=substrate_hash,
            )
        )
    return tuple(findings)


def _rule_source_homogeneity(
    plan: DiscoursePlan, substrate_hash: str,
) -> tuple[ContemplationFinding, ...]:
    """Detect multi-move plans where every fact-bearing move draws from
    a single ``FactSource``.

    BRIEF / single-move plans are exempt (one source by definition).
    """
    if len(plan.moves) < 2:
        return ()
    sources = Counter(
        m.fact.source for m in plan.moves if m.fact is not None
    )
    if not sources or len(sources) > 1:
        return ()
    (source, count), = sources.items()  # exactly one entry
    if count < 2:
        return ()
    anchor = plan.anchor()
    subject = (
        anchor.fact.subject
        if anchor is not None and anchor.fact is not None
        else plan.intent.subject or "<unknown>"
    )
    return (
        ContemplationFinding(
            kind=FindingKind.COVERAGE_GAP,
            subject=subject,
            predicate="single_source_plan",
            object=source.value,
            evidence_refs=(_evidence_ref_for_plan(plan),),
            proposed_action=(
                f"confirm coverage for {subject!r}: every move in this "
                f"plan draws from {source.value!r}. "
                f"Verify whether the unused sources truly carry nothing "
                f"on this subject, or whether selector ordering / "
                f"corpus structure is leaving qualifying facts unsurfaced."
            ),
            substrate_hash=substrate_hash,
        ),
    )


def contemplate_plan(plan: DiscoursePlan) -> tuple[ContemplationFinding, ...]:
    """Run every plan-level rule over *plan* and collect findings.

    Pure deterministic function: ``contemplate_plan(p) ==
    contemplate_plan(p)`` byte-identical for any plan ``p``.

    Empty plans yield no findings (nothing to reason about).
    """
    if plan.is_empty():
        return ()
    substrate_hash = _plan_substrate_hash(plan)
    findings: list[ContemplationFinding] = []
    findings.extend(_rule_planner_gap(plan, substrate_hash))
    findings.extend(_rule_predicate_monotony(plan, substrate_hash))
    findings.extend(_rule_source_homogeneity(plan, substrate_hash))
    return tuple(findings)


__all__ = [
    "contemplate_plan",
]
