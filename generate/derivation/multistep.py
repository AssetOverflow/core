"""ADR-0176 MS-3 — target-guided bounded multi-step search.

Composes everything: extract body+question quantities (MS-1 ``Target``),
comparative scalars (the pack), enumerate a small, principled set of candidate
**chains** that use *all* the quantities, and route them through the self-
verification gate (grounding ∧ cue ∧ unit ∧ completeness) + ``target_units`` +
uniqueness (MS-2 ``select_self_verified``).

Deliberately **shape-based, not blind enumeration**: it tries the arithmetic
shapes the gold structures actually use (product-of-all, sum-of-all, each
optionally followed by the comparative scalars), each licensed by a *present*
cue. This is bounded by construction (a handful of candidates) and deterministic.

Honest posture (wrong=0-first): when more than one shape self-verifies and they
disagree, the uniqueness rule **refuses** — broad cues cannot tell which op the
text licenses, and that ambiguity is a refusal, not a guess. Coverage is therefore
gated on cue *precision* (the ADR-0175 learning loop), exactly as the practice
eliminations will show. Refuse-preferring throughout; runs only in the sealed
practice lane.
"""

from __future__ import annotations

from typing import Final

from generate.derivation.comparatives import comparative_step, extract_comparative_scalars
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.search import MULTIPLICATIVE_CUES
from generate.derivation.target import Target, extract_target
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

MAX_QUANTITIES: Final[int] = 6


def _chain(quantities: list[Quantity], op: str, cue: str, tail: tuple[Step, ...]) -> GroundedDerivation:
    """Left-fold all quantities under ``op`` (cue ``cue``), then append ``tail``."""
    start, *rest = quantities
    steps = tuple(Step(op=op, operand=q, cue=cue) for q in rest) + tail
    return GroundedDerivation(start=start, steps=steps)


def _candidate_chains(
    quantities: list[Quantity], problem_text: str, target: Target
) -> list[GroundedDerivation]:
    """The small, principled candidate set. Bounded + deterministic."""
    tokens = _tokens(problem_text)
    comparative_tail = tuple(
        comparative_step(cs) for cs in extract_comparative_scalars(problem_text)
    )

    # product-of-all is licensed by a present multiplicative cue;
    # sum-of-all by a present aggregation hint (a strong, single-word sum signal).
    mult_cue = next((c for c in MULTIPLICATIVE_CUES if c in tokens), None)
    add_cue = target.aggregation if (target.aggregation in tokens) else None

    candidates: list[GroundedDerivation] = []
    for op, cue in (("multiply", mult_cue), ("add", add_cue)):
        if cue is None:
            continue
        candidates.append(_chain(quantities, op, cue, ()))
        if comparative_tail:
            candidates.append(_chain(quantities, op, cue, comparative_tail))
    return candidates


def candidate_chains(
    problem_text: str, target: Target | None = None
) -> list[GroundedDerivation]:
    """The bounded, deterministic candidate readings :func:`search_chain` weighs.

    The *enumeration* half of the search, with no gate applied: extract quantities,
    refuse-on-overflow (``> MAX_QUANTITIES``) / too-few (``< 2``) by yielding no
    candidates, derive the target, and build the principled set. Exposed for CP-2
    ledger training (ADR-0177), which must see every reading the search considers —
    not just the one it resolves to. ``search_chain`` delegates here, so the two
    can never drift.
    """
    quantities = list(extract_quantities(problem_text))
    if not 2 <= len(quantities) <= MAX_QUANTITIES:
        return []  # refuse-on-overflow / too few to compose
    resolved: Target = target if target is not None else extract_target(
        problem_text, known_units=tuple(q.unit for q in quantities)
    )
    return _candidate_chains(quantities, problem_text, resolved)


def search_chain(problem_text: str, target: Target | None = None) -> Resolution | None:
    """Target-guided bounded multi-step search over the problem's quantities.

    Returns a :class:`Resolution` only when a single candidate chain self-verifies
    (and, when a target unit is known, matches it); refuses on no candidate,
    disagreement, or > :data:`MAX_QUANTITIES` quantities. Deterministic.
    """
    # Target-UNIT matching is deferred: the model's answer_unit is the start
    # quantity's unit, which is wrong for cross-unit products (6 boxes x 50 apples
    # -> value 300 but unit "boxes"), so a unit gate would over-refuse correct
    # answers. The Target still prunes via its aggregation cue + supplies the
    # question quantities. Unit matching returns once a result-unit model exists.
    return select_self_verified(
        candidate_chains(problem_text, target), problem_text, target_units=()
    )
