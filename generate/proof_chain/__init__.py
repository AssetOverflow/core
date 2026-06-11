"""ADR-0204/0205 — proof_chain: propositional proof graphs over the binding-graph DAG.

- Phase 2.2 (ADR-0204): the proof-graph *builder* — proof → binding graph, structure
  only (`build_proof_graph`).
- Phase 2.3 (ADR-0205): the first inference rule + the wrong=0 mechanism —
  `evaluate_modus_ponens` / `evaluate_proof_conclusion` (modus_ponens + the
  disagreement/uniqueness rule), in `rules.py`.
- Phase 2.4: the full sound+complete propositional entailment operator over the
  ADR-0201 ROBDD (`evaluate_entailment_with_trace`), in `entail.py` — committed
  home is ADR-0218 (its original "ADR-0206" label was a numbering collision).
- ADR-0218 PR B: `PromotionCertificate` + pure replay verifier
  (`build_certificate` / `verify_certificate`), in `certificate.py`.  Evidence
  substrate only — no promotion, no vault import, no status transition.

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
from .certificate import (
    CERTIFICATE_VERSION,
    ENGINE_PIN_MISMATCH,
    MALFORMED_CERTIFICATE,
    PREMISE_STATUS_VOCAB,
    REPLAY_MATCH,
    REPLAY_MISMATCH,
    VERIFICATION_REASONS,
    CertificateVerification,
    PremiseRecord,
    PromotionCertificate,
    build_certificate,
    verify_certificate,
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
    "CERTIFICATE_VERSION",
    "CONCLUSION_DISAGREEMENT",
    "CONCLUSION_MISMATCH",
    "CertificateVerification",
    "ENGINE_PIN_MISMATCH",
    "MALFORMED_CERTIFICATE",
    "MISSING_IMPLICATION",
    "MP_REASONS",
    "MPOutcome",
    "MPVerdict",
    "PREMISE_STATUS_VOCAB",
    "PROOF_INTRODUCED_BY",
    "PROOF_NO_UNIT",
    "PROOF_SOURCE_ID",
    "PremiseRecord",
    "Proof",
    "ProofError",
    "ProofGraph",
    "ProofNode",
    "PromotionCertificate",
    "REPLAY_MATCH",
    "REPLAY_MISMATCH",
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
    "VERIFICATION_REASONS",
    "build_certificate",
    "build_proof_graph",
    "evaluate_entailment",
    "evaluate_entailment_with_trace",
    "evaluate_modus_ponens",
    "evaluate_proof_conclusion",
    "proof_from_premises",
    "verify_certificate",
)
