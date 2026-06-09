"""Typed terminal states + per-pass findings for the contemplation pass manager (N6).

v0 is a single bounded pass chain — no loops, no daemon, no L10 runtime. Each pass appends a
``Finding`` (a traceable artifact, not hidden chain-of-thought), and the chain ends in exactly
one ``Terminal`` state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Terminal(str, Enum):
    """The terminal state of one bounded contemplation pass."""

    SOLVED_VERIFIED = "SOLVED_VERIFIED"
    REFUSED_KNOWN_BOUNDARY = "REFUSED_KNOWN_BOUNDARY"
    REFUSED_UNSUPPORTED_FAMILY = "REFUSED_UNSUPPORTED_FAMILY"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    PROPOSAL_EMITTED = "PROPOSAL_EMITTED"
    # The ASK tenant (Q1-D): a solvable attempt blocked on missing/ambiguous *input*
    # that a grounded question can intake. A SIBLING of PROPOSAL_EMITTED, never a
    # subtype — a proposal offers a capability for review; a question requests a datum
    # from the user. Off-serving: produced by the Q1-D delivery layer into the
    # teaching/questions sink, never served until a future ask_serving_enabled gate.
    QUESTION_NEEDED = "QUESTION_NEEDED"
    AMBIGUOUS_ORGAN = "AMBIGUOUS_ORGAN"
    NO_PROGRESS = "NO_PROGRESS"


@dataclass(frozen=True, slots=True)
class Finding:
    """One pass's typed result — name of the pass and a short summary of what it observed."""

    pass_name: str
    summary: str


__all__ = ["Finding", "Terminal"]
