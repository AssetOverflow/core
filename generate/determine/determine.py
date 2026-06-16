"""DETERMINE (roadmap Step 4) — reason over realized structure → the honest gear.

A question (a query-bearing ``Comprehension``) is answered ONLY from what the held
self has already REALIZED (R0/R1 structural recall) — never from the field, never
from an LLM, never from absence. The verdict is **as-told, never "verified"**: every
realizable record is SPECULATIVE, and ``ADMISSIBLE_AS_EVIDENCE = {COHERENT}``, so a
determination grounded in SPECULATIVE records carries ``basis="as_told"`` — "based on
what I was told (unverified)". Until COHERENT promotion exists (out of scope), D0
produces only ``as_told`` assertions or ``Undetermined`` refusals. No estimation, no
corpus mutation (teaching stays HITL proposal-only).

wrong=0 / soundness (open-world): D0 asserts an answer ONLY when the asked relation is
SOUNDLY entailed by realized facts — directly, by ONE-HOP relational algebra
(inverse/converse + pack-declared symmetric), by SOUND TRANSITIVE CLOSURE over a declared
strict-order predicate, or by transitive member/subset subsumption. Absence of a fact
never refutes it (open-world), so D0 never asserts an answer from missing knowledge — it
refuses (``Undetermined``). It asserts only ``answer=True``; it never asserts False.

Supported predicates are a CLOSED set for which DIRECT entailment is sound — a
realized ground fact ``p(subject, target)`` answers the asked ``p(subject, target)``:
the ``member`` relation (subsumption / "Is X a Y?") and the binary relational
predicates of ``en_core_relational_predicates_v1`` (``parent_of``, ``less_than``,
``left_of``, ``before_event`` …; see ``generate.meaning_graph.relational``). The
categorical (``subset``/``disjoint`` …) and propositional (``implies``/``or`` …)
predicates are deliberately EXCLUDED — their truth is not a stored-pair lookup, so
admitting them would be unsound. Negated questions and any predicate outside the closed
set are an honest ``Undetermined``. Beyond direct entailment, D0 applies three SOUND
extensions over the realized facts — ONE-HOP relational algebra (inverse/converse +
pack-declared symmetric; see ``generate.meaning_graph.relational``), SOUND TRANSITIVE
CLOSURE over the declared strict-order predicates (``TRANSITIVE_PREDICATES``;
``p ∘ p → p`` over the predicate's OWN edges), and transitive member/subset SUBSUMPTION —
each search-then-verified, never closed-world, never ``answer=False``.
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.composition import LogicChainPlan, lower_logic_chain
from generate.composition.lower_transitive import lower_transitive_chain
from generate.epistemic_basis import epistemic_basis as _basis
from generate.meaning_graph.reader import Comprehension, Refusal
from generate.meaning_graph.relational import (
    INVERSE_OF,
    RELATIONAL_PREDICATES,
    SYMMETRIC_PREDICATES,
    TRANSITIVE_PREDICATES,
)
from generate.realize import RealizedRecord, recall_realized
from session.context import SessionContext

#: The CLOSED set of query predicates with a SOUND DIRECT-entailment path: ``member``,
#: ``subset`` (a told ``subset(a, b)`` — "all a are b" — directly answers the asked
#: ``subset(a, b)``), plus the ground binary relational predicates. Direct entailment is
#: "a realized fact ``p(s, t)`` directly answers the asked ``p(s, t)``". The OTHER
#: categorical predicates (``disjoint`` / ``intersects`` / ``some_not``) and the
#: propositional ones stay EXCLUDED — their truth is not a stored-pair lookup.
_SUPPORTED_PREDICATES = frozenset({"member", "subset"}) | RELATIONAL_PREDICATES

#: Predicates C can answer by SOUND transitive SUBSUMPTION (is-a) chaining when direct
#: entailment misses. The only sound is-a rules are ``subset ∘ subset → subset`` and
#: ``member ∘ subset → member`` (Description-Logic subsumption). ``member ∘ member`` is
#: DELIBERATELY ABSENT: instance-of is not transitive — "Socrates is a man" + "man is a
#: species" does NOT entail "Socrates is a species". The reader's member/subset split
#: (instance-of vs subclass-of) is exactly what makes the included rules sound.
_SUBSUMPTION_PREDICATES = frozenset({"member", "subset"})

#: Bound on the realized subset-fact count the transitive search will consider. Above
#: it, transitive subsumption declines (a safe, deterministic COVERAGE refusal — never
#: an unsound answer); direct entailment is unaffected. Search-then-verify is cheap
#: (O(V+E) reachability), so this is a generous backstop, not a tight grounding budget.
_SUBSUMPTION_SUBSET_FACT_BUDGET = 4096

#: Bound on the realized edge count the transitive RELATIONAL search will consider for a
#: given strict-order predicate. Above it, transitive closure declines (a safe,
#: deterministic COVERAGE refusal — never an unsound answer); direct and one-hop
#: entailment are unaffected. Reachability is O(V+E), so this is a generous backstop.
_TRANSITIVE_EDGE_BUDGET = 4096


@dataclass(frozen=True, slots=True)
class Determined:
    """An answer reasoned from realized structure.

    ``basis`` is the epistemic standing of the grounding: ``"as_told"`` when the
    grounds are SPECULATIVE (candidate memory — the only case today), ``"verified"``
    only if every ground is admissible-as-evidence (COHERENT — not yet reachable).
    ``answer`` is the truth of the asked (possibly negated) question.
    """

    answer: bool
    basis: str
    predicate: str
    subject: str
    object: str
    grounds: tuple[RealizedRecord, ...]
    #: Which sound rule produced the answer — provenance for audit/replay. One of
    #: ``direct`` (a stored fact of the asked predicate AND direction), ``inverse`` /
    #: ``symmetric`` (a one-hop relational-algebra rule reading the stored edge in its
    #: other lawful direction), ``transitive`` (a same-predicate strict-order chain
    #: ``p ∘ p → p`` over the predicate's own edges), or ``subsumption`` (transitive is-a
    #: chaining). It does NOT affect the surface — ``render_determination`` reads only
    #: ``basis``.
    rule: str = "direct"


@dataclass(frozen=True, slots=True)
class Undetermined:
    """No honest answer (refusal). ``reason`` is for audit, not control."""

    reason: str


def determine(
    question: Comprehension | Refusal, ctx: SessionContext
) -> Determined | Undetermined:
    """Answer a membership-or-relational question from realized structure, or refuse.

    Eligibility: a query-bearing ``Comprehension`` with exactly one binary,
    non-negated query whose predicate is in the closed direct-entailment set
    (``member`` or a relational pack predicate). The answer is asserted ONLY on direct
    structural entailment by a realized fact of the SAME predicate; everything else is
    a typed ``Undetermined`` (open-world: absence never asserts a positive answer).
    """
    if isinstance(question, Refusal):
        return Undetermined("refusal")
    if not isinstance(question, Comprehension):
        return Undetermined("not_a_comprehension")
    if len(question.queries) != 1:
        return Undetermined("not_single_query")  # a determination answers one question

    query = question.queries[0]
    if query.predicate not in _SUPPORTED_PREDICATES:
        return Undetermined("unsupported_query")  # honest: closed direct-entailment set
    if len(query.arguments) != 2:
        return Undetermined("malformed_query")  # member is binary by construction
    if query.negated:
        # Realized facts are all positive (R0/R1 refuse negated relations), so a
        # negated question would only ever be answered from the positive's presence.
        # D0 declines it explicitly rather than ship an entailment path the reader
        # cannot exercise (it refuses negated membership questions upstream anyway).
        return Undetermined("negated_query_unsupported")

    predicate = query.predicate
    subject, target = query.arguments[0], query.arguments[1]

    # 1. DIRECT entailment: a realized p(subject, target) holds as-told. Exact,
    # deterministic structural recall (R1a) — never a metric call. Symmetric relations
    # (sibling_of, equal_to …) read only the stored direction here.
    direct = recall_realized(ctx, subject=subject, predicate=predicate)
    grounding = next((f for f in direct if f.relation_arguments == (subject, target)), None)
    if grounding is not None:
        return Determined(
            answer=True,
            basis=_basis((grounding,)),
            predicate=predicate,
            subject=subject,
            object=target,
            grounds=(grounding,),
        )

    # 1b. RELATIONAL one-hop entailment: a SOUND inverse/converse or symmetric rule
    # reads a stored edge in its OTHER lawful direction. Open-world (asserts only True),
    # ONE hop (no transitive chaining), structurally sound by construction — the same
    # discipline as direct entailment; never False, never an undeclared rule.
    relational = _relational_one_hop(ctx, predicate, subject, target)
    if relational is not None:
        return relational

    # 1c. TRANSITIVE relational entailment (B2): a DECLARED strict-order predicate
    # (``TRANSITIVE_PREDICATES``) may hold by SOUND transitive closure over its OWN
    # realized edges (``p ∘ p → p``), search-then-verified by the proof_chain ROBDD.
    # Open-world (asserts only True), never False, never composes another predicate's
    # edges (no transitive-through-inverse). Only fires for the declared strict orders;
    # every other predicate falls through unchanged.
    if predicate in TRANSITIVE_PREDICATES:
        transitive = _relational_transitive(ctx, predicate, subject, target)
        if transitive is not None:
            return transitive

    # 2. TRANSITIVE subsumption (C): when direct entailment misses, a member/subset
    # query may still hold by SOUND is-a chaining (member∘subset, subset∘subset) decided
    # by the sound+complete proof_chain ROBDD — NEVER member∘member.
    if predicate in _SUBSUMPTION_PREDICATES:
        chained = _determine_subsumption(ctx, predicate, subject, target)
        if chained is not None:
            return chained

    # 3. Open-world refusal — absence (no direct fact, no sound chain) never asserts a
    # positive answer and never asserts False.
    return Undetermined("ungrounded" if not direct else "not_entailed")


def _find_relational_edge(
    ctx: SessionContext, predicate: str, a: str, b: str
) -> RealizedRecord | None:
    """A realized ``predicate(a, b)`` fact (exact structural recall, R1a), or ``None``."""
    facts = recall_realized(ctx, subject=a, predicate=predicate)
    return next((f for f in facts if f.relation_arguments == (a, b)), None)


def _relational_one_hop(
    ctx: SessionContext, predicate: str, subject: str, target: str
) -> Determined | None:
    """Answer ``predicate(subject, target)`` by ONE sound relational-algebra rule, or
    ``None`` (the caller then refuses, open-world). Two rules, each reading a stored edge
    in its OTHER lawful direction:

      INVERSE/converse  ``p(subject, target)``  <=  stored ``inverse(p)(target, subject)``
      SYMMETRIC         ``p(subject, target)``  <=  stored ``p(target, subject)``

    NEVER transitive (one hop only), NEVER False (open-world), NEVER an undeclared rule:
    inverse fires only for a declared converse pair and symmetric only for a pack-declared
    symmetric predicate — so ``less_than`` is not self-inverse and ``parent_of`` is not
    symmetric.
    """
    inverse = INVERSE_OF.get(predicate)
    if inverse is not None:
        edge = _find_relational_edge(ctx, inverse, target, subject)
        if edge is not None:
            return _relational_determined(predicate, subject, target, (edge,), "inverse")
    if predicate in SYMMETRIC_PREDICATES:
        edge = _find_relational_edge(ctx, predicate, target, subject)
        if edge is not None:
            return _relational_determined(predicate, subject, target, (edge,), "symmetric")
    return None


def _relational_determined(
    predicate: str,
    subject: str,
    target: str,
    grounds: tuple[RealizedRecord, ...],
    rule: str,
) -> Determined:
    """A relational ``Determined`` — answer True, basis from the grounds' standing
    (as_told today), the grounding edge(s) recorded, the rule recorded. The SINGLE
    construction site shared by the one-hop rules (inverse/symmetric — a single stored
    edge, passed as ``(edge,)``) and the transitive rule (a chain of same-predicate
    edges), so the INV-30 scan still sees exactly ONE relational ``answer=True`` site for
    all relational rules."""
    return Determined(
        answer=True,
        basis=_basis(grounds),
        predicate=predicate,
        subject=subject,
        object=target,
        grounds=grounds,
        rule=rule,
    )


def _relational_transitive(
    ctx: SessionContext, predicate: str, subject: str, target: str
) -> Determined | None:
    """Decide ``predicate(subject, target)`` by SOUND transitive closure over the
    predicate's OWN realized edges (``p(a, b) ∧ p(b, c) ⊨ p(a, c)``), or ``None`` (the
    caller then refuses, open-world).

    Restricted to the declared strict-order predicates (``TRANSITIVE_PREDICATES``).
    Search-then-verify, mirroring ``_determine_subsumption``: BFS reachability over the
    realized ``predicate`` edges finds a simple chain ``subject → … → target`` (reusing
    ``_subset_path``'s generic BFS), then the sound+complete proof_chain ROBDD VERIFIES
    the transitive entailment. Asserts only ``answer=True``; never ``answer=False``;
    composes ONLY same-predicate edges (inverse/symmetric mixing stays one-hop). wrong=0
    is structural: only same-predicate edges are traversed AND the decider confirms it.
    """
    if predicate not in TRANSITIVE_PREDICATES:
        return None  # closed, default-off — defence in depth (the caller already gates)

    edges = recall_realized(ctx, predicate=predicate)
    if len(edges) > _TRANSITIVE_EDGE_BUDGET:
        return None  # bounded — a safe coverage refusal, never an unsound answer

    # predicate adjacency: a → [(b, fact)] over the realized ``predicate`` edges.
    adjacency: dict[str, list[tuple[str, RealizedRecord]]] = {}
    for f in edges:
        adjacency.setdefault(f.relation_arguments[0], []).append(
            (f.relation_arguments[1], f)
        )

    # ``_subset_path`` is generic BFS reachability over an adjacency map; reused here for
    # the predicate's edges. ``()`` (subject == target — strict orders are irreflexive)
    # or ``None`` (unreachable) both refuse: no fabricated reflexive / disconnected chain.
    path = _subset_path(subject, target, adjacency)
    if not path:
        return None
    return _verify_relational_transitive(predicate, subject, target, path)


def _verify_relational_transitive(
    predicate: str, subject: str, target: str, path: tuple[RealizedRecord, ...]
) -> Determined | None:
    """Verify a found transitive chain with the proof_chain ROBDD and, on ENTAILED,
    return the ``Determined`` (``rule="transitive"``). The propositional theory is LINEAR
    in the path (each edge as a true atom + ``p ∘ p → p`` instantiated per hop), so it
    scales. Returns ``None`` if the lowering refuses a corrupted path OR the decider does
    not confirm entailment (defence in depth: a path-construction bug cannot produce a
    wrong assertion)."""
    lowered = lower_transitive_chain(predicate, subject, target, path)
    if lowered is None:
        return None
    premises, query_atom = lowered

    from generate.proof_chain.entail import Entailment, evaluate_entailment

    if evaluate_entailment(premises, query_atom).outcome is not Entailment.ENTAILED:
        return None
    return _relational_determined(predicate, subject, target, path, "transitive")


def _subset_path(
    start: str, target: str, supers: dict[str, list[tuple[str, RealizedRecord]]]
) -> tuple[RealizedRecord, ...] | None:
    """The realized edge facts on a path ``start → … → target`` (≥1 edge) over the given
    adjacency map, or ``None`` if ``target`` is not reachable from ``start``. Generic BFS
    reachability — used for ``subset`` is-a edges (subsumption) AND a strict-order
    predicate's OWN edges (transitive closure). BFS, so the path is shortest; ``()`` is
    returned when ``start == target`` (the caller treats it as a non-chain); deterministic
    (neighbours are visited in sorted order)."""
    if start == target:
        return ()
    frontier: list[str] = [start]
    came_from: dict[str, tuple[str, RealizedRecord]] = {}
    seen = {start}
    while frontier:
        node = frontier.pop(0)
        for nxt, fact in sorted(supers.get(node, ()), key=lambda e: e[0]):
            if nxt in seen:
                continue
            came_from[nxt] = (node, fact)
            if nxt == target:
                chain: list[RealizedRecord] = []
                cur = target
                while cur != start:
                    prev, fact = came_from[cur]
                    chain.append(fact)
                    cur = prev
                return tuple(reversed(chain))
            seen.add(nxt)
            frontier.append(nxt)
    return None


def _determine_subsumption(
    ctx: SessionContext, predicate: str, subject: str, target: str
) -> Determined | None:
    """Decide a member/subset query by SOUND transitive is-a chaining, or ``None`` when
    no sound chain entails it (the caller then refuses, open-world).

    Search-then-verify. Reachability over the SOUND is-a edges finds a candidate chain —
    ``subset ∘ subset`` for a subset query, ``member ∘ subset*`` for a member query —
    then the proof_chain ROBDD VERIFIES that chain's propositional entailment (O(path)
    premises; full O(n³) grounding overruns the canonicalizer, and transitive closure is
    reachability, not general SAT). ``member ∘ member`` is NEVER an edge, so the
    instance-of fallacy ("Socrates is a man" + "man is a species" ⊬ "Socrates is a
    species") is unreachable. wrong=0 is structural: only sound edges are traversed AND
    the sound+complete decider confirms the derivation.
    """
    subsets = recall_realized(ctx, predicate="subset")
    if len(subsets) > _SUBSUMPTION_SUBSET_FACT_BUDGET:
        return None  # bounded — a safe coverage refusal, never an unsound answer

    # subset adjacency: class → [(superclass, fact)], the subclass-of edges.
    supers: dict[str, list[tuple[str, RealizedRecord]]] = {}
    for f in subsets:
        supers.setdefault(f.relation_arguments[0], []).append(
            (f.relation_arguments[1], f)
        )

    if predicate == "subset":
        path = _subset_path(subject, target, supers)
        if not path:  # None (unreachable) or () (start==target, not a real subset claim)
            return None
        return _verify_subsumption(predicate, subject, target, member_fact=None, subset_path=path)

    # member query: a direct membership ``member(subject, b)`` reaches ``target`` iff
    # ``b`` subsumes to ``target`` over subset edges (member ∘ subset*).
    for m in recall_realized(ctx, subject=subject, predicate="member"):
        b = m.relation_arguments[1]
        sub_path = _subset_path(b, target, supers)
        if sub_path:  # ≥1 subset edge from b to target (b == target is the direct case)
            verdict = _verify_subsumption(
                predicate, subject, target, member_fact=m, subset_path=sub_path
            )
            if verdict is not None:
                return verdict
    return None


def _verify_subsumption(
    predicate: str,
    subject: str,
    target: str,
    *,
    member_fact: RealizedRecord | None,
    subset_path: tuple[RealizedRecord, ...],
) -> Determined | None:
    """Verify a found is-a chain with the proof_chain ROBDD and, on ENTAILED, return the
    Determined. The propositional theory is LINEAR in the path (the facts on the chain as
    true atoms + the sound rule instantiated at each hop), so it scales — unlike the full
    closure grounding. Returns ``None`` if the decider does not confirm entailment
    (defence in depth: a path-construction bug cannot produce a wrong assertion)."""
    # Soundness-by-construction (belt-and-suspenders): the propositional theory below
    # labels every ``subset_path`` fact ``S`` and the ``member_fact`` ``M``. Both callers
    # (``_determine_subsumption`` and ``consolidate``) build these from predicate-filtered
    # recalls, so the labels match — the lowering refuses a mislabeled / wrong-arity
    # chain (``member ∘ member`` cannot be laundered through a corrupted path).
    plan = LogicChainPlan(
        predicate=predicate,
        subject=subject,
        target=target,
        member_fact=member_fact,
        subset_path=subset_path,
    )
    lowered = lower_logic_chain(plan)
    if lowered is None:
        return None
    premises, query_atom = lowered

    from generate.proof_chain.entail import Entailment, evaluate_entailment

    if evaluate_entailment(premises, query_atom).outcome is not Entailment.ENTAILED:
        return None

    grounds = ((member_fact,) if member_fact is not None else ()) + subset_path
    return Determined(
        answer=True,
        basis=_basis(grounds),
        predicate=predicate,
        subject=subject,
        object=target,
        grounds=grounds,
        rule="subsumption",
    )
