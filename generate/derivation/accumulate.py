"""ADR-0178 GB-3b.1 — single-referent accumulation chaining.

The first cross-clause *comprehension* reading: one actor's quantity changes over
successive clauses (``Sam has 14 apples. He buys 9 more.`` -> ``14 + 9``). It is
the safe specialisation of the cross-clause sum that GB-3a's referent guard
correctly refuses wholesale (the ``Alice has 6 … Tom has 2 …`` hazard): we chain
across clauses **only** when (a) the later clause stays on the **same referent**
and (b) it carries a **licensed change cue** whose polarity is unambiguous.
Otherwise we refuse — the guard is generalised, never weakened.

Reading:

1. **Anchor** — clause 1 must establish exactly one quantity ``(actor, N, unit)``.
2. **Change steps** — each later quantity-bearing clause applies ``+ M`` (gain) or
   ``- M`` (loss) to the running total, where ``M`` is the clause's single grounded
   quantity, taken **in the anchor's unit** (``9 more`` = 9 more *apples*; the unit
   is inherited from the running total, which is what accumulation means).
3. **Gate** — the constructed chain runs through the unchanged self-verification
   gate (grounding ∧ unit ∧ completeness ∧ uniqueness). The gate keeps
   wrong=0; this only proposes a structurally-licensed candidate.

ADR-0184 S1 extracted reusable referent/change-cue helpers into
``generate.derivation.state``. S2 routes accumulation through a minimal semantic
ledger before replaying to ``GroundedDerivation``. This module remains the public
accumulation composer surface; behavior is intentionally unchanged.

Sealed (no ``chat/`` import); deterministic; refuse-preferring.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation
from generate.derivation.state.ledger import build_accumulation_ledger
from generate.derivation.state.replay import replay_accumulation_ledger
from generate.derivation.verify import Resolution, select_self_verified


def _quantity_clauses(problem_text: str) -> list[str]:
    """Sentence-level clauses that carry extracted quantities."""

    return [c for c in segment_clauses(problem_text) if extract_quantities(c)]


def _build_accumulation(
    problem_text: str, *, drop_isolated_foreign: bool
) -> GroundedDerivation | None:
    """Construct the single-referent accumulation chain (ungated).

    ``drop_isolated_foreign`` (ADR-0182): when a change clause carries more than
    one quantity, drop those with a **non-empty unit foreign to the anchor's unit**
    (a candidate distractor — ``studies for 3 hours`` among ``pencils``) and proceed
    if exactly one same-unit/unitless change remains. With the flag off this is the
    strict GB-3b.1 reading (a multi-quantity change clause refuses), so
    :func:`compose_accumulation` is byte-identical to its pre-ADR-0182 behavior.
    The distractor-skip reading is **never committed alone** — it only ever enters
    the pool to force a disagreement refusal (see :mod:`generate.derivation.pool`).
    """

    ledger = build_accumulation_ledger(
        _quantity_clauses(problem_text),
        drop_isolated_foreign=drop_isolated_foreign,
    )
    if ledger is None:
        return None
    return replay_accumulation_ledger(ledger)


# ADR-0182 anchor-skip: sub-clause split on conjunctions. A single sentence can pack
# a state and its change ("Tom has 8 tickets and buys 4 more tickets") — the
# sentence-level segmenter (used everywhere; not changed) keeps them together. This
# finer split is *local* to the ungated candidate generator, so it cannot move
# GB-1/GB-2/serving/practice (which never call it). Lexeme-level (ADR-0165): it names
# coordinating conjunctions, it does not parse grammar.
_CONJUNCTION_SPLIT: Final[re.Pattern[str]] = re.compile(r",?\s+(?:and then|and|then)\s+")


def _sub_clauses(problem_text: str) -> list[str]:
    """Sentence clauses, each further split on coordinating conjunctions."""

    parts: list[str] = []
    for clause in segment_clauses(problem_text):
        parts.extend(p.strip() for p in _CONJUNCTION_SPLIT.split(clause) if p.strip())
    return parts


def _build_accumulation_anchor_skip(problem_text: str) -> GroundedDerivation | None:
    """ADR-0182 — accumulation over sub-clauses, skipping a leading all-foreign block.

    Reads ``A train travels 60 mph for 2 hours. Tom has 8 tickets and buys 4 more
    tickets.`` by skipping the (anchor-position) train block — its quantities cannot
    seed an anchor (≠1 quantity) — and anchoring on the first single-quantity
    sub-clause (``Tom has 8 tickets``), then chaining its conjunction-mate change
    (``buys 4 more`` → +4). The skipped block's quantities go unused; the pool's
    isolated-foreign exemption then classifies the reading ``exempt`` (commit-
    ineligible), so it can only force a disagreement refusal, never commit. Ungated.
    """

    sub_clauses = [(s, extract_quantities(s)) for s in _sub_clauses(problem_text)]
    quantity_subs = [(s, qs) for s, qs in sub_clauses if qs]
    if len(quantity_subs) < 2:
        return None

    # Anchor = first single-quantity sub-clause; leading non-anchorable (≠1
    # quantity) sub-clauses are skipped (candidate distractor blocks).
    anchor_idx = next((i for i, (_, qs) in enumerate(quantity_subs) if len(qs) == 1), None)
    if anchor_idx is None:
        return None

    selected = [sub for sub, _ in quantity_subs[anchor_idx:]]
    ledger = build_accumulation_ledger(selected, drop_isolated_foreign=False)
    if ledger is None:
        return None
    return replay_accumulation_ledger(ledger)


def compose_accumulation(problem_text: str) -> Resolution | None:
    """GB-3b.1 composer — single-referent gain/loss accumulation. Refuse-preferring.

    The strict (commit) reading: it gates the no-distractor-skip derivation through
    the unchanged self-verification gate. Behavior is byte-identical to pre-ADR-0182.
    """

    derivation = _build_accumulation(problem_text, drop_isolated_foreign=False)
    if derivation is None:
        return None
    return select_self_verified([derivation], problem_text, target_units=())


def accumulation_candidates(problem_text: str) -> tuple[GroundedDerivation, ...]:
    """ADR-0182 — the ungated accumulation readings for cross-composer pooling.

    Three readings: the strict GB-3b.1 reading, the distractor-skip reading (drops an
    isolated-foreign quantity in a multi-quantity change clause — 0014), and the
    anchor-skip reading (skips a leading all-foreign block + reads a conjunction-mate
    intra-sentence change — 0016). Ungated: the pool classifies each (``complete``
    commits, ``exempt`` refuses-only) and the disagreement rule does the wrong=0 work.
    Deterministic; de-dup is the pool's job.
    """

    candidates: list[GroundedDerivation] = []
    for drop in (False, True):
        derivation = _build_accumulation(problem_text, drop_isolated_foreign=drop)
        if derivation is not None:
            candidates.append(derivation)
    anchor_skip = _build_accumulation_anchor_skip(problem_text)
    if anchor_skip is not None:
        candidates.append(anchor_skip)
    return tuple(candidates)
