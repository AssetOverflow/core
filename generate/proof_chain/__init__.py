"""ADR-0204 — proof_chain: propositional proof graphs over the binding-graph DAG.

Phase 2.2 (this module set): the proof-graph *builder* — proof → binding graph,
structure only. The canonicalizer (`generate.logic_canonical`) and equivalence
check (`generate.logic_equivalence`) it rides on are top-level modules; the
inference rule (`modus_ponens` + the disagreement rule) is phase 2.3 / ADR-0205.

Honesty boundary (load-bearing through 2.3): sound over declared atoms, not
grounded in recognized input.
"""

from __future__ import annotations

from .builder import (
    PROOF_INTRODUCED_BY,
    PROOF_NO_UNIT,
    PROOF_SOURCE_ID,
    ProofGraph,
    build_proof_graph,
)
from .model import Proof, ProofError, ProofNode, proof_from_premises

__all__ = (
    "PROOF_INTRODUCED_BY",
    "PROOF_NO_UNIT",
    "PROOF_SOURCE_ID",
    "Proof",
    "ProofError",
    "ProofGraph",
    "ProofNode",
    "build_proof_graph",
    "proof_from_premises",
)
