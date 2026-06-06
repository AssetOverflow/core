"""Deterministic surface rendering for a Determined answer (Step B-2) and a converse
estimate (Step E).

Turns a ``Determined`` into the user-facing string the runtime surfaces. The basis is
rendered HONESTLY: SPECULATIVE grounds (today's only case) render as "as I was told",
never "verified" — only COHERENT-admissible grounds (not yet reachable) would. D0 only
ever asserts ``answer=True``, so the surface is an affirmation; there is no fabricated
or asserted-False surface to render.

``render_estimate`` renders the base claim of a converse-guess; the ADR-0206
``shape_surface`` then DISCLOSES it with an ``[approximate]`` prefix — so the estimate is
never confused with a grounded determination.
"""

from __future__ import annotations

from generate.determine.determine import Determined
from generate.determine.estimate import ConverseEstimate

#: Predicate → surface phrase. ``member`` reads as "is a"; the relational pack
#: predicates fall back to their lemma with underscores spaced ("less_than" → "less
#: than"). Closed and deterministic; an unknown predicate still renders legibly.
_PREDICATE_PHRASE: dict[str, str] = {
    "member": "is a",
}


def render_determination(d: Determined) -> str:
    """The user-facing surface for a Determined answer — deterministic, honest basis."""
    phrase = _PREDICATE_PHRASE.get(d.predicate, d.predicate.replace("_", " "))
    qualifier = "as I was told" if d.basis == "as_told" else "verified"
    return f"Yes — {qualifier}, {d.subject} {phrase} {d.object}."


def render_estimate(e: ConverseEstimate) -> str:
    """The base claim of a converse-guess (pre-disclosure).

    ``shape_surface`` prefixes ``[approximate]`` — so this stays a plain claim; the
    honesty marker is added by the bridge, not baked in here. Deterministic.
    """
    phrase = _PREDICATE_PHRASE.get(e.predicate, e.predicate.replace("_", " "))
    return f"{e.subject} {phrase} {e.object}"
