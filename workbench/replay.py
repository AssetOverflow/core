"""Sealed single-turn replay over the turn journal (Wave R3).

``GET /replay/{turn_id}`` re-executes a journaled prompt in a sealed fresh
runtime and compares the resulting envelope leaf-by-leaf against the
recorded :class:`~workbench.journal.TurnJournalEntry`.

The claim demonstrated is exactly the architectural one: same prompt, same
genesis substrate -> bit-identical envelope.  The original turn ran in its
own fresh ``ChatRuntime()`` that may have loaded an engine-state checkpoint
present at the time; the journal does not record whether one existed, so
``origin_state`` is reported as ``"unrecorded"`` and a divergence means
nondeterminism OR origin-state influence — never claimed to be one or the
other.

This module owns classification and comparison only.  Execution is
injected by the caller (``workbench.api`` passes its own chat-turn
executor over a sealed runtime), which keeps the comparison pure and the
no-fabricated-equivalence obligation testable: if the executor raises,
no comparison object exists.
"""

from __future__ import annotations

import time
from dataclasses import fields, replace
from typing import Callable

from workbench.journal import TurnJournalEntry
from workbench.schemas import (
    ChatTurnResult,
    TurnReplayComparison,
    TurnReplayDivergence,
)

# Every TurnJournalEntry field must appear in exactly one of these sets —
# enforced by tests so a future journal field forces an explicit
# classification decision instead of silently defaulting.
CRITICAL_FIELDS = frozenset(
    {
        "turn_id",
        "prompt",
        "surface",
        "articulation_surface",
        "walk_surface",
        "trace_hash",
        "grounding_source",
        "epistemic_state",
        "normative_clearance",
        "verdicts",
        "refusal_emitted",
        "hedge_injected",
        "proposal_candidates",
        "leeway_evidence",
        "pipeline_record",
        "field_evidence",
        "checkpoint_emitted",
        "trace_integrity",
    }
)
# Wall-clock by nature, or derived over wall-clock bytes (journal_digest
# hashes the timestamp): expected to differ on every replay and never
# evidence against equivalence.
INFORMATIONAL_FIELDS = frozenset({"timestamp", "turn_cost_ms", "journal_digest"})


def replay_turn(
    entry: TurnJournalEntry,
    *,
    execute: Callable[[str], ChatTurnResult],
) -> TurnReplayComparison:
    """Re-execute ``entry.prompt`` via ``execute`` and compare envelopes.

    ``execute`` must run the prompt through the same envelope-assembly path
    that produced the recorded entry, over a sealed runtime.  This function
    never fabricates a comparison: if ``execute`` raises, the exception
    propagates and no ``TurnReplayComparison`` exists.
    """
    started = time.perf_counter()
    result = execute(entry.prompt)
    elapsed_ms = max(0, int(round((time.perf_counter() - started) * 1000)))
    result = replace(result, turn_cost_ms=elapsed_ms, turn_id=entry.turn_id)
    replayed = TurnJournalEntry.from_chat_turn(result, turn_id=entry.turn_id)

    divergences: list[TurnReplayDivergence] = []
    for spec in fields(TurnJournalEntry):
        original_value = getattr(entry, spec.name)
        replay_value = getattr(replayed, spec.name)
        if original_value == replay_value:
            continue
        divergences.append(
            TurnReplayDivergence(
                path=spec.name,
                original=original_value,
                replay=replay_value,
                severity=(
                    "critical" if spec.name in CRITICAL_FIELDS else "informational"
                ),
            )
        )

    return TurnReplayComparison(
        turn_id=entry.turn_id,
        comparison_basis="sealed_fresh_runtime_single_turn",
        origin_state="unrecorded",
        original_trace_hash=entry.trace_hash,
        replay_trace_hash=replayed.trace_hash,
        equivalent=not any(d.severity == "critical" for d in divergences),
        replay_turn_cost_ms=elapsed_ms,
        divergences=divergences,
        leeway_evidence=entry.leeway_evidence,
    )
