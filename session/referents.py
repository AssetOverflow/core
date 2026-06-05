"""
session/referents.py — ReferentRegistry

Tracks active discourse referents across turns so incoming pronoun tokens can
be resolved before field propagation.  Resolution also records which referent
turns were consumed by the most recent ingest, giving SessionGraph truthful
backward edges instead of broad historical guesses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from core.array_codec import decode_array, encode_array

_PRONOUN_SLOTS: dict[str, str] = {
    "it": "neut_sg",
    "this": "neut_sg",
    "that": "neut_sg",
    "its": "neut_sg",
    "they": "plural",
    "them": "plural",
    "their": "plural",
    "these": "plural",
    "those": "plural",
    "he": "masc_sg",
    "him": "masc_sg",
    "his": "masc_sg",
    "she": "fem_sg",
    "her": "fem_sg",
    "hers": "fem_sg",
}

_SLOT_NAMES: frozenset[str] = frozenset(_PRONOUN_SLOTS.values())


@dataclass(slots=True)
class ReferentEntry:
    surface: str
    versor: np.ndarray
    turn: int
    slot: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "versor": encode_array(self.versor),
            "turn": int(self.turn),
            "slot": self.slot,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReferentEntry":
        return cls(
            surface=payload["surface"],
            versor=decode_array(payload["versor"]),
            turn=int(payload["turn"]),
            slot=payload["slot"],
        )


class ReferentRegistry:
    """Per-session registry of active discourse referents."""

    def __init__(self) -> None:
        self._slots: dict[str, ReferentEntry] = {}
        self._history: list[ReferentEntry] = []
        self._last_resolved_sources: list[int] = []
        self._last_resolved_slots: dict[str, int] = {}

    def register(
        self,
        surface: str,
        versor: np.ndarray,
        turn: int,
        slot: str = "neut_sg",
    ) -> None:
        """Register a noun as the active referent for *slot*."""
        if slot not in _SLOT_NAMES:
            raise ValueError(f"Unknown referent slot: {slot!r}. Valid: {_SLOT_NAMES}")
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
        """Register the last token that has a supplied versor."""
        for tok in reversed(tokens):
            if tok in versors:
                self.register(tok, versors[tok], turn=turn, slot=slot)
                return

    def update_turn_versor(self, turn: int, versor: np.ndarray) -> None:
        """Synchronize active/history entries for a corrected source turn."""
        arr = np.asarray(versor, dtype=np.float32).copy()
        for entry in self._history:
            if entry.turn == turn:
                entry.versor = arr.copy()
                if self._slots.get(entry.slot) is entry:
                    self._slots[entry.slot] = entry

    def resolve(self, tokens: Sequence[str]) -> list[str]:
        """
        Replace anaphoric pronouns with the surface form of the active
        referent in the matching slot.  Unresolved pronouns are kept as-is.
        """
        out: list[str] = []
        sources: list[int] = []
        slots: dict[str, int] = {}
        for tok in tokens:
            slot = _PRONOUN_SLOTS.get(tok.casefold())
            if slot is None:
                out.append(tok)
                continue
            entry = self._slots.get(slot)
            if entry is None:
                out.append(tok)
                continue
            out.append(entry.surface)
            sources.append(entry.turn)
            slots[slot] = entry.turn
        self._last_resolved_sources = list(dict.fromkeys(sources))
        self._last_resolved_slots = dict(slots)
        return out

    def resolve_versor(self, token: str) -> np.ndarray | None:
        slot = _PRONOUN_SLOTS.get(token.casefold())
        if slot is None:
            return None
        entry = self._slots.get(slot)
        return entry.versor.copy() if entry is not None else None

    def consumed_turns(self) -> list[int]:
        """Turn indices consumed by the most recent resolve() call."""
        return list(self._last_resolved_sources)

    def consumed_slots(self) -> dict[str, int]:
        """slot → source turn consumed by the most recent resolve() call."""
        return dict(self._last_resolved_slots)

    def active_referent(self, slot: str = "neut_sg") -> ReferentEntry | None:
        return self._slots.get(slot)

    def active_slots(self) -> dict[str, int]:
        return {slot: entry.turn for slot, entry in self._slots.items()}

    def history(self) -> list[ReferentEntry]:
        return list(self._history)

    def clear(self) -> None:
        self._slots.clear()
        self._history.clear()
        self._last_resolved_sources.clear()
        self._last_resolved_slots.clear()

    def __repr__(self) -> str:
        active = {k: v.surface for k, v in self._slots.items()}
        return f"ReferentRegistry(active={active})"

    def to_dict(self) -> dict[str, Any]:
        """Serialize, preserving the _slots <-> _history object aliasing.

        ``register`` puts the SAME ReferentEntry object in both ``_slots[slot]``
        and ``_history``; ``update_turn_versor`` relies on that identity
        (``_slots.get(slot) is entry``). We persist ``_history`` as the source of
        truth and ``_slots`` as slot -> history-index, so restore rebinds the
        exact same objects rather than independent copies.
        """
        slot_to_index: dict[str, int] = {}
        for slot, entry in self._slots.items():
            for i, hist_entry in enumerate(self._history):
                if hist_entry is entry:
                    slot_to_index[slot] = i
                    break
        return {
            "history": [e.to_dict() for e in self._history],
            "slot_to_index": slot_to_index,
            "last_resolved_sources": list(self._last_resolved_sources),
            "last_resolved_slots": dict(self._last_resolved_slots),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReferentRegistry":
        registry = cls()
        registry._history = [ReferentEntry.from_dict(e) for e in payload["history"]]
        registry._slots = {
            slot: registry._history[i]
            for slot, i in payload["slot_to_index"].items()
        }
        registry._last_resolved_sources = list(payload["last_resolved_sources"])
        registry._last_resolved_slots = dict(payload["last_resolved_slots"])
        return registry
