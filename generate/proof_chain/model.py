"""ADR-0204 — Proof input model (the one canonical proof shape).

A ``Proof`` is the single committed input representation for proof_chain — the
corpus surface shapes (``proof_nodes``/``depends_on``/``conclusion_node`` and
``premises``/``conclusion``/``rule``) desugar onto it, so proof input never
becomes a second dialect (same discipline ADR-0202 applies to formulas).

Pure data — no canonicalizer, no binding graph. :func:`generate.proof_chain.builder`
translates a ``Proof`` into a ``SemanticSymbolicBindingGraph``.

Honesty boundary (load-bearing through phase 2.3): proof_chain is **sound over its
declared atoms**, not grounded in recognized input. This module declares structure
only.
"""

from __future__ import annotations

from dataclasses import dataclass


class ProofError(ValueError):
    """Raised on malformed proof input. Refusal-first; never coerces."""


@dataclass(frozen=True, slots=True)
class ProofNode:
    """One node of a proof DAG.

    ``node_id`` becomes the binding-graph ``symbol_id`` / ``lhs_symbol_id`` and so
    must be a Python identifier. ``formula`` is an ADR-0202 propositional string.
    ``depends_on`` names the nodes this one is derived from (→ the equation's
    ``dependencies``). ``rule`` is the inference label (→ ``operation_kind``);
    ``"premise"`` for an assumption (no ``depends_on``)."""

    node_id: str
    formula: str
    depends_on: tuple[str, ...]
    rule: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "depends_on", tuple(self.depends_on))

        if not isinstance(self.node_id, str) or not self.node_id.isidentifier():
            raise ProofError(
                "ProofNode.node_id must be a Python identifier str; "
                f"got {self.node_id!r}"
            )
        if not isinstance(self.formula, str) or not self.formula.strip():
            raise ProofError("ProofNode.formula must be a non-empty str")
        if not isinstance(self.rule, str) or not self.rule.strip():
            raise ProofError("ProofNode.rule must be a non-empty str")
        if self.rule != self.rule.strip():
            raise ProofError("ProofNode.rule must not have leading/trailing whitespace")
        if self.rule == "premise" and self.depends_on:
            raise ProofError('ProofNode.rule == "premise" requires empty depends_on')
        if self.node_id in self.depends_on:
            # A self-dependency is a length-1 cycle; the binding-graph acyclicity
            # guard (ADR-0203) would also catch it, but refuse early and clearly.
            raise ProofError(f"ProofNode {self.node_id!r} depends on itself")


@dataclass(frozen=True, slots=True)
class Proof:
    """A proof DAG: nodes plus the designated conclusion node.

    Construction validates only proof-shape integrity (unique ids, conclusion
    exists, dependencies name declared nodes). Acyclicity and referential
    integrity at the symbol level are enforced by the binding graph at build
    time (ADR-0203 / ADR-0132) — deliberately, so the guard fires through the
    real builder path rather than a duplicate pre-check."""

    nodes: tuple[ProofNode, ...]
    conclusion_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        if not self.nodes:
            raise ProofError("Proof must have at least one node")
        ids = [n.node_id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ProofError(f"duplicate ProofNode.node_id: {ids}")
        known = set(ids)
        for node in self.nodes:
            for dep in node.depends_on:
                if dep not in known:
                    raise ProofError(
                        f"ProofNode {node.node_id!r} depends on undeclared node {dep!r}"
                    )
        if self.conclusion_id not in known:
            raise ProofError(f"conclusion_id {self.conclusion_id!r} is not a declared node")


def proof_from_premises(
    premises: tuple[str, ...], conclusion: str, *, rule: str
) -> Proof:
    """Desugar the ``premises``/``conclusion``/``rule`` corpus shape onto ``Proof``.

    Each premise becomes a ``rule="premise"`` node with no dependencies; the
    conclusion becomes one node with ``rule=rule`` depending on every premise."""
    nodes: list[ProofNode] = []
    premise_ids: list[str] = []
    for i, formula in enumerate(premises):
        nid = f"premise_{i}"
        premise_ids.append(nid)
        nodes.append(ProofNode(node_id=nid, formula=formula, depends_on=(), rule="premise"))
    nodes.append(
        ProofNode(node_id="conclusion", formula=conclusion,
                  depends_on=tuple(premise_ids), rule=rule)
    )
    return Proof(nodes=tuple(nodes), conclusion_id="conclusion")
