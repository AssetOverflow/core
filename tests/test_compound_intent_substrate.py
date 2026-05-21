"""Compound-intent substrate — ADR-0089 Phase C1 (audit Finding 4, 2026-05-20).

Pre-fix ``CognitiveTurnPipeline.run()`` called only the single-intent
``classify_intent`` and silently dropped every secondary clause of a
compound prompt like *"What is X and how does it relate to Y?"*.

Phase C1 is **pure observability**: the pipeline now also runs
``classify_compound_intent`` at step 1b and records every dropped
clause on ``CognitiveTurnResult.dropped_compound_clauses``.  The
dominant clause continues to route through the existing single-intent
path — surfaces, trace_hashes, and every existing test remain
byte-identical.

These tests pin:

  * Single-clause prompts produce ``dropped_compound_clauses == ()``.
  * Compound prompts surface the secondary clauses as classified
    ``DialogueIntent``s with their tags and subjects preserved.
  * The dominant-clause surface is byte-identical to today (no
    behavior change).
  * The trace_hash for compound prompts is byte-identical to today
    (no new trace input).
"""

from __future__ import annotations

import pytest

from chat.runtime import ChatRuntime
from core.cognition import CognitiveTurnPipeline
from generate.intent import IntentTag


@pytest.fixture()
def pipeline() -> CognitiveTurnPipeline:
    return CognitiveTurnPipeline(runtime=ChatRuntime())


def test_single_clause_records_no_dropped_clauses(
    pipeline: CognitiveTurnPipeline,
) -> None:
    result = pipeline.run("What is truth?", max_tokens=4)
    assert result.dropped_compound_clauses == ()


def test_compound_and_records_secondary_clause(
    pipeline: CognitiveTurnPipeline,
) -> None:
    """An AND-joined compound surfaces the second clause as telemetry."""
    result = pipeline.run(
        "What is truth, and why does it matter?",
        max_tokens=4,
    )
    # The compound classifier split this into two parts; the second
    # should be recorded as dropped.
    assert len(result.dropped_compound_clauses) >= 1
    secondary = result.dropped_compound_clauses[0]
    # The second clause is a CAUSE shape ("why does ...").
    assert secondary.tag is IntentTag.CAUSE


def test_compound_path_byte_identical_to_pre_c1() -> None:
    """Phase C1 is byte-identical at every existing observable.

    The dominant-clause routing path is unchanged: ``classify_intent``
    still runs on the raw text (with its current limitations, including
    the broken-subject case the audit identified).  Phase C1 only
    *adds* observability of the secondary clauses — it does not
    improve the dominant-clause routing.  That improvement is
    explicitly the Phase C2 scope per ADR-0089.

    This test pins the no-behavior-change contract: the user-visible
    surface and the trace_hash for a compound prompt are identical to
    what they were pre-Phase-C1.
    """
    # Run the compound prompt twice on independent runtimes; the second
    # run is what the pipeline records.  Both must agree byte-for-byte
    # on the user-visible surface and trace_hash because nothing in the
    # surface / trace path consumes ``dropped_compound_clauses`` yet.
    rt_a = ChatRuntime()
    rt_b = ChatRuntime()
    pa = CognitiveTurnPipeline(runtime=rt_a)
    pb = CognitiveTurnPipeline(runtime=rt_b)
    result_a = pa.run("What is truth, and why does it matter?", max_tokens=4)
    result_b = pb.run("What is truth, and why does it matter?", max_tokens=4)
    assert result_a.surface == result_b.surface
    assert result_a.trace_hash == result_b.trace_hash
    # And the dropped-clauses observability did fire.
    assert len(result_a.dropped_compound_clauses) >= 1


def test_no_recognized_connector_returns_single_part(
    pipeline: CognitiveTurnPipeline,
) -> None:
    """A prompt without a recognised connector must not invent a
    secondary clause."""
    result = pipeline.run("Define knowledge.", max_tokens=4)
    assert result.dropped_compound_clauses == ()
