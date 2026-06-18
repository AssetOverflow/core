"""Gate A2j — possession giveaway target-residual (R4 sibling, not goal-residual).

Experience Flywheel Sprint 7 selected this family from decomposition of
composition-validation **cv-0021** (train_sample **0035**): anchor possession,
progress giveaways to named recipients (including ``N more than`` a prior
giveaway), question asks how many *more* to give away to reach a stated
remainder.

    total_to_give = possession − target_remainder
    more_needed = total_to_give − Σ giveaways (with comparative increment)

Distinct from Gate A2e ``goal_residual``:

- anchor is possession language (``has``), not goal intent (``wants``/``needs``);
- target remainder is stated in the question (``left with only N``), not a goal
  quantity in the anchor clause;
- comparative ``more than <prior recipient>`` licenses an extra subtract step.

Promotion requires:

- question binds ``more``, ``give``, and ``left``;
- exactly one possession quantity in the anchor clause;
- at least one giveaway progress clause with licensed giveaway cues;
- hazard refusal (goal language, comparative questions, competing possessions).

Deterministic; sealed module (no ``chat/`` import).
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation, Quantity, Step
from generate.derivation.state.bind import leading_subject_token
from generate.derivation.target import _question_clause
from generate.derivation.verify import Resolution, select_self_verified
from generate.math_roundtrip import _tokens

_AND_SPLIT_RE: Final[re.Pattern[str]] = re.compile(r",\s*and\s+", re.IGNORECASE)

_GOAL_INTENT: Final[frozenset[str]] = frozenset(
    {"want", "wants", "wanted", "need", "needs", "hoping", "hopes", "plans", "aims", "goal"}
)
_COMPARATIVE_TARGET_CUES: Final[frozenset[str]] = frozenset({"than"})
_GIVEAWAY_CUES: Final[frozenset[str]] = frozenset({"got", "gave", "gives", "give"})
_POSSESSION_CUES: Final[frozenset[str]] = frozenset({"has", "have", "had"})


def _asks_giveaway_residual(question_clause: str) -> bool:
    tokens = _tokens(question_clause)
    if _COMPARATIVE_TARGET_CUES & tokens:
        return False
    return "more" in tokens and "give" in tokens and "left" in tokens


def _target_remainder(question_clause: str) -> Quantity | None:
    """The ``only N`` remainder stated in the question."""
    quantities = [q for q in extract_quantities(question_clause) if not q.unit]
    if len(quantities) != 1:
        return None
    return quantities[0]


def _giveaway_subclauses(clause: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in _AND_SPLIT_RE.split(clause) if part.strip())


def _competing_possession_hazard(subclause: str) -> bool:
    tokens = _tokens(subclause)
    if not (_POSSESSION_CUES & tokens):
        return False
    return not (_GIVEAWAY_CUES & tokens)


def build_giveaway_target_residual(problem_text: str) -> GroundedDerivation | None:
    """Construct ``possession − remainder − Σgiveaways``, or ``None``."""
    question_clause = _question_clause(problem_text)
    if not _asks_giveaway_residual(question_clause):
        return None

    remainder = _target_remainder(question_clause)
    if remainder is None:
        return None

    clauses = segment_clauses(problem_text)
    body_clauses = [c for c in clauses if c != question_clause]
    quantity_clauses = [c for c in body_clauses if extract_quantities(c)]
    if len(quantity_clauses) < 2:
        return None

    anchor_clause = quantity_clauses[0]
    anchor_tokens = _tokens(anchor_clause)
    if not (_POSSESSION_CUES & anchor_tokens):
        return None
    if _GOAL_INTENT & anchor_tokens:
        return None

    anchor_quantities = extract_quantities(anchor_clause)
    if len(anchor_quantities) != 1:
        return None
    possession = anchor_quantities[0]

    steps: list[Step] = [
        Step(
            op="subtract",
            operand=Quantity(
                value=remainder.value,
                unit=possession.unit,
                source_token=remainder.source_token,
            ),
            cue="left",
        )
    ]

    first_giveaway: Quantity | None = None
    giveaway_steps = 0

    for clause in quantity_clauses[1:]:
        for subclause in _giveaway_subclauses(clause):
            if _competing_possession_hazard(subclause):
                return None
            clause_tokens = _tokens(subclause)
            if not (_GIVEAWAY_CUES & clause_tokens):
                continue
            cue = next(c for c in ("got", "gave", "gives", "give") if c in clause_tokens)

            progress = [
                q
                for q in extract_quantities(subclause)
                if (not q.unit) or q.unit == possession.unit
            ]
            if not progress:
                return None

            if "more" in clause_tokens and "than" in clause_tokens:
                if len(progress) != 1:
                    return None
                if first_giveaway is None:
                    return None
                increment = progress[0]
                base = first_giveaway
                steps.append(
                    Step(
                        op="subtract",
                        operand=Quantity(
                            value=base.value,
                            unit=possession.unit,
                            source_token=base.source_token,
                        ),
                        cue=leading_subject_token(subclause) or cue,
                    )
                )
                steps.append(
                    Step(
                        op="subtract",
                        operand=Quantity(
                            value=increment.value,
                            unit=possession.unit,
                            source_token=increment.source_token,
                        ),
                        cue="more",
                    )
                )
                giveaway_steps += 2
                continue

            for q in progress:
                operand = Quantity(
                    value=q.value, unit=possession.unit, source_token=q.source_token
                )
                steps.append(Step(op="subtract", operand=operand, cue=cue))
                giveaway_steps += 1
                if first_giveaway is None:
                    first_giveaway = operand

    if giveaway_steps < 2:
        return None
    return GroundedDerivation(start=possession, steps=tuple(steps))


def compose_giveaway_target_residual(problem_text: str) -> Resolution | None:
    """Gate the typed giveaway-residual chain through self-verification."""
    derivation = build_giveaway_target_residual(problem_text)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())


def resolve_promotable_giveaway_target_residual(problem_text: str) -> Resolution | None:
    """Serving promotion bridge (Gate A2j)."""
    return compose_giveaway_target_residual(problem_text)