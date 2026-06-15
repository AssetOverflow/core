"""Transitive-chain lowering — a strict-order chain ``p(subject → … → target)`` becomes
a propositional ``(premises, query)`` theory for the sound ROBDD gate. The sibling of
``lower_logic.py`` for relational transitivity.

The lowering proposes a theory; it NEVER evaluates entailment. The caller routes the
result through the UNCHANGED ``evaluate_entailment`` gate, which re-derives validity from
scratch — so a path-construction bug here cannot produce a wrong assertion (soundness by
construction). Mirrors ``lower_logic_chain``'s ``subset ∘ subset`` branch, parameterized
by predicate: the only structural difference is the rule (``p ∘ p → p`` for any declared
transitive ``p``, vs. the is-a rules).
"""

from __future__ import annotations

from generate.realize import RealizedRecord


def lower_transitive_chain(
    predicate: str,
    subject: str,
    target: str,
    path: tuple[RealizedRecord, ...],
) -> tuple[tuple[str, ...], str] | None:
    """Lower a transitive strict-order chain into a propositional ``(premises,
    query_atom)`` theory: each edge ``p(cur, nxt)`` asserted as a true atom + the
    transitivity rule ``p ∘ p → p`` instantiated at each hop, querying the closure atom
    ``p(subject, target)``. LINEAR in the path, so it scales.

    Returns ``None`` — refuse rather than smuggle a fabricated closure through a corrupted
    path, regardless of the caller's discipline — for any of:

      * an empty path (no chain);
      * a mislabeled / wrong-arity edge (a fact whose predicate is not ``predicate`` or
        whose arity is not 2 — a cross-predicate edge cannot be laundered in);
      * a NON-CONTIGUOUS chain (the edges do not form ``subject → … → target``).
    """
    if not path:
        return None
    if any(
        f.relation_predicate != predicate or len(f.relation_arguments) != 2
        for f in path
    ):
        return None

    atoms: dict[tuple[str, str], str] = {}

    def atom(a: str, b: str) -> str:
        key = (a, b)
        name = atoms.get(key)
        if name is None:
            name = f"x{len(atoms)}"
            atoms[key] = name
        return name

    premises: list[str] = []
    cur = subject
    for hop, fact in enumerate(path):
        a, b = fact.relation_arguments
        if a != cur:  # non-contiguous: the chain does not continue from ``cur``
            return None
        premises.append(atom(cur, b))  # p(cur, b) is told
        if hop > 0:  # extend the accumulated closure p(subject, cur) with this edge
            premises.append(  # p ∘ p → p
                f"({atom(subject, cur)} & {atom(cur, b)}) -> {atom(subject, b)}"
            )
        cur = b
    if cur != target:  # the chain does not reach ``target``
        return None

    return tuple(premises), atom(subject, target)
