"""Logic lowering — a ``LogicChainPlan`` becomes a propositional (premises, query)
theory for the sound ROBDD gate. Extracted byte-identically from
``generate/determine/determine.py::_verify_subsumption`` (M1 parity refactor).

The lowering proposes a theory; it NEVER evaluates entailment. The caller routes the
result through the UNCHANGED ``evaluate_entailment`` gate, which re-derives validity
from scratch — so a path-construction bug here cannot produce a wrong assertion
(soundness by construction).
"""

from __future__ import annotations

from generate.composition.plan import LogicChainPlan


def lower_logic_chain(plan: LogicChainPlan) -> tuple[tuple[str, ...], str] | None:
    """Lower an is-a chain plan into a propositional ``(premises, query_atom)`` theory.

    The propositional theory labels every ``subset_path`` fact ``S`` and the
    ``member_fact`` ``M``, asserts each edge plus the sound rule that extends the chain
    (``member ∘ subset → member`` / ``subset ∘ subset → subset``), and queries the
    closure atom. It is LINEAR in the path (the facts as true atoms + the sound rule at
    each hop), so it scales.

    Returns ``None`` for a mislabeled or wrong-arity chain — refuse rather than smuggle
    a ``member`` fact in as a ``subset`` edge (``member ∘ member`` cannot be laundered
    through a corrupted path), rather than trust the callers' discipline.
    """
    predicate = plan.predicate
    subject = plan.subject
    target = plan.target
    member_fact = plan.member_fact
    subset_path = plan.subset_path

    # Soundness-by-construction (belt-and-suspenders): refuse a mislabeled / wrong-arity
    # chain here, so a corrupted path cannot verify a smuggled member fact as a subset
    # edge regardless of either caller's discipline.
    if member_fact is not None and (
        member_fact.relation_predicate != "member"
        or len(member_fact.relation_arguments) != 2
    ):
        return None
    if any(
        f.relation_predicate != "subset" or len(f.relation_arguments) != 2
        for f in subset_path
    ):
        return None

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

    return tuple(premises), query_atom
