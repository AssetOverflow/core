"""ADR-0184 §7 S4 — the semantic candidate-source boundary.

The single module through which semantic-ledger worlds become derivation candidates.
World enumeration (which readings exist for a problem) lives here; conversion to the
arithmetic proof object goes only through :func:`replay_accumulation_ledger` (S2's
sole bridge).  The output is a tuple of inert ``GroundedDerivation`` values — this
boundary holds no commit authority: acceptance, classification, and refusal happen
only in the unchanged ``generate.derivation.verify`` / ``generate.derivation.pool``.

Boundary laws (each pinned by tests in
``tests/test_adr_0184_s4_semantic_candidate_source.py``):

* nothing under ``generate/derivation/state/`` imports verify/pool or names a commit
  surface (structural scan);
* a world that cannot be built, or a replay that refuses, contributes nothing —
  fail-closed, never a synthesized candidate;
* enumeration order is deterministic (strict, distractor-skip, anchor-skip) and
  byte-identical to the pre-S4 ``accumulation_candidates`` enumeration, duplicates
  included (de-dup remains the pool's job).

Sealed (no ``chat/`` import); deterministic; refuse-preferring.
"""

from __future__ import annotations

import re
from typing import Final

from generate.derivation.clauses import segment_clauses
from generate.derivation.extract import extract_quantities
from generate.derivation.model import GroundedDerivation
from generate.derivation.state.ledger import build_accumulation_ledger
from generate.derivation.state.model import SemanticLedger
from generate.derivation.state.replay import replay_accumulation_ledger


def _quantity_clauses(problem_text: str) -> list[str]:
    """Sentence-level clauses that carry extracted quantities (the ledger anchor +
    change-clause sequence)."""
    return [c for c in segment_clauses(problem_text) if extract_quantities(c)]


def accumulation_world(
    problem_text: str, *, drop_isolated_foreign: bool
) -> SemanticLedger | None:
    """The single-referent accumulation reading of ``problem_text`` as a ledger.

    ``drop_isolated_foreign`` (ADR-0182): when a change clause carries more than
    one quantity, drop those with a **non-empty unit foreign to the anchor's unit**
    (a candidate distractor — ``studies for 3 hours`` among ``pencils``) and proceed
    if exactly one same-unit/unitless change remains.  With the flag off this is the
    strict GB-3b.1 reading (a multi-quantity change clause refuses).  The
    distractor-skip reading is **never committed alone** — it only ever enters the
    pool to force a disagreement refusal (see :mod:`generate.derivation.pool`).
    """
    return build_accumulation_ledger(
        _quantity_clauses(problem_text), drop_isolated_foreign=drop_isolated_foreign
    )


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


def anchor_skip_world(problem_text: str) -> SemanticLedger | None:
    """ADR-0182 — the accumulation-over-sub-clauses reading, skipping a leading
    all-foreign block, as a ledger.

    Reads ``A train travels 60 mph for 2 hours. Tom has 8 tickets and buys 4 more
    tickets.`` by skipping the (anchor-position) train block — its quantities cannot
    seed an anchor (≠1 quantity) — and anchoring on the first single-quantity
    sub-clause (``Tom has 8 tickets``), then chaining its conjunction-mate change
    (``buys 4 more`` → +4). The skipped block's quantities go unused; the pool's
    isolated-foreign exemption then classifies the reading ``exempt`` (commit-
    ineligible), so it can only force a disagreement refusal, never commit.

    ``drop_isolated_foreign`` stays off here — the anchor-skip reading drops a whole
    leading block, not an in-clause foreign quantity.
    """
    sub_clauses = [(s, extract_quantities(s)) for s in _sub_clauses(problem_text)]
    quantity_subs = [(s, qs) for s, qs in sub_clauses if qs]
    if len(quantity_subs) < 2:
        return None

    # Anchor = first single-quantity sub-clause; leading non-anchorable (≠1
    # quantity) sub-clauses are skipped (candidate distractor blocks). The anchor and
    # its trailing change sub-clauses are then read by the same semantic ledger as the
    # sentence-level path: same referent guard, same one-change-per-clause rule, same
    # polarity gate.
    anchor_idx = next((i for i, (_, qs) in enumerate(quantity_subs) if len(qs) == 1), None)
    if anchor_idx is None:
        return None
    selected = [sub for sub, _ in quantity_subs[anchor_idx:]]
    return build_accumulation_ledger(selected, drop_isolated_foreign=False)


def accumulation_ledger_worlds(problem_text: str) -> tuple[SemanticLedger, ...]:
    """Every accumulation-backed semantic world for ``problem_text``, in the fixed
    enumeration order: strict, distractor-skip, anchor-skip.  A world that cannot be
    built is simply absent — fail-closed."""
    worlds: list[SemanticLedger] = []
    for drop in (False, True):
        world = accumulation_world(problem_text, drop_isolated_foreign=drop)
        if world is not None:
            worlds.append(world)
    anchor_skip = anchor_skip_world(problem_text)
    if anchor_skip is not None:
        worlds.append(anchor_skip)
    return tuple(worlds)


def semantic_state_candidates(problem_text: str) -> tuple[GroundedDerivation, ...]:
    """ADR-0184 §7 S4 — the semantic candidate source for cross-composer pooling.

    Replays every semantic world through the S2 bridge and returns the resulting
    ungated candidates.  Byte-identical to the pre-S4 ``accumulation_candidates``
    enumeration: the pool classifies each (``complete`` commits, ``exempt``
    refuses-only) and the disagreement rule does the wrong=0 work.  A refused replay
    contributes nothing (fail-closed).  Deterministic; de-dup is the pool's job.
    """
    candidates: list[GroundedDerivation] = []
    for world in accumulation_ledger_worlds(problem_text):
        derivation = replay_accumulation_ledger(world)
        if derivation is not None:
            candidates.append(derivation)
    return tuple(candidates)
