"""ADR-0205 — modus_ponens + the disagreement/uniqueness rule (proof_chain 2.3).

The first inference rule, and the wrong=0 mechanism for proofs. Operates on
proposition FORMULAS via the canonicalizer (`generate.logic_canonical`) — the
proof-layer dispatch (Option B): it never touches the math `check_admissibility` /
`_resolve_dep_units` (proofs have no units; the named 2.2 constraint, satisfied by
construction).

The disagreement rule is the literal twin of
`generate.derivation.verify.select_self_verified`: **pool ALL admissible single-step
MP derivations the premise set supports**, collect their canonical conclusion keys,
and admit iff they collapse to exactly one key equal to the declared conclusion.
Pooling over the premise set — NOT filtering to the declared conclusion first — is
the soundness mechanism: filter-first would admit-by-assertion when the same
premises admit a different key (the ``20/5 == 4`` class one level up).

**Honesty-boundary scope (load-bearing):** this guarantees a unique conclusion among
**single-step modus ponens** derivations over the given premises — NOT "uniquely
entailed" by all proof strategies. Same discipline as propositional-not-FOL.

Closed typed-reason set (the mechanism makes exactly these distinctions; the corpus's
finer labels collapse onto them — ADR-0205 §reason-set):
  * 6 disagreement refuse-labels → ``conclusion_disagreement``;
  * 4 antecedent-flavor labels (missing_antecedent / antecedent_mismatch /
    affirming_consequent / implication_direction_mismatch) → ``unestablished_antecedent``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from generate.logic_canonical import canonicalize, parse_top_implication
from generate.proof_chain.model import Proof, ProofError


class MPOutcome(str, Enum):
    ADMIT = "admit"
    REFUSE = "refuse"


# Closed reason vocabulary.
UNIQUE_CANONICAL_CONCLUSION: Final[str] = "unique_canonical_conclusion"  # admit
MISSING_IMPLICATION: Final[str] = "missing_implication"
UNESTABLISHED_ANTECEDENT: Final[str] = "unestablished_antecedent"
CONCLUSION_MISMATCH: Final[str] = "conclusion_mismatch"
CONCLUSION_DISAGREEMENT: Final[str] = "conclusion_disagreement"

MP_REASONS: Final[frozenset[str]] = frozenset({
    UNIQUE_CANONICAL_CONCLUSION,
    MISSING_IMPLICATION,
    UNESTABLISHED_ANTECEDENT,
    CONCLUSION_MISMATCH,
    CONCLUSION_DISAGREEMENT,
})


@dataclass(frozen=True, slots=True)
class MPVerdict:
    outcome: MPOutcome
    reason: str
    conclusion_key: str | None       # the unique admitted key (admit only)
    derived_keys: tuple[str, ...]    # distinct admissible-derivation keys (sorted)


def evaluate_modus_ponens(premises: tuple[str, ...], conclusion: str) -> MPVerdict:
    """Single-step modus ponens + the disagreement rule over ``premises``.

    Admit iff the admissible single-step MP derivations the premises support
    collapse to exactly one canonical key equal to ``conclusion``'s key. Refuses
    (typed) otherwise. Propagates the canonicalizer's ``LogicError`` family on a
    malformed / out-of-regime premise or conclusion."""
    conclusion_key = canonicalize(conclusion).canonical_key

    # Each premise establishes its own canonical key; implications also expose a
    # syntactic (antecedent, consequent).
    established: set[str] = set()
    implications: list[tuple[str, str]] = []
    for premise in premises:
        established.add(canonicalize(premise).canonical_key)
        parts = parse_top_implication(premise)
        if parts is not None:
            implications.append(parts)

    if not implications:
        return MPVerdict(MPOutcome.REFUSE, MISSING_IMPLICATION, None, ())

    # Enumerate admissible derivations: an implication A->B fires iff key(A) is an
    # established premise; it yields B. Pool over the WHOLE premise set.
    derived: dict[str, None] = {}  # insertion-ordered distinct yielded keys
    for antecedent, consequent in implications:
        if canonicalize(antecedent).canonical_key in established:
            derived[canonicalize(consequent).canonical_key] = None

    if not derived:
        # Implication(s) present, but none has an established antecedent.
        return MPVerdict(MPOutcome.REFUSE, UNESTABLISHED_ANTECEDENT, None, ())

    distinct = tuple(sorted(derived))
    if len(distinct) >= 2:
        # The premises admit deriving distinct conclusions → disagreement.
        return MPVerdict(MPOutcome.REFUSE, CONCLUSION_DISAGREEMENT, None, distinct)

    only = distinct[0]
    if only != conclusion_key:
        # A single admissible derivation, but it concludes something else.
        return MPVerdict(MPOutcome.REFUSE, CONCLUSION_MISMATCH, None, distinct)

    return MPVerdict(MPOutcome.ADMIT, UNIQUE_CANONICAL_CONCLUSION, only, distinct)


def evaluate_proof_conclusion(proof: Proof) -> MPVerdict:
    """Evaluate ``proof``'s conclusion node as a modus_ponens step.

    Wires the rule to the ADR-0204 ``Proof``: gathers the conclusion node's
    dependency-node formulas as the premise set and evaluates. Requires the
    conclusion node's ``rule == "modus_ponens"``."""
    by_id = {n.node_id: n for n in proof.nodes}
    concl = by_id[proof.conclusion_id]
    if concl.rule != "modus_ponens":
        raise ProofError(
            f"evaluate_proof_conclusion expects a modus_ponens conclusion; "
            f"got rule={concl.rule!r}"
        )
    premises = tuple(by_id[dep].formula for dep in concl.depends_on)
    return evaluate_modus_ponens(premises, concl.formula)
