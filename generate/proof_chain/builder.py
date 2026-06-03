"""ADR-0204 — Proof-graph builder (proof_chain is the binding graph's first consumer).

Translates a :class:`generate.proof_chain.model.Proof` into a
:class:`SemanticSymbolicBindingGraph`. **Structure only** — no inference rule
(``modus_ponens`` is phase 2.3 / ADR-0205). The builder constructs the DAG and
lets the ADR-0203 acyclicity guard + ADR-0132 referential-integrity checks fire at
construction; it asserts nothing about whether a step is *valid*.

Mapping (one canonical shape; every node → one symbol + one equation):

==================  ===================================
ProofNode field     Binding-graph target
==================  ===================================
``node_id``         ``SymbolBinding.symbol_id`` / ``BoundEquation.lhs_symbol_id``
``formula``→key     ``BoundEquation.rhs_canonical`` (the ROBDD canonical key)
``depends_on``      ``BoundEquation.dependencies``
``rule``            ``BoundEquation.operation_kind`` (``"premise"`` for assumptions)
==================  ===================================

Non-applicable math fields are typed placeholders (proofs have no units):
``unit_proof = PROOF_NO_UNIT``, ``admissibility_status = "pending"`` (nothing is
admitted in 2.2 — the rule check is 2.3). ``semantic_role`` uses ``"unknown"``
because the closed ADR-0132 role vocab has no ``"proposition"`` member; see
ADR-0204 §Open items.

May raise: the canonicalizer's ``LogicError`` family (malformed / out-of-regime /
budget on a node formula) and ``BindingGraphError`` (circular dependency,
referential integrity) — all refusal-first, none silently swallowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from generate.binding_graph import (
    BoundEquation,
    SemanticSymbolicBindingGraph,
    SourceSpanLink,
    SymbolBinding,
)
from generate.logic_canonical import canonicalize
from generate.proof_chain.model import Proof

#: Synthetic provenance for proofs that have no NL source span (e.g. fixtures).
PROOF_SOURCE_ID: Final[str] = "proof_chain"
PROOF_INTRODUCED_BY: Final[str] = "build_proof_graph"
#: ``unit_proof`` sentinel — units are non-applicable to propositional proof steps.
PROOF_NO_UNIT: Final[str] = "proof_step_no_unit"
#: Proposition symbols have no math role; the closed ADR-0132 vocab has no
#: "proposition" member (ADR-0204 §Open items tracks revisiting this).
_PROPOSITION_ROLE: Final[str] = "unknown"


@dataclass(frozen=True, slots=True)
class ProofGraph:
    """A built proof graph plus its designated conclusion symbol.

    ``conclusion_symbol_id`` is tracked here rather than as a ``BoundUnknown``
    in 2.2 (ADR-0135's ``question_form`` vocab does not fit "is this proven");
    conclusion typing is revisited in 2.3 when the disagreement rule operates on
    the conclusion's canonical key (ADR-0204 §Open items / ADR-0205)."""

    graph: SemanticSymbolicBindingGraph
    conclusion_symbol_id: str


def _span(formula: str) -> SourceSpanLink:
    return SourceSpanLink(
        source_id=PROOF_SOURCE_ID, start=0, end=len(formula), text=formula
    )


def build_proof_graph(proof: Proof) -> ProofGraph:
    """Build the binding graph for ``proof``. Structure only; refusal-first."""
    symbols: list[SymbolBinding] = []
    equations: list[BoundEquation] = []
    for node in proof.nodes:
        # Canonicalize the node's proposition; propagate any LogicError/regime/
        # budget refusal — a proof over a non-propositional formula refuses.
        canonical_key = canonicalize(node.formula).canonical_key
        span = _span(node.formula)
        symbols.append(
            SymbolBinding(
                symbol_id=node.node_id,
                name=node.node_id,
                semantic_role=_PROPOSITION_ROLE,
                source_span=span,
                introduced_by=PROOF_INTRODUCED_BY,
            )
        )
        equations.append(
            BoundEquation(
                lhs_symbol_id=node.node_id,
                rhs_canonical=canonical_key,
                dependencies=frozenset(node.depends_on),
                operation_kind=node.rule,
                unit_proof=PROOF_NO_UNIT,
                admissibility_status="pending",
                source_span=span,
            )
        )
    # Construction runs the ADR-0203 acyclicity guard + ADR-0132 referential
    # integrity in __post_init__ — a cyclic or dangling proof refuses HERE.
    graph = SemanticSymbolicBindingGraph(
        symbols=tuple(symbols), equations=tuple(equations)
    )
    return ProofGraph(graph=graph, conclusion_symbol_id=proof.conclusion_id)
