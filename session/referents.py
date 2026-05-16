"""
session/referents.py — ReferentRegistry

Tracks active discourse referents across turns so that incoming pronoun
tokens (it, this, that, they, he, she) can be resolved to the versor of
the last-mentioned noun-class entity before field propagation.

Design rules
------------
* One active referent slot per pronoun class (singular-neutral, plural,
  animate-masc, animate-fem).  Registration overwrites the previous slot.
* Resolution is non-destructive: looking up a pronoun does not clear the
  slot.  The slot is cleared only when a new noun registers into it.
* Zero dependencies on numpy internals — callers supply versors as
  np.ndarray; the registry stores copies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Pronoun → slot mapping
# ---------------------------------------------------------------------------

#: Tokens recognised as anaphoric pronouns, keyed to their resolution slot.
_PRONOUN_SLOTS: dict[str, str] = {
    "it":    "neut_sg",
    "this":  "neut_sg",
    "that":  "neut_sg",
    "its":   "neut_sg",
    "they":  "plural",
    "them":  "plural",
    "their": "plural",
    "these": "plural",
    "those": "plural",
    "he":    "masc_sg",
    "him":   "masc_sg",
    "his":   "masc_sg",
    "she":   "fem_sg",
    "her":   "fem_sg",
    "hers":  "fem_sg",
}

_SLOT_NAMES: frozenset[str] = frozenset(_PRONOUN_SLOTS.values())


# ---------------------------------------------------------------------------
# ReferentEntry — one registered referent
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ReferentEntry:
    surface: str          # canonical surface form that was registered
    versor: np.ndarray    # CGA versor at time of registration
    turn: int             # turn index when registered
    slot: str             # which pronoun slot this fills


# ---------------------------------------------------------------------------
# ReferentRegistry
# ---------------------------------------------------------------------------

class ReferentRegistry:
    """
    Per-session registry of active discourse referents.

    Usage
    -----
    # On each ingest call, *before* inject():
    resolved_tokens = registry.resolve(tokens)

    # After generating a response, register the main noun:
    registry.register(surface="light", versor=state.F, slot="neut_sg", turn=ctx.turn)
    """

    def __init__(self) -> None:
        # slot_name → most recent ReferentEntry
        self._slots: dict[str, ReferentEntry] = {}
        # full history for debugging / correction pass
        self._history: list[ReferentEntry] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        surface: str,
        versor: np.ndarray,
        turn: int,
        slot: str = "neut_sg",
    ) -> None:
        """Register a noun as the active referent for *slot*."""
        if slot not in _SLOT_NAMES:
            raise ValueError(f"Unknown referent slot: {slot!r}.  Valid: {_SLOT_NAMES}")
        entry = ReferentEntry(
            surface=surface,
            versor=np.asarray(versor, dtype=np.float32).copy(),
            turn=turn,
            slot=slot,
        )
        self._slots[slot] = entry
        self._history.append(entry)

    def register_from_tokens(
        self,
        tokens: Sequence[str],
        versors: dict[str, np.ndarray],
        turn: int,
        slot: str = "neut_sg",
    ) -> None:
        """
        Convenience: register the last content token whose surface appears
        in *versors* (a surface→versor dict from the vocab).
        """
        for tok in reversed(tokens):
            if tok in versors:
                self.register(tok, versors[tok], turn=turn, slot=slot)
                return

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        tokens: Sequence[str],
    ) -> list[str]:
        """
        Return a new token list where anaphoric pronouns are replaced by
        the surface form of the active referent in the matching slot.

        If no referent is registered for a pronoun's slot the pronoun is
        kept as-is (safe fallback — no fabrication).
        """
        out: list[str] = []
        for tok in tokens:
            slot = _PRONOUN_SLOTS.get(tok.casefold())
            if slot is not None:
                entry = self._slots.get(slot)
                out.append(entry.surface if entry is not None else tok)
            else:
                out.append(tok)
        return out

    def resolve_versor(
        self,
        token: str,
    ) -> np.ndarray | None:
        """
        Return the registered versor for a pronoun token, or None if the
        token is not a pronoun or has no active referent.
        """
        slot = _PRONOUN_SLOTS.get(token.casefold())
        if slot is None:
            return None
        entry = self._slots.get(slot)
        return entry.versor.copy() if entry is not None else None

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def active_referent(self, slot: str = "neut_sg") -> ReferentEntry | None:
        return self._slots.get(slot)

    def history(self) -> list[ReferentEntry]:
        return list(self._history)

    def clear(self) -> None:
        """Reset all slots (e.g. between sessions)."""
        self._slots.clear()
        self._history.clear()

    def __repr__(self) -> str:
        active = {k: v.surface for k, v in self._slots.items()}
        return f"ReferentRegistry(active={active})"
