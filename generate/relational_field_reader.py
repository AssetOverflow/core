"""The geometric FIELD reader for forward-substitutable quantitative relations.

Phase W of the field-reasoner wedge
(docs/analysis/field-reasoner-wedge-design-and-falsification-2026-06-04.md).

This is the system under test: it reads problem **text** into conformal points on
the e1 number line (``algebra.cga.embed_point`` at float64), resolves each unknown
by applying a conformal **translator versor** (``algebra.versor.versor_apply``), and
reads the answer back by **projective dehomogenization** (``read_scalar_e1``). The
resolution is genuinely geometric: ``versor_apply(T_delta, embed([x])) == embed([x+δ])``
exactly (verified), so "A is δ more than B" is a translation, not a hidden add.

It is a **second, hand-written reader**: its tokenizer / number extraction / relation
classification are an independent reimplementation. It imports **nothing** from
``generate.derivation`` / ``generate.math_candidate_parser`` / ``generate.math_*`` /
``WORD_NUMBERS`` — so its agreement with a symbolic reader is not common-mode by
construction (the disjointness is *proven* by INV-27, not asserted here).

**Refusal-first.** It commits an answer only inside a narrow, sealed grammar
(digit integers; ``has``/``more``/``fewer``/``than``/``how many`` cues; additive and
part-whole only). It REFUSES — never guesses — on:

- multiplicative / ratio cues (``times``/``twice``/``double``/``ratio`` …) — fenced,
  because ``cga_inner`` is sign/orientation-blind (A=2B vs A=−2B);
- any quantity above :data:`algebra.cga.EMBED_EXACT_MAX` (precision ceiling);
- a non-forward-substitutable reference (an unknown referenced before it is defined);
- a negative resolved quantity, a non-integer read-back, or any unparsed sentence.

The answer is exact-integer; there is no float tolerance anywhere on the commit path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from algebra.cga import EMBED_EXACT_MAX, embed_point, read_scalar_e1
from algebra.cl41 import N_COMPONENTS, geometric_product
from algebra.versor import versor_apply

# The reader's stable identity for the Tier-2 gate (registered in INV-27).
READER_LINEAGE: str = "field.relational_number_line"

_F64 = np.float64

# Multiplicative / ratio cues are out of the sealed metric domain — refuse.
_FENCED_CUE = re.compile(
    r"\b(times|twice|double|triple|thrice|half|quarter|ratio|per|each)\b"
)

_MORE_THAN = re.compile(r"\b(\w+)\s+(?:has|have)\s+(\d+)\s+more\s+\w+\s+than\s+(\w+)")
_FEWER_THAN = re.compile(
    r"\b(\w+)\s+(?:has|have)\s+(\d+)\s+(?:fewer|less)\s+\w+\s+than\s+(\w+)"
)
_FACT = re.compile(r"\b(\w+)\s+(?:has|have)\s+(\d+)\s+(\w+)")
_QUERY_SINGLE = re.compile(r"how many\s+(\w+)\s+does\s+(\w+)\s+have")
_QUERY_SUM = re.compile(
    r"how many\s+(\w+)\s+do\s+(\w+)\s+and\s+(\w+)(?:\s+and\s+(\w+))?\s+have"
)


class FieldReaderError(ValueError):
    """Internal signal that a case is out of the sealed grammar (→ typed refusal)."""


@dataclass(frozen=True, slots=True)
class FieldReading:
    """Result of the geometric reading. ``answer is None`` iff ``refused``."""

    refused: bool
    answer: int | None = None
    answer_unit: str | None = None
    refusal_reason: str | None = None
    reader_lineage: str = READER_LINEAGE


def _refuse(reason: str) -> FieldReading:
    return FieldReading(refused=True, refusal_reason=reason)


def _translator_e1(delta: int) -> np.ndarray:
    """The conformal translator versor that shifts an e1-axis point by ``delta``.

    ``T = 1 − ½·(δ·e1)·n_inf`` with ``n_inf = e4 + e5``. For null n_inf the
    exponential series truncates exactly, so ``versor_apply(T, embed([x]))`` lands
    on ``embed([x+δ])`` with zero residual (the metric stays exact in f64).
    """
    n_inf = np.zeros(N_COMPONENTS, dtype=_F64)
    n_inf[4] = 1.0
    n_inf[5] = 1.0
    e1 = np.zeros(N_COMPONENTS, dtype=_F64)
    e1[1] = float(delta)
    t = geometric_product(e1, n_inf)
    rotor = np.zeros(N_COMPONENTS, dtype=_F64)
    rotor[0] = 1.0
    return rotor - 0.5 * t


def _check_magnitude(value: int) -> None:
    if abs(value) > EMBED_EXACT_MAX:
        raise FieldReaderError("over_ceiling")


def _apply_delta(point: np.ndarray, delta: int) -> np.ndarray:
    """Translate an e1 point by ``delta`` and PROVE the move was exact.

    The translator sandwich loses f64 integer exactness when ``δ·x²`` approaches
    2^52, which would silently commit a plausible-but-wrong integer (the resolve_pooled
    failure mode). So we verify the read-back moved by *exactly* ``delta`` and refuse
    (``precision_drift``) otherwise — the field never commits a drifted answer.
    """
    before = _read_int(point)
    moved = versor_apply(_translator_e1(delta), point)
    if read_scalar_e1(moved) != before + delta:  # exact integer move, or refuse
        raise FieldReaderError("precision_drift")
    return moved


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.?!]", text.lower()) if s.strip()]


def read_relational(text: str) -> FieldReading:
    """Read problem ``text`` geometrically into an exact integer answer, or refuse."""
    if not isinstance(text, str) or not text.strip():
        return _refuse("empty_input")
    if _FENCED_CUE.search(text.lower()):
        return _refuse("fenced_multiplicative")

    try:
        return _read(text)
    except FieldReaderError as exc:
        return _refuse(str(exc))


def _read(text: str) -> FieldReading:
    sentences = _sentences(text)

    # --- locate the query (the question sentence) -------------------------------
    query_unit: str | None = None
    query_single: str | None = None
    query_parts: list[str] | None = None
    for s in sentences:
        if "how many" in s:
            if (m := _QUERY_SUM.search(s)) is not None:
                query_unit = m.group(1)
                query_parts = [g for g in m.groups()[1:] if g]
            elif (m := _QUERY_SINGLE.search(s)) is not None:
                query_unit = m.group(1)
                query_single = m.group(2)
            else:
                raise FieldReaderError("unparsed_query")
            break
    if query_single is None and query_parts is None:
        raise FieldReaderError("no_query")

    # --- parse the declarative sentences, in order ------------------------------
    points: dict[str, np.ndarray] = {}

    def resolve(entity: str) -> None:
        if entity not in points:
            raise FieldReaderError("non_forward_substitutable")

    for s in sentences:
        if "how many" in s:
            continue
        if (m := _MORE_THAN.search(s)) is not None:
            entity, n, ref = m.group(1), int(m.group(2)), m.group(3)
            _check_magnitude(n)
            resolve(ref)
            points[entity] = _apply_delta(points[ref], n)
        elif (m := _FEWER_THAN.search(s)) is not None:
            entity, n, ref = m.group(1), int(m.group(2)), m.group(3)
            _check_magnitude(n)
            resolve(ref)
            points[entity] = _apply_delta(points[ref], -n)
        elif (m := _FACT.search(s)) is not None:
            entity, n = m.group(1), int(m.group(2))
            _check_magnitude(n)
            points[entity] = embed_point(np.array([float(n), 0.0, 0.0]), dtype=_F64)
        else:
            raise FieldReaderError("unparsed_sentence")

    # --- read the answer back off the geometry ----------------------------------
    if query_single is not None:
        if query_single not in points:
            raise FieldReaderError("query_entity_unresolved")
        answer = _read_int(points[query_single])
    else:
        assert query_parts is not None
        total = embed_point(np.array([0.0, 0.0, 0.0]), dtype=_F64)
        for part in query_parts:
            if part not in points:
                raise FieldReaderError("query_entity_unresolved")
            total = _apply_delta(total, _read_int(points[part]))
        answer = _read_int(total)

    if answer < 0:
        raise FieldReaderError("negative_quantity")
    return FieldReading(refused=False, answer=answer, answer_unit=query_unit)


def _read_int(point: np.ndarray) -> int:
    """Projective read-back, refusing any non-integer coordinate (no float slack)."""
    value = read_scalar_e1(point)
    rounded = round(value)
    if abs(value - rounded) > 0.0:  # exact-integer commit path; no tolerance
        raise FieldReaderError("non_integer_readback")
    return int(rounded)
