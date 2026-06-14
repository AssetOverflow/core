"""Composition plan types — the typed structure a composer proposes (never commits).

A plan binds clause-local sub-structures into one composite that the lowering turns
into a domain proof object for an UNCHANGED sound gate. M1 lands only the logic is-a
chain. A closed join-op vocabulary is deliberately NOT introduced yet
(defer-substrate-vocab-commitment): the chain discriminates on the relational
``predicate`` it already carries, and an explicit join-op field lands only when a
second op's lowering actually dispatches on it (M3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # type-only — avoids any import cycle with the realize/determine path
    from generate.realize import RealizedRecord


@dataclass(frozen=True, slots=True)
class LogicChainPlan:
    """The logic instantiation of the plan -> lower -> verify spine: an is-a chain.

    Carries the clause-local relational roots — an optional ``member`` fact plus an
    ordered ``subset`` path. The plan proposes structure only; ``lower_logic_chain``
    turns it into a propositional theory that an UNCHANGED sound gate
    (``generate.proof_chain.entail.evaluate_entailment``) must accept. The plan never
    decides truth. Generalizes the chain previously inlined in
    ``generate/determine/determine.py::_verify_subsumption`` (byte-identical lowering).
    """

    predicate: str  # "member" | "subset"
    subject: str
    target: str
    member_fact: "RealizedRecord | None"
    subset_path: "tuple[RealizedRecord, ...]"
