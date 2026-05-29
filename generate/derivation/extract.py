"""ADR-0175 Phase 3b / ADR-0179 — lexeme-level quantity extraction.

Pulls ``(value, unit, source_token)`` triples from a problem using conservative
orthographic patterns. Per ADR-0165 these are *lexeme* patterns ("what this
piece looks like: a number, a unit word") — never grammar templates ("how words
combine to mean X"). The *combining* is the search's job (search.py / compose.py)
gated by self-verification, which is refuse-preferring; over-extraction here can
only cost *refusals*, never a wrong answer.

ADR-0179 enrichments integrated here (sealed lane only — ``chat/`` does not import
this module, so none of this can move the serving ``3/47/0``):

* **EX-1 — word-numbers.** ``"three apples"`` → ``3.0``, including tens-one
  hyphen compounds (``"twenty-four"`` → ``24.0``). Reuses the canonical
  ``WORD_NUMBERS`` table from :mod:`generate.math_roundtrip` (single number
  vocabulary). Factor-bearing forms (``half``/``third``/``quarter``) are excluded
  — they read as divisors, not counts.
* **EX-4 — list-unit inheritance.** In a bare numeric list with the unit stated
  once at the end (``"20, 36, 40 and 50 push-ups"``) the trailing unit attaches
  to every number in the list. Still orthographic: a run of number tokens joined
  by comma/``and`` delimiters, then one unit token. Whether the resulting
  quantities may compose is the gate's decision, not the extractor's.
* **EX-5 — sentence-final numbers.** A number with no following unit word (end of
  sentence/text or before terminal punctuation) extracts with an empty unit so it
  stays available to the completeness check without inventing a unit lexeme.

EX-3 (multi-word units) is deliberately **not** integrated. Two distinct traps
defeat the tightest lookahead-anchored rule the brief admits:

1. **Connective-crossing** (in
   ``docs/handoff/AUDIT-ADR-0179-EX-RECONCILE.md``). The greedy lowercase unit
   span regresses GB-2's same-unit detection (``"6 apples and 4 apples"`` → unit
   ``"apples and"``) and does not cleanly recover real multi-word units from
   0024-class text (``"20 jumping jacks on Monday"`` → ``"jumping jacks on"``).
2. **Postmodifier-adjective tails** (discovered during the Track C redo of
   ``docs/handoff/PARALLEL-WORK-PLAN-2026-05-29.md``). Even a *tight*
   ``digit + lc word + lc word + (?=clause-terminator)`` rule fires on
   ``"25 years old?"`` and produces unit ``"years old"`` instead of
   ``"years"`` — regressing
   ``tests/test_adr_0176_ms1_question_target.py::TestQuestionQuantities::test_extracts_quantity_stated_in_question``.
   The pattern is endemic: GSM8K cases 0006/0033 and several MS2 chain tests use
   ``"X years old"``. Closing it would need a second closed lexeme set (a stop
   list of measurement postmodifiers — ``old``, ``tall``, ``long``, ``wide``,
   ``deep``, ``high``, ``away``, ``apart``, ``ago``, …) which the audit did not
   anticipate and which the Track C brief judged too open-ended to enumerate
   responsibly. ``TestEX3StillDeferred`` in
   ``tests/test_adr_0179_extract.py`` pins this second trap so no future redo
   silently re-introduces it.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.model import Quantity
from generate.math_roundtrip import WORD_NUMBERS

# Number (int or decimal) immediately followed by a single unit word. Lexeme-level.
_QTY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)\s+([a-zA-Z]+)"
)

# EX-4: a same-unit numeric list with the unit stated once at the end, e.g.
# ``20, 36, 40 and 50 push-ups``. A run of number tokens separated by comma/and
# delimiters, followed by one (optionally hyphenated) unit token.
_LIST_WITH_TRAILING_UNIT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])"
    r"((?:\d+(?:\.\d+)?\s*(?:,\s*|\s+and\s+)){1,}\d+(?:\.\d+)?)"
    r"\s+([a-zA-Z]+(?:-[a-zA-Z]+)*)"
)
_NUMBER_RE: Final[re.Pattern[str]] = re.compile(r"\d+(?:\.\d+)?")

# EX-1: word-number (optionally a tens-one hyphen compound) followed by a unit
# word. Built from the round-trip table; factor-bearing forms excluded.
_WORD_NUMBER_ALT: Final[str] = "|".join(
    re.escape(word)
    for word in sorted(WORD_NUMBERS, key=len, reverse=True)
    if word not in {"half", "third", "quarter"}
)
_WORD_QTY_RE: Final[re.Pattern[str]] = re.compile(
    rf"(?i)\b({_WORD_NUMBER_ALT})(?:-({_WORD_NUMBER_ALT}))?\s+([a-zA-Z]+)\b"
)

# EX-5: a number with no following unit, at end of sentence/text.
_FINAL_NUMBER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)(?=\s*(?:[.?!]|$))"
)


def _quantity(value_token: str, unit: str) -> Quantity | None:
    """Build a quantity from an already-matched numeric token."""
    try:
        value = float(value_token)
    except ValueError:  # pragma: no cover - regex guarantees numeric
        return None
    return Quantity(value=value, unit=unit.lower(), source_token=value_token)


def _resolve_word_number(first: str, second: str | None) -> float | None:
    """Resolve a conservative word-number token from ``WORD_NUMBERS``.

    A bare word resolves directly. A hyphen compound resolves only as a tens-one
    form (``twenty-four``, ``ninety-nine``); anything else returns ``None`` so the
    extractor stays conservative rather than guessing a composition rule.
    """
    first_value = WORD_NUMBERS.get(first.lower())
    if first_value is None:
        return None
    if second is None:
        return float(first_value)
    second_value = WORD_NUMBERS.get(second.lower())
    if second_value is None:
        return None
    if first_value < 20 or first_value >= 100 or not 0 < second_value < 10:
        return None
    return float(first_value + second_value)


def _claimed(pos: int, spans: list[tuple[int, int]]) -> bool:
    """Whether a numeric token at ``pos`` was already claimed by an earlier pass."""
    return any(start <= pos < end for start, end in spans)


def extract_quantities(problem_text: str) -> tuple[Quantity, ...]:
    """Extract ``(value, unit, source_token)`` quantities in left-to-right order.

    Deterministic. ``source_token`` is the surface number string (used by the
    self-verification gate to prove the value is grounded in the text). Units are
    lowercased; the value's surface token is preserved verbatim.

    Passes run most-specific first and claim the digit spans they consume so later
    passes never double-count a number:

    1. EX-4 same-unit list (claims every number in the list);
    2. digit + single unit word (skips numbers a list already claimed);
    3. EX-1 word-number + unit word (alphabetic, disjoint from digit spans);
    4. EX-5 sentence-final bare number (skips any already-claimed digit).
    """
    found: list[tuple[int, Quantity]] = []
    claimed: list[tuple[int, int]] = []

    # 1. EX-4 — list with one trailing unit; the unit inherits to every number.
    for match in _LIST_WITH_TRAILING_UNIT_RE.finditer(problem_text):
        unit = match.group(2).lower()
        for num in _NUMBER_RE.finditer(match.group(1)):
            pos = match.start(1) + num.start()
            quantity = _quantity(num.group(0), unit)
            if quantity is not None:
                found.append((pos, quantity))
                claimed.append((pos, pos + len(num.group(0))))

    # 2. digit + single unit word — the original base pattern.
    for match in _QTY_RE.finditer(problem_text):
        if _claimed(match.start(1), claimed):
            continue
        quantity = _quantity(match.group(1), match.group(2))
        if quantity is not None:
            found.append((match.start(1), quantity))
            claimed.append(match.span(1))

    # 3. EX-1 — word-numbers (and tens-one hyphen compounds) with a unit word.
    for match in _WORD_QTY_RE.finditer(problem_text):
        value = _resolve_word_number(match.group(1), match.group(2))
        if value is None:
            continue
        source_token = (
            match.group(1)
            if match.group(2) is None
            else match.group(0).rsplit(maxsplit=1)[0]
        )
        found.append(
            (
                match.start(1),
                Quantity(value=value, unit=match.group(3).lower(), source_token=source_token),
            )
        )

    # 4. EX-5 — sentence-final bare numbers (empty unit).
    for match in _FINAL_NUMBER_RE.finditer(problem_text):
        if _claimed(match.start(1), claimed):
            continue
        quantity = _quantity(match.group(1), "")
        if quantity is not None:
            found.append((match.start(1), quantity))

    found.sort(key=lambda item: item[0])
    return tuple(quantity for _, quantity in found)
