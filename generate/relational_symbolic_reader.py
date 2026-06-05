"""The SYMBOLIC reader for forward-substitutable quantitative relations.

The second, code-disjoint reading of the same micro-domain as
``generate.relational_field_reader`` — but it resolves by plain integer arithmetic
over a parsed schema, importing **no** ``algebra`` / ``field`` (proven import-disjoint
from the field reader by INV-27). It is:

- the control arm of the ablation experiment (does the geometric FIELD reader add any
  signal over a competent symbolic reader, or is it decoration?), and
- the C3 capability path if the field does not earn its role (a second independent
  reading whose agreement with another reader is the wrong=0 gate).

It is a *competent* reader, not a strawman: it reads the same grammar and applies the
same fences (multiplicative/ratio, forward-substitutability, negatives), and it
detects over-determination (a quantity stated two ways that conflict) and refuses —
so the ablation is a fair test. It has NO float/precision limit (pure int), so unlike
the field it commits arbitrarily large quantities.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Stable identity for the Tier-2 gate (registered in INV-27).
READER_LINEAGE: str = "symbolic.relational_schema"

_FENCED_CUE = re.compile(
    r"\b(times|twice|double|triple|thrice|half|quarter|ratio|per|each)\b"
)

# Independent regex set (own spelling/order) — same grammar, different implementation.
_REL_MORE = re.compile(r"(\w+) (?:has|have) (\d+) more \w+ than (\w+)")
_REL_FEWER = re.compile(r"(\w+) (?:has|have) (\d+) (?:fewer|less) \w+ than (\w+)")
_REL_FACT = re.compile(r"(\w+) (?:has|have) (\d+) (\w+)")
_Q_SINGLE = re.compile(r"how many (\w+) does (\w+) have")
_Q_SUM = re.compile(r"how many (\w+) do (\w+) and (\w+)(?: and (\w+))? have")


class SymbolicReaderError(ValueError):
    """Out-of-grammar case → typed refusal."""


@dataclass(frozen=True, slots=True)
class SymbolicReading:
    refused: bool
    answer: int | None = None
    answer_unit: str | None = None
    refusal_reason: str | None = None
    reader_lineage: str = READER_LINEAGE


def _refuse(reason: str) -> SymbolicReading:
    return SymbolicReading(refused=True, refusal_reason=reason)


def read_relational(text: str) -> SymbolicReading:
    if not isinstance(text, str) or not text.strip():
        return _refuse("empty_input")
    if _FENCED_CUE.search(text.lower()):
        return _refuse("fenced_multiplicative")
    try:
        return _read(text.lower())
    except SymbolicReaderError as exc:
        return _refuse(str(exc))


def _set(values: dict[str, int], entity: str, value: int) -> None:
    """Assign, detecting over-determination (a conflicting re-statement)."""
    if entity in values and values[entity] != value:
        raise SymbolicReaderError("over_determined_conflict")
    values[entity] = value


def _read(text: str) -> SymbolicReading:
    parts = [s.strip() for s in re.split(r"[.?!]", text) if s.strip()]

    unit: str | None = None
    q_single: str | None = None
    q_sum: list[str] | None = None
    for s in parts:
        if "how many" not in s:
            continue
        if (m := _Q_SUM.search(s)) is not None:
            unit = m.group(1)
            q_sum = [g for g in m.groups()[1:] if g]
        elif (m := _Q_SINGLE.search(s)) is not None:
            unit, q_single = m.group(1), m.group(2)
        else:
            raise SymbolicReaderError("unparsed_query")
        break
    if q_single is None and q_sum is None:
        raise SymbolicReaderError("no_query")

    values: dict[str, int] = {}
    for s in parts:
        if "how many" in s:
            continue
        if (m := _REL_MORE.search(s)) is not None:
            ent, n, ref = m.group(1), int(m.group(2)), m.group(3)
            if ref not in values:
                raise SymbolicReaderError("non_forward_substitutable")
            _set(values, ent, values[ref] + n)
        elif (m := _REL_FEWER.search(s)) is not None:
            ent, n, ref = m.group(1), int(m.group(2)), m.group(3)
            if ref not in values:
                raise SymbolicReaderError("non_forward_substitutable")
            _set(values, ent, values[ref] - n)
        elif (m := _REL_FACT.search(s)) is not None:
            ent, n = m.group(1), int(m.group(2))
            _set(values, ent, n)
        else:
            raise SymbolicReaderError("unparsed_sentence")

    if q_single is not None:
        if q_single not in values:
            raise SymbolicReaderError("query_entity_unresolved")
        answer = values[q_single]
    else:
        assert q_sum is not None
        if any(p not in values for p in q_sum):
            raise SymbolicReaderError("query_entity_unresolved")
        answer = sum(values[p] for p in q_sum)

    if answer < 0:
        raise SymbolicReaderError("negative_quantity")
    return SymbolicReading(refused=False, answer=answer, answer_unit=unit)
