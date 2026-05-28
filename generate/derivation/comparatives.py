"""ADR-0176 — comparative-scalar extraction from the en_core_comparatives_v1 pack.

Turns comparative lexemes into the scalar *operation* they license — the
irreducible world-facts the engine cannot derive from arithmetic (ADR-0175
section 10): ``twice`` -> x2, ``half`` -> x0.5, ``triple`` -> x3, and the
``<number> times`` pattern -> x<number>.

This supplies only the **scalar primitive**. *Which* quantity the scalar applies
to (the referent) is resolved by the multi-step search (ADR-0176), not here.

Closed-set + refusal-preferring: an uncovered comparative yields nothing, so the
search refuses rather than guesses. Lexeme-level per ADR-0165 (a comparative is an
orthographic shape; ``<number> times`` is number + lexeme).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from generate.derivation.model import Quantity, Step
from generate.math_roundtrip import WORD_NUMBERS

_PACK_DIR: Final[Path] = (
    Path(__file__).resolve().parents[2]
    / "language_packs"
    / "data"
    / "en_core_comparatives_v1"
)


@dataclass(frozen=True, slots=True)
class ComparativeScalar:
    """A comparative's scalar operation. ``cue`` is the licensing lexeme."""

    op: str  # "multiply"
    scalar: float
    source_span: str
    cue: str
    # The number token of a "<N> times" comparative (e.g. "7" / "three"), or None
    # for a fixed lexeme (twice/half). Used by completeness so a digit comparative
    # ("7 times") is counted as consuming the body quantity "7".
    number_token: str | None = None


@lru_cache(maxsize=1)
def _load_comparatives() -> dict[str, tuple[str, float]]:
    """Load the closed-set comparative lexeme -> (op, scalar) map from the pack."""
    out: dict[str, tuple[str, float]] = {}
    path = _PACK_DIR / "comparatives.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        out[entry["lexeme"]] = (entry["op"], float(entry["scalar"]))
    return out


# Word-numbers usable as the N in "<N> times" (e.g. "three times" -> x3).
_WORD_NUM_ALT: Final[str] = "|".join(
    re.escape(w) for w in sorted(WORD_NUMBERS, key=len, reverse=True)
)
_N_TIMES_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?i)\b(\d+(?:\.\d+)?|{_WORD_NUM_ALT})\s+times\b"
)


def _resolve_number(token: str) -> float | None:
    try:
        return float(token)
    except ValueError:
        return float(WORD_NUMBERS[token.lower()]) if token.lower() in WORD_NUMBERS else None


def extract_comparative_scalars(text: str) -> tuple[ComparativeScalar, ...]:
    """Extract comparative scalars in left-to-right text order. Deterministic.

    Emits a :class:`ComparativeScalar` for each present fixed comparative lexeme
    (``twice``/``half``/...) and each ``<number> times`` phrase. ``<number> times``
    takes precedence over a bare ``times`` so a fixed lexeme is never double-counted.
    """
    pack = _load_comparatives()
    found: list[tuple[int, ComparativeScalar]] = []

    # "<number> times" pattern (scalar = the number).
    for m in _N_TIMES_RE.finditer(text):
        n = _resolve_number(m.group(1))
        if n is None or n <= 0:
            continue
        found.append(
            (
                m.start(),
                ComparativeScalar("multiply", n, m.group(0), "times", number_token=m.group(1)),
            )
        )

    # Fixed comparative lexemes (word-boundary, case-insensitive).
    for lexeme, (op, scalar) in pack.items():
        for m in re.finditer(rf"(?i)\b{re.escape(lexeme)}\b", text):
            found.append(
                (m.start(), ComparativeScalar(op, scalar, m.group(0), lexeme))
            )

    found.sort(key=lambda pair: (pair[0], pair[1].cue))
    return tuple(cs for _, cs in found)


def comparative_step(cs: ComparativeScalar) -> Step:
    """Bridge a comparative scalar into a derivation :class:`Step` (ADR-0176 MS-2).

    The step is flagged ``comparative=True``: its operand value is the pack-supplied
    scalar (grounded by the comparative cue, not by a text value token). Its
    ``source_token`` is the ``<N> times`` number token when present (so completeness
    counts the consumed body quantity), else the comparative lexeme.
    """
    source = cs.number_token if cs.number_token is not None else cs.cue
    return Step(
        op=cs.op,
        operand=Quantity(value=cs.scalar, unit="", source_token=source),
        cue=cs.cue,
        comparative=True,
    )
