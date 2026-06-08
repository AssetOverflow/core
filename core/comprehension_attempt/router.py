"""Deterministic multi-organ setup router (N3).

Boring on purpose: attempt the R1 and R2 setup compilers, collect their typed attempts, and
select a setup ONLY when exactly one organ produced an admissible one. No dynamic "best"
scoring, no priority heuristics.

```text
exactly one setup_correct          -> routed (use it)
zero setup_correct                 -> all_refused (classify downstream)
>= 2 setup_correct, signatures agree-> routed (organs concur)
>= 2 setup_correct, signatures differ-> ambiguous (refuse — never pick)
```

Cross-organ signatures are produced by different functions and never coincide, so in practice
two admitting organs always resolve to ``ambiguous``. The router never solves and never emits
``setup_wrong`` — that is an eval-only outcome; against gold the routed setup must match (the
wrong=0 invariant, asserted by the router tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.comprehension_attempt.classify import classify_cmb, classify_r1, classify_r2, classify_r3
from core.comprehension_attempt.model import ComprehensionAttempt

RouteStatus = Literal["routed", "all_refused", "ambiguous"]


@dataclass(frozen=True, slots=True)
class RouteResult:
    """The outcome of routing one problem across the organs: every attempt, the selected setup
    (or ``None``), and the routing status."""

    attempts: tuple[ComprehensionAttempt, ...]
    selected: ComprehensionAttempt | None
    status: RouteStatus


def cmb_is_authoritative(attempts: tuple[ComprehensionAttempt, ...]) -> bool:
    """True when the R4 combined-rate organ **positively** recognized combined-rate shape — a setup,
    or a substantive ``cmb_*`` refusal (NOT the bare ``not_combined_rate_shaped`` / ``empty``
    step-aside). When it does, R3's broader single-rate read of the SAME text is inadmissible: a more
    specific positive recognition beats a broader partial one ("Anna and Ben paint together; Anna
    paints 3 rooms/hour" must not be answered as a single-rate 12). This is the narrow CMB↔R3
    instance of a future general domain-specificity adjudication; it does NOT mean "CMB always wins"
    (on ``input_shape`` CMB cedes to R3, e.g. a plain single-rate car problem)."""
    cmb = next((a for a in attempts if a.organ == "r4_combined_rate"), None)
    if cmb is None:
        return False
    return cmb.is_setup_correct or (cmb.refusal_reason or "").startswith("cmb_")


def route_setup(text: str, *, case_id: str | None = None) -> RouteResult:
    """Route *text* to the single organ that admits an honest setup, or refuse."""
    attempts = (
        classify_r1(text, case_id=case_id),
        classify_r2(text, case_id=case_id),
        classify_r3(text, case_id=case_id),
        classify_cmb(text, case_id=case_id),
    )
    # CMB-over-R3 domain precedence: a substantive CMB recognition vetoes R3's single-rate over-read.
    vetoed = cmb_is_authoritative(attempts)
    correct = tuple(
        a for a in attempts if a.is_setup_correct and not (vetoed and a.organ == "r3_rate")
    )
    if len(correct) == 1:
        return RouteResult(attempts, correct[0], "routed")
    if not correct:
        return RouteResult(attempts, None, "all_refused")
    if len({a.setup_signature for a in correct}) == 1:
        return RouteResult(attempts, correct[0], "routed")
    return RouteResult(attempts, None, "ambiguous")


__all__ = ["RouteResult", "RouteStatus", "cmb_is_authoritative", "route_setup"]
