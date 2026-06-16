"""Field incidence reader — the SUT for the section-level coherence probe (option A).

Reads an over-determined 2-D incidence configuration (named points + claims of the
form "point P lies on the line through A and B") and decides whether the configuration
is jointly CONSISTENT, using ONLY the field's incidence algebra: each point embeds as a
conformal null vector, each line is the grade-3 OPNS flat ``A ^ B ^ n_inf``
(`graded_wedge`), and incidence is the EXACT ``P ^ line == 0`` zero-test
(`is_incident`). No float tolerance to admit (per wrong=0): a point off a line is
refused, never accepted as on it.

This is deliberately the FIELD doing the read geometrically. The probe
(`evals/field_incidence/ablation.py`) measures whether that read is independent of —
or merely reducible to — a fair rational-arithmetic incidence control over the same
grammar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from algebra.cga import EMBED_EXACT_MAX, embed_point, graded_wedge, is_incident
from algebra.cl41 import N_COMPONENTS

READER_LINEAGE = "field.incidence_2d"
_F64 = np.float64


@dataclass(frozen=True, slots=True)
class IncidenceReading:
    refused: bool
    verdict: str | None = None  # "consistent" | "inconsistent"
    refusal_reason: str | None = None
    reader_lineage: str = READER_LINEAGE


def _n_inf() -> np.ndarray:
    v = np.zeros(N_COMPONENTS, dtype=_F64)
    v[4] = 1.0
    v[5] = 1.0
    return v


def _embed2d(xy: list) -> np.ndarray:
    return embed_point(np.array([float(xy[0]), float(xy[1]), 0.0], dtype=_F64), dtype=_F64)


def read_incidence(points: dict, incidences: list) -> IncidenceReading:
    """Decide joint incidence consistency geometrically, or refuse out-of-regime."""
    if not points or not incidences:
        return IncidenceReading(refused=True, refusal_reason="empty_case")
    for xy in points.values():
        if not (isinstance(xy, list) and len(xy) == 2):
            return IncidenceReading(refused=True, refusal_reason="malformed_point")
        if max(abs(float(xy[0])), abs(float(xy[1]))) > EMBED_EXACT_MAX:
            return IncidenceReading(refused=True, refusal_reason="over_ceiling")

    embedded = {name: _embed2d(xy) for name, xy in points.items()}
    n_inf = _n_inf()

    for inc in incidences:
        if len(inc) != 3 or any(n not in embedded for n in inc):
            return IncidenceReading(refused=True, refusal_reason="malformed_incidence")
        p, a, b = inc
        if a == b:
            return IncidenceReading(refused=True, refusal_reason="degenerate_line")
        line = graded_wedge(graded_wedge(embedded[a], embedded[b]), n_inf)
        if not is_incident(embedded[p], line):
            return IncidenceReading(refused=False, verdict="inconsistent")
    return IncidenceReading(refused=False, verdict="consistent")
