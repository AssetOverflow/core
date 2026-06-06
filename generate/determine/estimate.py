"""E — ESTIMATION (roadmap Step 5): the calibrated converse-guess.

DETERMINE refuses a symmetric-converse query as *sound-but-incomplete*: told
``p(a, b)``, asked ``p(b, a)``, it answers only the stored direction (see
``generate.meaning_graph.relational``). E adds a single **defeasible** estimator on
top of that refusal — the converse-guess: "``p(a, b)`` is told, so guess ``p(b, a)``
holds too." It is **blind** (it never reads the pack's symmetry metadata), so it is
*correct* on a symmetric predicate and *wrong* on a directed one. Whether the engine
is allowed to SERVE the guess is decided NOT here but by the reliability gate
(ADR-0175 ``license_for(SERVE)``) over a committed per-predicate ``ClassTally`` — the
engine serves the guess only for predicate-classes it has measured itself reliable on,
and even then the surface is DISCLOSED ``[approximate]`` (ADR-0206 ``shape_surface``),
never asserted as fact.

wrong=0: this module only *proposes a candidate*; it commits nothing and asserts
nothing. The gate decides licensing; disclosure marks every served estimate. A wrong
estimate is therefore always a DISCLOSED wrong, never a silent one.
"""

from __future__ import annotations

from dataclasses import dataclass

from generate.realize import recall_realized
from session.context import SessionContext


@dataclass(frozen=True, slots=True)
class ConverseEstimate:
    """A defeasible converse-guess candidate for a ``p(subject, object)`` query.

    ``answer`` is always ``True`` — the estimator's only move is "the converse
    relation holds". ``basis="estimate_converse"`` keeps it distinct from a
    determination's ``as_told``/``verified``: this was guessed, not grounded.
    ``told_structure_key`` ties the guess to the realized fact it generalized,
    so the served estimate is replayable to its evidence.
    """

    predicate: str
    subject: str
    object: str
    answer: bool
    basis: str
    told_structure_key: str


#: The capability-axis id a converse-guess is tallied under — the predicate itself.
#: Each predicate earns (or fails to earn) its own SERVE license independently.
def converse_class_name(predicate: str) -> str:
    return f"converse:{predicate}"


def estimate_converse(
    ctx: SessionContext, predicate: str, subject: str, target: str
) -> ConverseEstimate | None:
    """Return a converse-guess for ``p(subject, target)`` iff the converse was told.

    The estimator fires only when a realized ``p(target, subject)`` exists (the
    stored direction DETERMINE already declined to generalize). It returns the
    candidate WITHOUT committing it — the caller (the reliability-gated serving
    wire) decides whether the predicate-class is licensed to serve it, disclosed.
    Returns ``None`` when there is no told converse to generalize from.
    """
    told = recall_realized(ctx, subject=target, predicate=predicate)
    grounding = next((f for f in told if f.relation_arguments == (target, subject)), None)
    if grounding is None:
        return None
    return ConverseEstimate(
        predicate=predicate,
        subject=subject,
        object=target,
        answer=True,
        basis="estimate_converse",
        told_structure_key=grounding.structure_key,
    )


__all__ = ["ConverseEstimate", "converse_class_name", "estimate_converse"]
