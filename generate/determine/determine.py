"""DETERMINE (roadmap Step 4) — reason over realized structure → the honest gear.

A question (a query-bearing ``Comprehension``) is answered ONLY from what the held
self has already REALIZED (R0/R1 structural recall) — never from the field, never
from an LLM, never from absence. The verdict is **as-told, never "verified"**: every
realizable record is SPECULATIVE, and ``ADMISSIBLE_AS_EVIDENCE = {COHERENT}``, so a
determination grounded in SPECULATIVE records carries ``basis="as_told"`` — "based on
what I was told (unverified)". Until COHERENT promotion exists (out of scope), D0
produces only ``as_told`` assertions or ``Undetermined`` refusals. No estimation, no
corpus mutation (teaching stays HITL proposal-only).

wrong=0 / soundness (open-world): D0 asserts an answer ONLY when the asked relation
is DIRECTLY entailed by a realized fact. Absence of a fact never refutes it
(open-world), so D0 never asserts an answer from missing knowledge — it refuses
(``Undetermined``). It asserts only ``answer=True`` on a direct hit; it never asserts
False.

Supported predicates are a CLOSED set for which DIRECT entailment is sound — a
realized ground fact ``p(subject, target)`` answers the asked ``p(subject, target)``:
the ``member`` relation (subsumption / "Is X a Y?") and the binary relational
predicates of ``en_core_relational_predicates_v1`` (``parent_of``, ``less_than``,
``left_of``, ``before_event`` …; see ``generate.meaning_graph.relational``). The
categorical (``subset``/``disjoint`` …) and propositional (``implies``/``or`` …)
predicates are deliberately EXCLUDED — their truth is not a stored-pair lookup, so
admitting them would be unsound. Negated questions, symmetric-converse questions, and
any predicate outside the closed set are an honest ``Undetermined`` — D0 ships no
entailment path it cannot exercise (no transitive/symmetric/rule inference).
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.meaning_graph.reader import Comprehension, Refusal
from generate.meaning_graph.relational import RELATIONAL_PREDICATES
from generate.realize import RealizedRecord, recall_realized
from session.context import SessionContext
from teaching.epistemic import ADMISSIBLE_AS_EVIDENCE, EpistemicStatus

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


@dataclass(frozen=True, slots=True)
class Undetermined:
    """No honest answer (refusal). ``reason`` is for audit, not control."""

    reason: str


def _basis(grounds: tuple[RealizedRecord, ...]) -> str:
    """Carry the grounds' epistemic standing forward — never overclaim "verified"."""
    statuses = {EpistemicStatus(g.epistemic_status) for g in grounds}
    return "verified" if statuses and statuses <= ADMISSIBLE_AS_EVIDENCE else "as_told"


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


def _subset_path(
    start: str, target: str, supers: dict[str, list[tuple[str, RealizedRecord]]]
) -> tuple[RealizedRecord, ...] | None:
    """The realized ``subset`` facts on a path ``start → … → target`` (≥1 edge), or
    ``None`` if ``target`` is not reachable from ``start`` over the subset edges. BFS,
    so the path is shortest; deterministic (neighbours are visited in sorted order)."""
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
    atoms: dict[tuple[str, str, str], str] = {}

    def atom(p: str, a: str, b: str) -> str:
        key = (p, a, b)
        name = atoms.get(key)
        if name is None:
            name = f"x{len(atoms)}"
            atoms[key] = name
        return name

    premises: list[str] = []
    # Walk the subset path, asserting each edge and the sound rule that extends the chain.
    if predicate == "member":
        assert member_fact is not None
        cur = member_fact.relation_arguments[1]
        premises.append(atom("M", subject, cur))  # member(subject, b) is told
        for fact in subset_path:
            nxt = fact.relation_arguments[1]
            premises.append(atom("S", cur, nxt))  # subset(cur, nxt) is told
            premises.append(  # member ∘ subset → member
                f"({atom('M', subject, cur)} & {atom('S', cur, nxt)}) -> {atom('M', subject, nxt)}"
            )
            cur = nxt
        query_atom = atom("M", subject, target)
    else:
        cur = subject
        for hop, fact in enumerate(subset_path):
            nxt = fact.relation_arguments[1]
            premises.append(atom("S", cur, nxt))  # subset(cur, nxt) is told
            if hop > 0:  # the first told edge IS the accumulator S_subject_c1; extend it
                premises.append(  # subset ∘ subset → subset
                    f"({atom('S', subject, cur)} & {atom('S', cur, nxt)}) -> {atom('S', subject, nxt)}"
                )
            cur = nxt
        query_atom = atom("S", subject, target)

    from generate.proof_chain.entail import Entailment, evaluate_entailment

    if evaluate_entailment(tuple(premises), query_atom).outcome is not Entailment.ENTAILED:
        return None

    grounds = ((member_fact,) if member_fact is not None else ()) + subset_path
    return Determined(
        answer=True,
        basis=_basis(grounds),
        predicate=predicate,
        subject=subject,
        object=target,
        grounds=grounds,
    )
