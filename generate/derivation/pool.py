"""ADR-0182 — cross-composer disagreement pooling.

The distractor-quantity confusers (``confuser-v1-0014`` → 300, ``0016`` → 3840)
misfire because a blunt product-of-all is the *unique* self-verifying reading: the
completeness clause forces the distractor into it, and no rival reading exists to
trigger the wrong=0 disagreement rule. The microscope showed no tight cue/gate rule
separates these from the legitimate cross-unit products (``for`` licenses both the
0014 distractor and the correct ``train-0021`` product) — that is the deferred
cue-precision problem (ADR-0177).

This module sidesteps cue precision: it pools the **ungated candidate readings of
every composer** (accumulation, in-clause multiplicative, target-guided chain) for
one problem and resolves them together. A reading is classified
(:func:`generate.derivation.verify.classify_derivation`) as ``complete``
(commit-eligible) or ``exempt`` (commit-INELIGIBLE — verified but for an
isolated-foreign *distractor* quantity it leaves unused). The rule:

* candidates disagree (more than one distinct answer across the pool) → **refuse**
  (the wrong=0 disagreement rule does the work);
* a single distinct answer → commit **only if** a ``complete`` candidate produced it
  (an ``exempt``-only answer never commits — full completeness is still required to
  resolve, so ADR-0175's multi-step-incomplete defence is untouched).

For a distractor problem this gives the product (``complete``) a competing additive
reading (``exempt``) to disagree with → refusal; for a genuine product (0021/0003)
there is no rival reading, so it still commits. Deterministic; sealed (serving is
never invoked here).
"""

from __future__ import annotations

from generate.derivation.goal_residual import build_goal_residual
from generate.derivation.model import GroundedDerivation
from generate.derivation.multistep import candidate_chains
from generate.derivation.search import multiplicative_candidates
from generate.derivation.state.source import semantic_state_candidates
from generate.derivation.target import asks_prior_state
from generate.derivation.verify import Resolution, classify_derivation


def pooled_candidates(problem_text: str) -> list[GroundedDerivation]:
    """Every composer's ungated candidate readings, de-duplicated. Deterministic
    order (semantic-state accumulation worlds via the ADR-0184 §7-S4 candidate-source
    boundary, then multiplicative, then chain)."""
    seen: set[tuple[object, ...]] = set()
    pooled: list[GroundedDerivation] = []
    _goal_residual = build_goal_residual(problem_text)
    for derivation in (
        *semantic_state_candidates(problem_text),
        *multiplicative_candidates(problem_text),
        *candidate_chains(problem_text),
        *((_goal_residual,) if _goal_residual is not None else ()),
    ):
        key = (
            round(derivation.answer, 9),
            derivation.start.source_token,
            tuple((step.op, step.operand.source_token) for step in derivation.steps),
        )
        if key in seen:
            continue
        seen.add(key)
        pooled.append(derivation)
    return pooled


def resolve_pooled(problem_text: str) -> Resolution | None:
    """Resolve a problem by pooling every composer's readings. Refuse-preferring.

    Refuses on no verifying candidate, on disagreement among the pool, or when the
    sole answer is produced only by commit-ineligible (``exempt``) readings.

    ADR-0182 question-scope guard: a question asking for a *prior* state ("how much
    did Lisa have **before** lunch?") asks for a temporal point the forward composers
    do not compute — they derive the final/net state. Until a question-time reader
    exists, that is a refusal, never a guess at the wrong point.
    """
    if asks_prior_state(problem_text):
        return None

    classified = [
        (kind, derivation)
        for derivation in pooled_candidates(problem_text)
        if (kind := classify_derivation(derivation, problem_text)) is not None
    ]
    if not classified:
        return None

    distinct = {round(derivation.answer, 9) for _, derivation in classified}
    if len(distinct) != 1:
        return None  # disagreement -> refuse (wrong=0)

    committable = [d for kind, d in classified if kind == "complete"]
    if not committable:
        return None  # exempt-only -> refuse (a commit requires full completeness)

    chosen = committable[0]
    return Resolution(
        answer=chosen.answer,
        answer_unit=chosen.answer_unit,
        derivation=chosen,
    )
