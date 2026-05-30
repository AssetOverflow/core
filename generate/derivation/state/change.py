"""ADR-0184 S1 — conservative change-cue helpers.

These helpers are behavior-equivalent extractions from
:mod:`generate.derivation.accumulate`.  They classify only the closed gain/loss
cue set already used by GB-3b.1 and return ``None`` when polarity is absent or
ambiguous.  Cue hits propose semantic change frames; they never commit answers.
"""

from __future__ import annotations

from typing import Final

from generate.math_roundtrip import _tokens

# Closed change-cue lexeme sets (ADR-0165: lexemes, not grammar templates; refined
# by the CP ledger, not asserted complete).  Sorted use keeps cue selection stable.
GAIN_VERBS: Final[frozenset[str]] = frozenset(
    {
        "buys",
        "bought",
        "gets",
        "got",
        "finds",
        "found",
        "picks",
        "picked",
        "earns",
        "earned",
        "receives",
        "received",
        "collects",
        "collected",
        "wins",
        "won",
        "makes",
        "made",
        "gains",
        "gained",
        "adds",
        "added",
    }
)
LOSS_VERBS: Final[frozenset[str]] = frozenset(
    {
        "loses",
        "lost",
        "spends",
        "spent",
        "uses",
        "used",
        "eats",
        "ate",
        "sells",
        "sold",
        "donates",
        "donated",
        "drops",
        "dropped",
        "removes",
        "removed",
        "breaks",
        "broke",
    }
)


def classify_change_polarity(clause: str) -> int | None:
    """Return ``+1`` for gain, ``-1`` for loss, or ``None`` to refuse.

    Ordering is behavior-equivalent with the prior accumulation helper:

    * ``more`` present -> gain;
    * else an unambiguous loss verb -> loss;
    * else ``gives``/``gave`` with ``to``/``away`` -> loss;
    * else an unambiguous gain verb -> gain;
    * else refuse by returning ``None``.
    """

    tokens = set(_tokens(clause))
    if "more" in tokens:
        return +1
    loss = bool(LOSS_VERBS & tokens)
    gain = bool(GAIN_VERBS & tokens)
    gives = "gives" in tokens or "gave" in tokens
    directional = "to" in tokens or "away" in tokens
    if loss and not gain:
        return -1
    if gives and directional and not gain and not loss:
        return -1
    if gain and not loss:
        return +1
    return None


def select_change_cue(clause: str, polarity: int) -> str:
    """Return a grounded cue lexeme present in ``clause`` for ``polarity``.

    The returned cue is consumed by the existing derivation verifier's cue-grounding
    clause.  This function assumes ``polarity`` was produced by
    :func:`classify_change_polarity` for the same clause.
    """

    tokens = set(_tokens(clause))
    if "more" in tokens and polarity > 0:
        return "more"
    verbs = GAIN_VERBS if polarity > 0 else LOSS_VERBS
    present = sorted(verbs & tokens)
    if present:
        return present[0]
    return "gives"  # the only remaining licensed loss path (gives … to/away)
