"""ADR-0207 §5 step 2 / R4 — goal-residual reading (single-referent).

The first **residual-to-target** comprehension reading, distinct from GB-3b.1
accumulation (:mod:`generate.derivation.accumulate`):

- accumulation reads a **possession** that changes — ``start ± changes`` (``Sam has
  14 apples. He buys 9 more.`` -> ``14 + 9``);
- this reads a **goal** and the **progress** toward it — ``goal − Σprogress``
  (``Michael wants to lose 10 pounds. He lost 3, then 4. How much more to meet his
  goal?`` -> ``10 − 3 − 4``).

**Critical wrong=0 distinction — the coincidental-correctness trap.** Goal-residual is
*not* possession-accumulation. For a **loss** goal the two arithmetics coincide
(``10 − 3 − 4`` == ``10 − (3+4)``), so a naive "make accumulation fire" change would
pass ``cv-0005`` for the wrong reason — reading the goal ``10`` as a possession start.
For a **gain/save** goal they **diverge**: ``wants to save 20, saved 5, saved 6`` ->
residual ``20 − 5 − 6 = 9``, whereas possession-accumulation gives ``20 + 5 + 6 = 31``.
This production fires **only** on goal-language and **always subtracts** progress
(progress reduces the residual regardless of its world-polarity), so it reads the goal,
never the possession. The gain-goal divergence is the wrong=0 firewall test.

Lexeme-level (ADR-0165): goal-intent and residual-question cues are closed token sets,
not sentence-shape grammar. The constructed chain runs through the unchanged
self-verification gate (grounding ∧ unit ∧ completeness ∧ uniqueness) — refuse-
preferring; this only proposes a structurally-licensed candidate.

Sealed (no ``chat/`` import); deterministic.
"""

from __future__ import annotations

from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.state.bind import continues_anchor_referent, leading_subject_token
from generate.derivation.state.change import classify_change_polarity, select_change_cue
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

# Goal-intent lexemes: the anchor quantity is a *target*, not a possession. Closed set.
_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "hoping", "hopes", "plans", "aims", "goal"}
)
# Residual-question lexemes: the question asks the remaining distance to the goal.
_RESIDUAL_CUES: Final[frozenset[str]] = frozenset({"more", "left", "remaining"})
_GOAL_REACH: Final[frozenset[str]] = frozenset({"meet", "reach", "hit", "achieve"})


def _asks_residual(question_clause: str) -> bool:
    """The question asks the remaining distance to a goal (lexeme-level)."""
    q = _tokens(question_clause)
    return bool(_RESIDUAL_CUES & q) or ("goal" in q and bool(_GOAL_REACH & q))


def build_goal_residual(problem_text: str) -> GroundedDerivation | None:
    """Construct the ungated goal-residual chain ``goal − Σprogress``, or ``None``.

    Fires only when: (a) the question asks a residual-to-goal; (b) the first
    quantity-clause carries a goal-intent lexeme and establishes exactly one goal
    quantity; (c) every later quantity-clause stays on the same referent and carries a
    licensed change cue (its quantities are *progress*). Progress is **subtracted**
    (it reduces the residual) regardless of the change's world-polarity — this is what
    makes the reading goal-residual, not possession-accumulation.
    """
    if not _asks_residual(_question_clause(problem_text)):
        return None

    clauses = segment_clauses(problem_text)
    quantity_clauses = [c for c in clauses if extract_quantities(c)]
    if len(quantity_clauses) < 2:
        return None

    anchor_clause, *progress_clauses = quantity_clauses
    if not (_GOAL_INTENT & _tokens(anchor_clause)):
        return None  # the anchor must be goal-language, not a possession
    anchor_quantities = extract_quantities(anchor_clause)
    if len(anchor_quantities) != 1:
        return None  # exactly one goal quantity
    goal = anchor_quantities[0]
    anchor_subject = leading_subject_token(anchor_clause)

    steps: list[Step] = []
    for clause in progress_clauses:
        if not continues_anchor_referent(clause, anchor_subject):
            return None  # new named actor -> referent hazard -> refuse
        polarity = classify_change_polarity(clause)
        if polarity is None:
            return None  # progress must carry a licensed change cue
        cue = select_change_cue(clause, polarity)
        progress = [q for q in extract_quantities(clause) if (not q.unit) or q.unit == goal.unit]
        if not progress:
            return None  # no same-unit progress quantity -> refuse
        for q in progress:
            operand = Quantity(value=q.value, unit=goal.unit, source_token=q.source_token)
            steps.append(Step(op="subtract", operand=operand, cue=cue))

    if not steps:
        return None
    return GroundedDerivation(start=goal, steps=tuple(steps))


def compose_goal_residual(problem_text: str) -> Resolution | None:
    """R4 goal-residual composer. Refuse-preferring: gates the chain through the
    unchanged self-verification gate (grounding ∧ unit ∧ completeness ∧ uniqueness)."""
    derivation = build_goal_residual(problem_text)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())
