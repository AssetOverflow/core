"""Completeness leg of the candidate-graph reader's admissibility gate.

ADR-0191 — the candidate-graph reader checked *grounding* (every claimed
slot traces to a source token) and *round-trip* (the parsed candidate
re-realizes), but had no *completeness* obligation.  A problem whose
later clauses failed to parse into operations still emitted whatever
partial graph remained — the classic confabulation the derivation
reader's ``verify.py`` already refuses (grounding ∧ cue ∧ unit ∧
**completeness** ∧ uniqueness).

This module supplies the missing leg as a pure, side-effect-free check:

    Collect every numeric / multiplier quantity present in the source
    (all statement sentences + the question).  Collect every quantity the
    chosen reading actually CONSUMED (candidate provenance).  If a source
    quantity is not consumed, the reading is incomplete → the reader must
    refuse.

Design properties (why this preserves wrong==0 and cannot regress):

- **Refusal-only.**  The check only ever flips an emitted answer to a
  refusal; it never invents an answer.  So it can only *remove* wrong
  answers, never create one.
- **Set semantics, not multiset.**  ``uncovered = required - consumed``
  over value SETS.  This deliberately tolerates a source quantity echoed
  in the question (avoids false refusals) while still catching a clause
  whose distinct quantity was dropped — which is what every observed
  confabulation does.
- **Pack-authoritative number-sense.**  Quantities are resolved through
  the ``en_numerics_v1`` pack (``parse_compound_cardinal``) and the
  parser's own ``_resolve_value`` — the same machinery the extractors
  use.  Identical surface forms (``$40``, ``twenty-five``, ``one
  hundred``, ``3/4``) therefore resolve to identical values on both the
  required and the consumed side and cancel exactly; the guard never
  disagrees with the engine about what a number is.
- **Conservative multiplier set.**  Only the unambiguous multiplier
  anchors ``twice / thrice / half`` count as standalone quantity signals
  (these are not cardinals).  Ordinal-ambiguous words (``third`` /
  ``quarter`` — usually "the third day") are excluded to avoid spurious
  refusals.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from generate.math_candidate_parser import _CURRENCY_SYMBOLS, _resolve_value
from language_packs.numerics_loader import (
    lookup_cardinal,
    lookup_multiplier,
    parse_compound_cardinal,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from generate.math_candidate_parser import CandidateInitial
    from generate.math_roundtrip import CandidateOperation

# Multiplier-anchor quantity signals (``twice``/``double``/``half`` ...) are
# read from the en_numerics_v1 pack via ``lookup_multiplier`` — NOT hardcoded
# — so the guard never drifts from the pack lexicon (it carries twice,
# thrice, half, double, triple, quadruple, quintuple).  Ordinal-ambiguous
# words (``third`` / ``quarter``) are not multipliers in the pack, so they are
# excluded automatically rather than by a hand-maintained denylist.


def _multiplier_value(token: str) -> float | None:
    entry = lookup_multiplier(token)
    return float(entry.factor) if entry is not None else None


# Currency-symbol character class, taken from the parser's pinned symbol set
# (``$ ¢ € £ ¥ ₱``) so symbol-prefixed amounts tokenize as one span and
# resolve identically to the consumed candidate token.
_CURRENCY_CLASS = "".join(re.escape(c) for c in _CURRENCY_SYMBOLS)

# One pass that yields, in order: currency/digit/decimal/slash-fraction
# literals, and word tokens (incl. hyphenated cardinals like "twenty-five").
# Word runs are re-joined below so multi-word cardinals ("one hundred",
# "two thousand five hundred") resolve as a single quantity.
_TOKEN_RE = re.compile(
    rf"[{_CURRENCY_CLASS}]?\d[\d,]*(?:\.\d+)?(?:/\d+)?"  # $40 / 18.00 / 3/4
    r"|[A-Za-z]+(?:-[A-Za-z]+)*"                          # words incl. hyphenated
)


def _numeric_token_value(token: str) -> float | None:
    """Value of a single non-cardinal token (digit/currency/fraction)."""
    resolved = _resolve_value(token)
    return float(resolved.value) if resolved is not None else None


def _token_value(token: str) -> float | None:
    """Canonical numeric value of a single quantity token, or None.

    Multiplier anchors first, then compound cardinals (pack), then the
    parser's value resolver for digit / currency / fraction surface
    forms.  Used to normalize CONSUMED candidate tokens identically to
    the required scan.
    """
    if not token:
        return None
    t = token.strip()
    mult = _multiplier_value(t)
    if mult is not None:
        return mult
    cardinal = parse_compound_cardinal(t)
    if cardinal is not None:
        return float(cardinal)
    return _numeric_token_value(t)


def quantity_values_in_text(text: str) -> set[float]:
    """Every numeric / multiplier quantity value present in ``text``.

    Greedily merges runs of cardinal words (joined by hyphens or "and")
    so "two thousand five hundred" is one quantity, not five.  Digit /
    currency / fraction literals and multiplier anchors are resolved per
    token.  Pack-authoritative throughout.
    """
    if not text:
        return set()
    values: set[float] = set()
    tokens = _TOKEN_RE.findall(text)

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        low = tok.lower()
        # Multiplier anchor (standalone quantity signal), per the pack.
        mult = _multiplier_value(low)
        if mult is not None:
            values.add(mult)
            i += 1
            continue
        # Cardinal-word run: extend across adjacent cardinal words and
        # interior "and" connectors ("three hundred and fifty").
        if lookup_cardinal(low) is not None:
            run = [tok]
            j = i + 1
            while j < n:
                nxt = tokens[j].lower()
                if lookup_cardinal(nxt) is not None:
                    run.append(tokens[j])
                    j += 1
                elif nxt == "and" and j + 1 < n and lookup_cardinal(
                    tokens[j + 1].lower()
                ) is not None:
                    run.append(tokens[j])
                    j += 1
                else:
                    break
            v = parse_compound_cardinal(" ".join(run))
            if v is not None:
                values.add(float(v))
            i = j
            continue
        # Digit / currency / fraction literal.
        v = _numeric_token_value(tok)
        if v is not None:
            values.add(v)
        i += 1
    return values


def _candidate_consumed_tokens(
    choice: "CandidateInitial | CandidateOperation",
) -> tuple[str, ...]:
    """Source quantity tokens a single candidate consumed.

    Aggregating initials (day-enumeration, embedded-quantifier,
    multi-word-cardinal) collapse several source tokens into one derived
    value; they expose every consumed token via ``consumed_value_tokens``.
    Every other candidate consumes exactly its ``matched_value_token``.
    """
    consumed = getattr(choice, "consumed_value_tokens", ())
    if consumed:
        return tuple(consumed)
    tok = getattr(choice, "matched_value_token", "")
    return (tok,) if tok else ()


def consumed_values(branch: tuple[object, ...]) -> set[float]:
    """Canonical quantity values consumed by a chosen reading (branch)."""
    values: set[float] = set()
    for choice in branch:
        for tok in _candidate_consumed_tokens(choice):  # type: ignore[arg-type]
            v = _token_value(tok)
            if v is not None:
                values.add(v)
    return values


def uncovered_quantities(
    *,
    statement_sentences: list[str],
    question_text: str,
    branch: tuple[object, ...],
) -> set[float]:
    """Source quantities the chosen reading failed to consume.

    A non-empty result means the reading is incomplete: the source
    carries a quantity the solved graph never accounts for, so emitting
    its answer would confabulate.  The reader must refuse.
    """
    required: set[float] = set()
    for s in statement_sentences:
        required |= quantity_values_in_text(s)
    required |= quantity_values_in_text(question_text)
    return required - consumed_values(branch)
