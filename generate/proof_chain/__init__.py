"""ADR-0204/0205 — proof_chain: propositional proof graphs over the binding-graph DAG.

- Phase 2.2 (ADR-0204): the proof-graph *builder* — proof → binding graph, structure
  only (`build_proof_graph`).
- Phase 2.3 (ADR-0205): the first inference rule + the wrong=0 mechanism —
  `evaluate_modus_ponens` / `evaluate_proof_conclusion` (modus_ponens + the
  disagreement/uniqueness rule), in `rules.py`.

Honesty boundary (load-bearing through 2.3): sound over declared atoms, not grounded
in recognized input; the disagreement rule guarantees a unique conclusion among
SINGLE-STEP modus ponens over the premises, not "uniquely entailed" by all strategies.
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
from .rules import (
    CONCLUSION_DISAGREEMENT,
    CONCLUSION_MISMATCH,
    MISSING_IMPLICATION,
    MP_REASONS,
    UNESTABLISHED_ANTECEDENT,
    UNIQUE_CANONICAL_CONCLUSION,
    MPOutcome,
    MPVerdict,
    evaluate_modus_ponens,
    evaluate_proof_conclusion,
)
from .entail import (
    ENTAILMENT_REASONS,
    INCONSISTENT_PREMISES,
    OUT_OF_REGIME_OR_MALFORMED,
    TAUTOLOGICAL_IMPLICATION,
    TAUTOLOGICAL_REFUTATION,
    UNDETERMINED,
    Entailment,
    EntailmentTrace,
    EntailmentVerdict,
    evaluate_entailment,
    evaluate_entailment_with_trace,
)

__all__ = (
    "CONCLUSION_DISAGREEMENT",
    "CONCLUSION_MISMATCH",
    "MISSING_IMPLICATION",
    "MP_REASONS",
    "MPOutcome",
    "MPVerdict",
    "PROOF_INTRODUCED_BY",
    "PROOF_NO_UNIT",
    "PROOF_SOURCE_ID",
    "Proof",
    "ProofError",
    "ProofGraph",
    "ProofNode",
    "ENTAILMENT_REASONS",
    "Entailment",
    "EntailmentTrace",
    "EntailmentVerdict",
    "INCONSISTENT_PREMISES",
    "OUT_OF_REGIME_OR_MALFORMED",
    "TAUTOLOGICAL_IMPLICATION",
    "TAUTOLOGICAL_REFUTATION",
    "UNESTABLISHED_ANTECEDENT",
    "UNDETERMINED",
    "UNIQUE_CANONICAL_CONCLUSION",
    "build_proof_graph",
    "evaluate_entailment",
    "evaluate_entailment_with_trace",
    "evaluate_modus_ponens",
    "evaluate_proof_conclusion",
    "proof_from_premises",
)
