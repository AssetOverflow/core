"""ADR-0178 GB-3b.1 — single-referent accumulation chaining.

The first cross-clause *comprehension* reading: one actor's quantity changes over
successive clauses (``Sam has 14 apples. He buys 9 more.`` -> ``14 + 9``). It is
the safe specialisation of the cross-clause sum that GB-3a's referent guard
correctly refuses wholesale (the ``Alice has 6 … Tom has 2 …`` hazard): we chain
across clauses **only** when (a) the later clause stays on the **same referent**
and (b) it carries a **licensed change cue** whose polarity is unambiguous.
Otherwise we refuse — the guard is generalised, never weakened.

ADR-0184 S1 extracted the reusable referent and change-cue helpers into
``generate.derivation.state``; S2 routed both accumulation readings through the
semantic ledger (SET/GAIN/LOSS over one entity/unit key) with replay back to
``GroundedDerivation``; §7 S4 moved world enumeration into the candidate-source
boundary, :mod:`generate.derivation.state.source`.  This module remains the public
accumulation composer surface — :func:`compose_accumulation` (the gated strict
reading) and :func:`accumulation_candidates` (a thin compatibility wrapper over
:func:`generate.derivation.state.source.semantic_state_candidates`, per ADR-0184
§10).  Behavior is intentionally unchanged, and every candidate still faces the
unchanged verifier/pool.

Sealed (no ``chat/`` import); deterministic; refuse-preferring.
"""

from __future__ import annotations

from generate.derivation.model import GroundedDerivation
from generate.derivation.state.replay import replay_accumulation_ledger
from generate.derivation.state.source import accumulation_world, semantic_state_candidates
from generate.derivation.verify import Resolution, select_self_verified


def _build_accumulation(
    problem_text: str, *, drop_isolated_foreign: bool
) -> GroundedDerivation | None:
    """Construct the single-referent accumulation chain (ungated) — build the
    semantic world at the S4 boundary, replay through the S2 bridge."""
    ledger = accumulation_world(problem_text, drop_isolated_foreign=drop_isolated_foreign)
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

    Compatibility wrapper (ADR-0184 §10): the enumeration lives at the semantic
    candidate-source boundary and is byte-identical to the pre-S4 behavior — three
    readings (strict, distractor-skip, anchor-skip), ungated, deterministic order,
    de-dup left to the pool.
    """
    return semantic_state_candidates(problem_text)
