"""D — CLOSE (roadmap Step 5): idle deductive consolidation of derived facts.

The loop "learns from determined facts." Between turns, ``consolidate_once`` runs ONE
semi-naive layer of the member/subset deductive closure over the held self: for every
sound one-hop is-a inference whose conclusion is not yet realized, it VERIFIES the hop
with the sound+complete proof_chain ROBDD (reusing C's single verifier — no duplicate
proof logic) and writes the conclusion as a SPECULATIVE realized record carrying
derived-provenance (``generate.realize.realize_derived``). The next ``determine``
reaches the conclusion directly, and a later hop can chain off it — so the directly
answerable set climbs monotonically across idle ticks to the deductive-closure fixed
point, where a further tick is a no-op.

The only sound is-a rules are ``member ∘ subset → member`` and ``subset ∘ subset →
subset`` (Description-Logic subsumption). ``member ∘ member`` is NEVER an edge —
instance-of is not transitive ("Socrates is a man" + "man is a species" ⊬ "Socrates is
a species"). A consolidated ``member(s, t)`` is a member fact, extendable ONLY by a
subset edge, so the fallacy stays structurally unreachable across iterations.

wrong=0: every consolidated fact is the conclusion of a sound rule over realized
premises AND confirmed by the sound+complete decider (defence in depth). Honesty: a
fact derived from SPECULATIVE premises stays SPECULATIVE / as-told — the soundness of
the inference never upgrades the standing of the premises (COHERENT is never minted).
Boundary: SESSION memory (immediate, allowed), an extension of the ``generate.realize``
path — NOT reviewed/corpus learning and NOT coupled to proposals; the teaching/review
HITL path is untouched (no parallel learning path).

Determinism: a pure function of the current realized set. Candidates are consolidated
in sorted ``(predicate, subject, object)`` order, so the vault write order — and thus
the replayed structure — is independent of recall order. No clock, no LLM, no metric
call. Bounded by the same ``_SUBSUMPTION_SUBSET_FACT_BUDGET`` as the transitive search.
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.determine.determine import (
    _SUBSUMPTION_SUBSET_FACT_BUDGET,
    Determined,
    _verify_subsumption,
)
from generate.realize import RealizedRecord, Realized, realize_derived, recall_realized
from session.context import SessionContext

#: Rule label stamped on the derived record's provenance, keyed by the conclusion's
#: predicate. ``member`` conclusions come from ``member ∘ subset``; ``subset``
#: conclusions from ``subset ∘ subset``. (``member ∘ member`` is not a rule.)
_RULE_FOR_PREDICATE = {"member": "member_subset", "subset": "subset_subset"}


@dataclass(frozen=True, slots=True)
class ConsolidationResult:
    """Outcome of one idle consolidation layer.

    ``considered`` — one-hop conclusions not already realized (this tick's frontier).
    ``consolidated`` — conclusions newly written as derived realized records.
    ``redundant`` — verified conclusions that dedup-hit an existing record (defensive;
    the frontier already excludes present facts).
    ``at_fixed_point`` — True iff nothing new was consolidated (the closure is
    saturated; re-running is a no-op).
    ``budget_exceeded`` — True iff the realized subset-fact count exceeded the bound, so
    the layer safely declined (a coverage backstop, never an unsound write).
    """

    considered: int
    consolidated: int
    redundant: int
    at_fixed_point: bool
    budget_exceeded: bool = False


def _one_hop_candidates(
    member_facts: tuple[RealizedRecord, ...],
    subset_facts: tuple[RealizedRecord, ...],
) -> list[tuple[str, str, str, RealizedRecord | None, tuple[RealizedRecord, ...]]]:
    """Enumerate the sound one-hop conclusions NOT already realized.

    Returns ``(predicate, subject, object, member_fact, subset_path)`` tuples ready for
    ``_verify_subsumption``. A ``member`` candidate carries its seed member fact and a
    one-edge subset path; a ``subset`` candidate carries a two-edge subset path and no
    member fact. Reflexive conclusions (subject == object) are excluded — they are not
    real subsumption claims.
    """
    existing: set[tuple[str, str, str]] = set()
    for f in member_facts:
        if len(f.relation_arguments) == 2:
            existing.add(("member", f.relation_arguments[0], f.relation_arguments[1]))
    for f in subset_facts:
        if len(f.relation_arguments) == 2:
            existing.add(("subset", f.relation_arguments[0], f.relation_arguments[1]))

    # subset adjacency: class → [(superclass, fact)] — the subclass-of edges.
    supers: dict[str, list[tuple[str, RealizedRecord]]] = {}
    for f in subset_facts:
        if len(f.relation_arguments) == 2:
            supers.setdefault(f.relation_arguments[0], []).append(
                (f.relation_arguments[1], f)
            )

    out: list[
        tuple[str, str, str, RealizedRecord | None, tuple[RealizedRecord, ...]]
    ] = []

    # member ∘ subset → member: member(s, b) + subset(b, t) ⊢ member(s, t).
    for m in member_facts:
        if len(m.relation_arguments) != 2:
            continue
        s, b = m.relation_arguments
        for t, sub_fact in supers.get(b, ()):
            if s == t:
                continue
            if ("member", s, t) not in existing:
                out.append(("member", s, t, m, (sub_fact,)))

    # subset ∘ subset → subset: subset(a, b) + subset(b, t) ⊢ subset(a, t).
    for f in subset_facts:
        if len(f.relation_arguments) != 2:
            continue
        a, b = f.relation_arguments
        for t, sub_fact in supers.get(b, ()):
            if a == t:
                continue
            if ("subset", a, t) not in existing:
                out.append(("subset", a, t, None, (f, sub_fact)))

    return out


def consolidate_once(
    ctx: SessionContext, *, fact_budget: int = _SUBSUMPTION_SUBSET_FACT_BUDGET
) -> ConsolidationResult:
    """Consolidate one semi-naive layer of the member/subset deductive closure.

    Reads the realized member + subset facts present NOW, derives every sound one-hop
    conclusion not yet realized, proof_chain-verifies each, and writes the verified ones
    as derived realized records. Facts written this tick are NOT re-read this tick — the
    next layer derives off them next tick (semi-naive evaluation → monotone climb).
    """
    member_facts = recall_realized(ctx, predicate="member")
    subset_facts = recall_realized(ctx, predicate="subset")
    if len(subset_facts) > fact_budget:
        # Bounded — a safe coverage decline, never an unsound write.
        return ConsolidationResult(
            considered=0,
            consolidated=0,
            redundant=0,
            at_fixed_point=False,
            budget_exceeded=True,
        )

    candidates = _one_hop_candidates(member_facts, subset_facts)
    # Deterministic write order, independent of recall order.
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))

    consolidated = 0
    redundant = 0
    for predicate, subject, obj, member_fact, subset_path in candidates:
        verdict = _verify_subsumption(
            predicate, subject, obj, member_fact=member_fact, subset_path=subset_path
        )
        if not isinstance(verdict, Determined):
            # The sound+complete decider did not confirm the hop — never write
            # (defence in depth: a candidate-construction bug cannot consolidate a
            # wrong fact).
            continue
        premise_keys = tuple(g.structure_key for g in verdict.grounds)
        outcome = realize_derived(
            ctx,
            predicate=predicate,
            subject=subject,
            obj=obj,
            rule=_RULE_FOR_PREDICATE[predicate],
            premise_structure_keys=premise_keys,
        )
        if isinstance(outcome, Realized):
            if outcome.created:
                consolidated += 1
            else:
                redundant += 1

    return ConsolidationResult(
        considered=len(candidates),
        consolidated=consolidated,
        redundant=redundant,
        at_fixed_point=consolidated == 0,
    )


__all__ = ["ConsolidationResult", "consolidate_once"]
