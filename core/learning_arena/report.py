"""ADR-0199 / ADR-0175 — the domain-agnostic practice report.

Extracted verbatim (schema-preserving) from
``evals/gsm8k_math/practice/v1/runner.py`` so every subject's arena emits the
same report shape. ``PracticeReport.as_dict`` is byte-stable with the original
GSM8K report so existing goldens and ``report.json`` are unaffected.

The three refusal-diagnosis axes are the universal ADR-0175 §8 router
(skill / knowledge / ambiguity), not a domain quantity — so they live here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from core.reliability_gate import ClassTally

# ADR-0175 §8 — the universal "name the missing piece" axes.
REFUSAL_DIAGNOSES: tuple[str, ...] = ("skill_gap", "knowledge_gap", "genuine_ambiguity")


@dataclass(frozen=True, slots=True)
class EliminationRecord:
    """A wrong practice attempt that gold caught — the pruning signal (§9)."""

    case_id: str
    class_name: str
    attempted: float | None
    gold: float
    reason: str


def bucket_counts(diagnoses: Mapping[str, str]) -> dict[str, int]:
    out = {d: 0 for d in REFUSAL_DIAGNOSES}
    for d in diagnoses.values():
        out[d] = out.get(d, 0) + 1
    return out


@dataclass(frozen=True, slots=True)
class PracticeReport:
    counts: Mapping[str, int]
    ledger: Mapping[str, ClassTally]
    refusal_diagnoses: Mapping[str, str]
    elimination_records: tuple[EliminationRecord, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "adr": "0175",
            "regime": "practice",
            "counts": dict(self.counts),
            "per_class": {
                cls: {
                    "correct": t.correct,
                    "wrong": t.wrong,
                    "refused": t.refused,
                    "committed": t.committed,
                    "reliability": t.reliability,
                    "coverage": t.coverage,
                }
                for cls, t in sorted(self.ledger.items())
            },
            "refusal_diagnoses": dict(sorted(self.refusal_diagnoses.items())),
            "diagnosis_counts": bucket_counts(self.refusal_diagnoses),
            "elimination_records": [
                {
                    "case_id": r.case_id,
                    "class_name": r.class_name,
                    "attempted": r.attempted,
                    "gold": r.gold,
                    "reason": r.reason,
                }
                for r in self.elimination_records
            ],
        }
