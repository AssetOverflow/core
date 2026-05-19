"""chat/thread_context.py — Phase 3.1: session-thread state.

The runtime today treats each turn as an independent grounded surface.
There is no thread-level memory: a turn cannot reference what was
established three turns ago, even when the same subject reappears.
That is the *articulation gap* in plain terms — conversation reads
mechanical because each turn is freshly minted, never referenced
backward.

This module is the data primitive that closes that gap.  Phase 3.1
stores; Phase 3.2 (anaphora composer) reads.  Surface emission is
unchanged at P3.1 — turning the data layer on cannot regress any
existing test.

Design constraints (matching CLAUDE.md doctrine):

- **Bounded.**  Capacity ``MAX_THREAD_TURNS`` (default 8).  Older
  summaries evict in FIFO order; thread context is *not* a long-term
  store, it is a small recency window the anaphora composer can
  reference.  Long-term memory is the vault.
- **Immutable summaries.**  ``TurnSummary`` is frozen.  Pushing
  produces a new entry; never mutates an existing one.
- **No reconstruction from surface.**  The summary carries only
  structured fields (intent_tag, subject, grounding_source,
  chain_id).  Full surface text stays in the audit trail
  (``rt.turn_log``); thread context references only the shape.
- **No clock-time reads.**  Determinism — replays of the same
  sequence of turns produce identical thread state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable


# Recency window size.  8 is large enough for typical multi-turn
# anaphora ("As we established two turns ago..." through to "earlier
# in this conversation...") without giving the anaphora composer a
# context bigger than the surface itself.  Operators can override
# at construction time via :class:`ThreadContext(max_turns=N)`.
MAX_THREAD_TURNS: int = 8


@dataclass(frozen=True, slots=True)
class TurnSummary:
    """One structured record summarising a turn for thread-anaphora
    lookup.  Frozen — the runtime never mutates a pushed summary.

    Fields:
      - ``turn_index``: monotonic integer (0-based).  Same numbering
        as ``rt.turn_log``.
      - ``intent_tag_name``: lowercase intent name (``"cause"``,
        ``"definition"``, etc.).  Lowercased for case-insensitive
        match against new turns.
      - ``subject``: lowercased subject lemma (normalised to match
        the pack-resolver layer).  Empty string when the turn had no
        clean subject.
      - ``grounding_source``: ``"vault" | "teaching" | "pack" |
        "partial" | "oov" | "none"`` — the tier the turn surfaced
        through.  Anaphora is most useful when both turns surfaced
        through ``"pack"`` or ``"teaching"`` (deterministic
        backreference); the composer can choose to skip vault /
        partial / oov / none on its own policy.
      - ``chain_id``: present when ``grounding_source == "teaching"``,
        else ``None``.  Lets the anaphora composer detect "same
        chain referenced again" vs "different chain on same subject".
      - ``corpus_id``: present when ``grounding_source == "teaching"``,
        else ``None``.  Cross-corpus thread anaphora reads the
        corpus tag back to the user.
    """

    turn_index: int
    intent_tag_name: str
    subject: str
    grounding_source: str
    chain_id: str | None = None
    corpus_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "intent_tag_name": self.intent_tag_name,
            "subject": self.subject,
            "grounding_source": self.grounding_source,
            "chain_id": self.chain_id,
            "corpus_id": self.corpus_id,
        }


class ThreadContext:
    """Bounded FIFO of :class:`TurnSummary` records.

    Owned by :class:`chat.runtime.ChatRuntime`; updated after each
    turn.  Read-only from outside the runtime — tests can inspect
    via ``rt.thread_context.snapshot()``.
    """

    __slots__ = ("_deque", "_max_turns")

    def __init__(self, *, max_turns: int = MAX_THREAD_TURNS) -> None:
        if max_turns < 1:
            raise ValueError(f"max_turns must be >= 1 (got {max_turns!r})")
        self._max_turns = max_turns
        self._deque: deque[TurnSummary] = deque(maxlen=max_turns)

    @property
    def max_turns(self) -> int:
        return self._max_turns

    def __len__(self) -> int:
        return len(self._deque)

    def push(self, summary: TurnSummary) -> None:
        """Append a new turn summary; evict the oldest if at capacity."""
        if not isinstance(summary, TurnSummary):  # pragma: no cover — defensive
            raise TypeError(f"expected TurnSummary, got {type(summary).__name__}")
        self._deque.append(summary)

    def snapshot(self) -> tuple[TurnSummary, ...]:
        """Return an immutable tuple of every retained summary, in
        insertion order (oldest first)."""
        return tuple(self._deque)

    def recent_for_subject(
        self,
        subject: str,
        *,
        exclude_grounding: Iterable[str] = ("none", "oov", "partial"),
    ) -> TurnSummary | None:
        """Return the most-recent summary whose ``subject`` matches
        *subject* (case-insensitive, whitespace-trimmed), or ``None``.

        Summaries with ``grounding_source`` in *exclude_grounding* are
        skipped by default — they carry less anchor evidence than
        pack/teaching turns and the anaphora composer's "as we just
        established" reads false if the prior turn was actually
        ungrounded.  Operators can pass ``exclude_grounding=()`` to
        include every prior turn.
        """
        if not subject or not isinstance(subject, str):
            return None
        key = subject.strip().lower()
        if not key:
            return None
        excluded = frozenset(exclude_grounding)
        for summary in reversed(self._deque):
            if summary.grounding_source in excluded:
                continue
            if summary.subject == key:
                return summary
        return None

    def recent_subjects(
        self,
        *,
        exclude_grounding: Iterable[str] = ("none", "oov", "partial"),
    ) -> tuple[str, ...]:
        """Return the set of unique subjects in the window, ordered by
        most-recent-first.  Skips empty subjects and any whose
        grounding tier is in *exclude_grounding*."""
        excluded = frozenset(exclude_grounding)
        seen: set[str] = set()
        ordered: list[str] = []
        for summary in reversed(self._deque):
            if summary.grounding_source in excluded:
                continue
            if not summary.subject or summary.subject in seen:
                continue
            seen.add(summary.subject)
            ordered.append(summary.subject)
        return tuple(ordered)

    def clear(self) -> None:
        """Drop every retained summary.  Used by tests + by callers
        that explicitly reset session memory."""
        self._deque.clear()


__all__ = ["TurnSummary", "ThreadContext", "MAX_THREAD_TURNS"]
