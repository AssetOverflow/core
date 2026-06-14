"""Compositional reading spine (plan -> lower -> verify).

The comprehension organ recognizes individual structures but cannot COMPOSE them
across a unit/structure/referent boundary — the proven coverage wall
(``docs/analysis/comprehension-coverage-wall-map-2026-06-14.md``). This package is the
fix: a deterministic stage that builds a typed composition *plan* from clause-local
sub-structures, LOWERS it into a domain's existing proof object, and routes that object
UNCHANGED through the domain's existing sound gate. The composition layer has zero
authority to commit an answer — the unchanged, from-scratch re-deriving gate is the
sole wrong=0 firewall.

The spine is intended to be domain-general (one ``lower(plan) -> proof_object`` per
domain, each over the same plan core), but **M1 ships the LOGIC instantiation only**:
it generalizes the is-a chain previously inlined in
``generate/determine/determine.py::_verify_subsumption`` into a reusable
``LogicChainPlan`` + ``lower_logic_chain``, byte-identical to the original (a parity
refactor — no new capability). The math instantiation (``lower_math_plan`` over a
``GroundedDerivation``) and additional join-ops land in later phases, one op per PR,
each behind a grounded case + a mutation test that the gate refuses a mis-licensed
edge. Discipline: CLAUDE.md (Schema-Defined Proof Obligations,
defer-substrate-vocab-commitment).
"""

from generate.composition.lower_logic import lower_logic_chain
from generate.composition.plan import LogicChainPlan

__all__ = ["LogicChainPlan", "lower_logic_chain"]
