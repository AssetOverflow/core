"""Cognition eval metrics — deterministic, compact measurements."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    category: str
    prompt: str
    intent_correct: bool
    terms_captured: tuple[str, ...]
    terms_expected: tuple[str, ...]
    surface_contains_pass: bool
    versor_closure: bool
    versor_condition: float
    trace_hash: str
    surface: str


@dataclass(slots=True)
class EvalReport:
    total: int = 0
    intent_correct: int = 0
    terms_captured: int = 0
    terms_expected: int = 0
    surface_grounded: int = 0
    versor_closures: int = 0
    deterministic_traces: int = 0
    cases: list[CaseResult] = field(default_factory=list)
    trace_hashes: dict[str, str] = field(default_factory=dict)

    @property
    def intent_accuracy(self) -> float:
        return self.intent_correct / self.total if self.total else 0.0

    @property
    def term_capture_rate(self) -> float:
        return self.terms_captured / self.terms_expected if self.terms_expected else 1.0

    @property
    def surface_groundedness(self) -> float:
        return self.surface_grounded / self.total if self.total else 0.0

    @property
    def versor_closure_rate(self) -> float:
        return self.versor_closures / self.total if self.total else 0.0

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "intent_accuracy": round(self.intent_accuracy, 4),
            "term_capture_rate": round(self.term_capture_rate, 4),
            "surface_groundedness": round(self.surface_groundedness, 4),
            "versor_closure_rate": round(self.versor_closure_rate, 4),
            "deterministic_traces": self.deterministic_traces,
            "trace_hashes": dict(self.trace_hashes),
            "cases": [
                {
                    "case_id": c.case_id,
                    "category": c.category,
                    "intent_correct": c.intent_correct,
                    "surface_contains_pass": c.surface_contains_pass,
                    "versor_closure": c.versor_closure,
                    "versor_condition": round(c.versor_condition, 9),
                    "trace_hash": c.trace_hash,
                    "surface": c.surface,
                }
                for c in self.cases
            ],
        }
