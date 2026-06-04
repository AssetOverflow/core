"""ADR-0206 — Propositional entailment operator (proof_chain phase 2.4).

The multi-hop inference operator ``gaps.md`` asked for and ADR-0205 deferred. Where
:func:`generate.proof_chain.rules.evaluate_modus_ponens` is **single-step** ("unique
conclusion among single-step modus ponens"), this is the full, sound **and complete**
propositional entailment decision built directly on the ADR-0201 ROBDD keystone:

    premises ⊨ query   iff   (⋀ premises) → query   is a tautology.

Because the ROBDD is a *canonical, complete* decision procedure for propositional
logic, this answers arbitrary multi-hop deductive queries (chains of implications,
conjunctive rules, contrapositive, disjunctive syllogism — anything propositional),
not just one modus-ponens step. ``wrong == 0`` is structural: a tautology check is
exact, never approximate, and the canonicalizer **refuses** (``LogicError``) rather
than guess on malformed / out-of-decidable-regime (quantified/predicate) input.

Four outcomes, all sound:

* ``ENTAILED``  — ``(⋀P) → Q`` is a tautology (Q holds in every model of P).
* ``REFUTED``   — ``(⋀P) → ¬Q`` is a tautology (Q fails in every model of P).
* ``UNKNOWN``   — neither; Q is true in some models of P and false in others.
* ``REFUSED``   — premises are inconsistent (no model — everything would follow
  vacuously, so we decline an answer) **or** input is malformed / out-of-regime.

Honesty boundary (load-bearing): **propositional only**. Atoms are opaque Boolean
variables; predicate/quantified structure is out of regime and refuses (ADR-0201.1).
A grounded finite-entity problem (each predicate-entity pair → one atom) IS
propositional and in scope; an ungrounded ``forall x. P(x)`` is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from generate.logic_canonical import LogicError, canonicalize


class Entailment(str, Enum):
    ENTAILED = "entailed"
    REFUTED = "refuted"
    UNKNOWN = "unknown"
    REFUSED = "refused"


# Closed reason vocabulary (the mechanism makes exactly these distinctions).
TAUTOLOGICAL_IMPLICATION: Final[str] = "tautological_implication"   # entailed
TAUTOLOGICAL_REFUTATION: Final[str] = "tautological_refutation"     # refuted
UNDETERMINED: Final[str] = "undetermined"                           # unknown
INCONSISTENT_PREMISES: Final[str] = "inconsistent_premises"         # refused
OUT_OF_REGIME_OR_MALFORMED: Final[str] = "out_of_regime_or_malformed"  # refused

ENTAILMENT_REASONS: Final[frozenset[str]] = frozenset({
    TAUTOLOGICAL_IMPLICATION,
    TAUTOLOGICAL_REFUTATION,
    UNDETERMINED,
    INCONSISTENT_PREMISES,
    OUT_OF_REGIME_OR_MALFORMED,
})


@dataclass(frozen=True, slots=True)
class EntailmentVerdict:
    outcome: Entailment
    reason: str


def _conjoin(premises: tuple[str, ...]) -> str:
    """Fully-parenthesized conjunction of the premise formulas (``true`` if empty).

    Each premise is wrapped so its internal precedence cannot bleed across the
    ``&`` joins; an empty premise set is the always-true antecedent."""
    if not premises:
        return "true"
    return " & ".join(f"({p})" for p in premises)


def evaluate_entailment(premises: tuple[str, ...], query: str) -> EntailmentVerdict:
    """Decide whether ``premises`` propositionally entail / refute ``query``.

    Sound and complete over the propositional regime; refusal-first on anything
    outside it. Never raises on a logic-domain error — every ``LogicError`` (and
    its regime/budget subclasses) maps to a typed ``REFUSED`` verdict."""
    try:
        conj = _conjoin(premises)
        conj_canon = canonicalize(conj)
        if conj_canon.is_contradiction:
            # No model satisfies the premises: from a contradiction everything
            # follows. We decline rather than assert a vacuous entailment.
            return EntailmentVerdict(Entailment.REFUSED, INCONSISTENT_PREMISES)
        # Force the query through the canonicalizer too, so a malformed / out-of-
        # regime query refuses even when the implication check would shortcut.
        canonicalize(query)
        entailed = canonicalize(f"({conj}) -> ({query})").is_tautology
        refuted = canonicalize(f"({conj}) -> (~({query}))").is_tautology
    except LogicError:
        return EntailmentVerdict(Entailment.REFUSED, OUT_OF_REGIME_OR_MALFORMED)

    if entailed and refuted:
        # Only possible if the premises are inconsistent, already handled above;
        # defensive — never assert a contradiction-derived answer.
        return EntailmentVerdict(Entailment.REFUSED, INCONSISTENT_PREMISES)
    if entailed:
        return EntailmentVerdict(Entailment.ENTAILED, TAUTOLOGICAL_IMPLICATION)
    if refuted:
        return EntailmentVerdict(Entailment.REFUTED, TAUTOLOGICAL_REFUTATION)
    return EntailmentVerdict(Entailment.UNKNOWN, UNDETERMINED)
