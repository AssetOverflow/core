"""P1-B — the gold-setup-backed OFF-SERVING R2 verification producer.

The first consumer of the P1-A VERIFIED contract (``core.epistemic_disclosure.verified_contract``).
Given an R2 problem (prose ``text``) and the INDEPENDENTLY hand-authored gold SETUP
(``ConstraintProblem``), it constructs a :class:`VerificationProof` and runs it through
the contract. It answers exactly one question:

    Can CORE construct a VerificationProof that survives the P1-A contract, off-serving?

**WHAT THIS IS — and is NOT.**

  * It IS a validation of the VERIFIED contract + producer mechanics off-serving, using
    reader-vs-gold-setup convergence as the two independent reads.
  * It is NOT a serving-time VERIFIED producer. It depends on the eval-lane gold setup,
    which does not exist at serving time. It CANNOT move any serving metric and CANNOT
    emit a served ``[verified]``.
  * Serving-time independence (a non-gold, structurally-distinct second reader) is a
    SEPARATE, larger rung — explicitly deferred, not solved here.

**The two independent reads** (the contract's independence + convergence, honestly):

  * primary read   = ``read_constraint_problem(text)`` (lineage ``constraint_reader_v1``)
  * independent read = the gold-authored setup            (lineage ``constraint_gold_author_v1``)
  * convergence    = the two ``constraint_setup_signature`` digests are equal.

The gold *answer* never enters the proof — only the gold *structure* (a reading), through
the SAME canonical signature used for the primary read. A wrong reader structure diverges
from the gold-authored structure → ``reads_disagree`` → NOT_VERIFIED (the poison case).

Off-serving: imports no ``generate.derivation`` / ``core.reliability_gate``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from core.comprehension_attempt.model import ComprehensionAttempt
from core.epistemic_disclosure.disclosure_claim import DisclosureClaim
from core.epistemic_disclosure.limitation import (
    LimitationAssessment,
    assess_from_attempt,
)
from core.epistemic_disclosure.verified_contract import (
    VerificationProof,
    VerificationResult,
    VerificationVerdict,
    disclosure_for_verification,
    evaluate_verification,
)
from core.epistemic_state import EpistemicState
from evals.constraint_oracle.signature import (
    constraint_setup_signature,
    constraints_signature,
)
from generate.constraint_comprehension.model import ConstraintProblem
from generate.constraint_comprehension.reader import read_constraint_problem
from generate.constraint_comprehension.solver import solve_constraint_problem
from generate.meaning_graph.reader import Refusal

#: The two reader lineages — DISTINCT so the contract's independence check passes. Named
#: explicitly so nobody later mistakes ``constraint_gold_author_v1`` for a serving reader.
CONSTRAINT_READER_LINEAGE = "constraint_reader_v1"
CONSTRAINT_GOLD_AUTHOR_LINEAGE = "constraint_gold_author_v1"

#: The producer's own refusal reason (the reader refused → no primary read exists).
REASON_READER_REFUSED = "reader_refused"


def _sha(payload: str) -> str:
    """Deterministic hex digest of a canonical string payload."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _back_substitutes(problem: ConstraintProblem, solution: dict[str, int]) -> bool:
    """True iff ``solution`` satisfies EVERY constraint exactly (integer; never rounds).

    Back-substitution into the STATED constraints — proves the solver was faithful to the
    structure it was handed. It CANNOT catch a wrong read (that is the independent read's
    job); it catches a wrong solve.
    """
    for constraint in problem.constraints:
        lhs = constraint.lhs.constant + sum(
            coeff * solution.get(symbol, 0) for symbol, coeff in constraint.lhs.terms
        )
        if lhs != constraint.rhs:
            return False
    return True


@dataclass(frozen=True, slots=True)
class R2VerificationOutcome:
    """The producer's structured outcome: the contract verdict, the proof (``None`` only
    when the reader refused and no primary read exists), the limitation (on refusal), and
    the routed state/claim — reached ONLY via :func:`disclosure_for_verification`."""

    result: VerificationResult
    proof: VerificationProof | None
    limitation: LimitationAssessment | None
    epistemic_state: EpistemicState
    disclosure_claim: DisclosureClaim


def verify_r2(text: str, gold_setup: ConstraintProblem) -> R2VerificationOutcome:
    """Build and evaluate a VerificationProof for one R2 problem, off-serving.

    ``gold_setup`` is the INDEPENDENT read — the hand-authored canonical setup (setup
    fields only; the gold ANSWER is never an input here). The reader provides the primary
    read. The result is routed to a state/claim ONLY through the sanctioned contract gate.
    """
    primary = read_constraint_problem(text)

    # Reader refused → there is no primary read; classify the refusal as a limitation and
    # do NOT verify. No proof object exists to evaluate.
    if isinstance(primary, Refusal):
        limitation = assess_from_attempt(
            ComprehensionAttempt(
                organ="r2_constraints",
                outcome="setup_refused",
                refusal_reason=primary.reason,
            )
        )
        result = VerificationResult(
            verdict=VerificationVerdict.NOT_VERIFIED,
            failed_checks=(REASON_READER_REFUSED,),
        )
        state, claim = disclosure_for_verification(result)
        return R2VerificationOutcome(
            result=result,
            proof=None,
            limitation=limitation,
            epistemic_state=state,
            disclosure_claim=claim,
        )

    # The reader produced a setup. Solve it (the derivation from the STATED quantities) and
    # back-substitute. The gold answer is NEVER consulted — only the reader's own solve.
    solution = solve_constraint_problem(primary)
    if isinstance(solution, Refusal):
        boundary_clear = False
        derivation_digest = ""
        back_substitution_digest = ""
    else:
        boundary_clear = True
        bound = tuple(sorted(solution.items()))
        derivation_digest = _sha(
            repr(("derivation", constraints_signature(primary.constraints), bound))
        )
        back_substitution_digest = (
            _sha(repr(("back_substitution", bound)))
            if _back_substitutes(primary, solution)
            else ""
        )

    proof = VerificationProof(
        source_problem_digest=_sha(text),
        primary_reader_lineage=CONSTRAINT_READER_LINEAGE,
        independent_reader_lineage=CONSTRAINT_GOLD_AUTHOR_LINEAGE,
        primary_read_digest=_sha(repr(constraint_setup_signature(primary))),
        independent_read_digest=_sha(repr(constraint_setup_signature(gold_setup))),
        derivation_digest=derivation_digest,
        back_substitution_digest=back_substitution_digest,
        boundary_clear=boundary_clear,
        # Setup-only verification has no answer-key path, so no contradiction can arise
        # here; the contract still enforces it (P1-A test_contradiction_blocks_verification).
        contradiction_clear=True,
    )
    result = evaluate_verification(proof, limitation=None)
    state, claim = disclosure_for_verification(result)
    return R2VerificationOutcome(
        result=result,
        proof=proof,
        limitation=None,
        epistemic_state=state,
        disclosure_claim=claim,
    )


__all__ = [
    "CONSTRAINT_GOLD_AUTHOR_LINEAGE",
    "CONSTRAINT_READER_LINEAGE",
    "REASON_READER_REFUSED",
    "R2VerificationOutcome",
    "verify_r2",
]
