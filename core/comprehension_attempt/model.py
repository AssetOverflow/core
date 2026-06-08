"""Typed, immutable record of one comprehension organ's attempt at a problem (N2).

A small normalization layer over the R1 (`generate.quantitative_comprehension`) and R2
(`generate.constraint_comprehension`) setup compilers: it turns each organ's heterogeneous
output (a typed setup, or a typed `Refusal`) into one uniform, frozen `ComprehensionAttempt`.
Nothing here changes reader behavior — it only *describes* an outcome so the router (N3),
failure-family registry (N4), and contemplation pass manager (N6) can reason over both organs
uniformly.

Outcome semantics. `classify` (N2) produces **produce-mode** outcomes — what the organ did on
its own gates, with no gold in hand: `setup_refused` (the organ refused) or `setup_correct`
(an admissible setup was produced). The gold-relative outcomes (`setup_wrong`, `answer_wrong`)
are representable here but are emitted only in **eval mode** by the lanes that hold gold — never
fabricated by `classify`. `answer_*` / `contradiction` are reached when the solver / answer-choice
verifier run downstream (N6), not at setup classification time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from generate.binding_graph.model import SourceSpanLink

Organ = Literal["r1_quantitative", "r2_constraints", "r3_rate"]

Outcome = Literal[
    "setup_correct",   # an admissible setup was produced (produce-mode) / matches gold (eval-mode)
    "setup_refused",   # the organ refused to assemble a setup
    "setup_wrong",     # eval-mode only: produced setup diverges from gold (a wrong=0 breach)
    "answer_correct",  # a value was produced and self-verified / matches gold
    "answer_refused",  # setup produced but the solver/verifier refused
    "answer_wrong",    # eval-mode only: produced value diverges from gold
    "contradiction",   # a verified value contradicts a supplied answer key
]


@dataclass(frozen=True, slots=True)
class ComprehensionAttempt:
    """One organ's attempt at one problem. Immutable; carries the outcome, the refusal reason
    (if any), a deterministic setup signature (for cross-organ comparison), the answer (if a
    value was produced), and source-span evidence. ``family`` is left ``None`` by ``classify``
    and resolved later by the N4 failure-family registry."""

    organ: Organ
    outcome: Outcome
    case_id: str | None = None
    refusal_reason: str | None = None
    family: str | None = None
    setup_signature: str | None = None
    answer: int | None = None
    evidence: tuple[SourceSpanLink, ...] = ()

    @property
    def is_setup_correct(self) -> bool:
        return self.outcome == "setup_correct"

    @property
    def is_refusal(self) -> bool:
        return self.outcome in ("setup_refused", "answer_refused")


__all__ = ["ComprehensionAttempt", "Organ", "Outcome"]
