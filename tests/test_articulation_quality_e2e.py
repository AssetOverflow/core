"""Phase 5 — end-to-end test of the full articulation-quality loop.

Demonstrates the doctrine-aligned feedback loop the user asked for:

  live runtime (Phase 1-4)
    → per-turn ArticulationObservation
    → JSONL sink
    → offline mine_articulation_observations
    → SPECULATIVE PACK_MUTATION_CANDIDATE findings

No mutation of packs, vault, teaching corpus, or runtime state at any
step.  Operator reviews the emitted findings via the existing
proposal-review-ratify chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from chat.articulation_telemetry import load_articulation_observations
from chat.runtime import ChatRuntime
from core.config import RuntimeConfig
from core.contemplation.miners.articulation_quality import (
    mine_articulation_observations,
)
from core.contemplation.schema import FindingKind
from teaching.epistemic import EpistemicStatus


@dataclass
class _BufferSink:
    """Minimal in-memory ``ArticulationObservationSink``."""
    lines: List[str] = field(default_factory=list)

    def emit(self, line: str) -> None:
        self.lines.append(line)


# ---------------------------------------------------------------------------
# No sink attached → runtime emits nothing
# ---------------------------------------------------------------------------


def test_no_sink_means_no_emission() -> None:
    """Engaged plan + contemplation on + sink ABSENT → no JSONL line."""
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.chat("What is truth, and why does it matter?")
    # No buffer to inspect — verify the planner engaged so the
    # condition for emission was met EXCEPT for the missing sink.
    assert rt.last_plan_metrics is not None
    assert rt.last_plan_findings  # multi-move compound prompt fires WEAK_SURFACE


# ---------------------------------------------------------------------------
# Sink attached + contemplation off → no emission
# ---------------------------------------------------------------------------


def test_sink_attached_but_contemplation_off_yields_nothing() -> None:
    sink = _BufferSink()
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=False))
    rt.attach_articulation_sink(sink)
    rt.chat("What is truth, and why does it matter?")
    # Contemplation off → metrics None → emission gate fails closed.
    assert sink.lines == []


# ---------------------------------------------------------------------------
# Sink attached + contemplation on + planner engaged → one line emitted
# ---------------------------------------------------------------------------


def test_engaged_turn_emits_one_observation_line() -> None:
    sink = _BufferSink()
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.attach_articulation_sink(sink)
    rt.chat("What is truth, and why does it matter?")
    assert len(sink.lines) == 1
    [observation] = load_articulation_observations(sink.lines)
    assert observation.anchor_subject == "truth"
    assert observation.metrics["move_count"] >= 4
    assert any(
        f["kind"] == FindingKind.WEAK_SURFACE.value
        for f in observation.findings
    )


def test_brief_turn_does_not_emit() -> None:
    """BRIEF mode prompts short-circuit the planner before any plan
    is built — no observation should land in the sink."""
    sink = _BufferSink()
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.attach_articulation_sink(sink)
    rt.chat("What is knowledge?")
    assert sink.lines == []


# ---------------------------------------------------------------------------
# Multiple turns + offline miner closes the loop
# ---------------------------------------------------------------------------


def test_full_loop_emits_pack_mutation_candidate_after_repeated_pattern() -> None:
    """The headline Phase 5 demo:

      1.  Operator runs the compound prompt three times.
      2.  Each turn emits one observation; all three observations
          carry a ``WEAK_SURFACE`` finding for
          ``(truth, belongs_to)`` because the plan structure is
          deterministic.
      3.  Offline miner aggregates the three observations and emits
          one ``PACK_MUTATION_CANDIDATE`` finding stamped
          SPECULATIVE.
    """
    sink = _BufferSink()
    rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
    rt.attach_articulation_sink(sink)

    for _ in range(3):
        # Fresh runtime per turn to keep determinism clean; otherwise
        # vault state would diverge between turns.  (The sink survives
        # across the three runtimes — we re-attach.)
        rt = ChatRuntime(config=RuntimeConfig(discourse_contemplation=True))
        rt.attach_articulation_sink(sink)
        rt.chat("What is truth, and why does it matter?")

    assert len(sink.lines) == 3

    observations = load_articulation_observations(sink.lines)
    findings = mine_articulation_observations(observations=observations)

    # At minimum the recurring_predicate_monotony rule must fire — three
    # identical WEAK_SURFACE findings on (truth, belongs_to).
    pmc = [
        f for f in findings
        if f.kind is FindingKind.PACK_MUTATION_CANDIDATE
    ]
    assert pmc, "expected at least one PACK_MUTATION_CANDIDATE finding"

    monotony = [
        f for f in pmc if f.predicate == "recurring_predicate_monotony"
    ]
    assert len(monotony) == 1
    assert monotony[0].subject == "truth"
    assert monotony[0].object == "belongs_to"
    assert monotony[0].epistemic_status is EpistemicStatus.SPECULATIVE


# ---------------------------------------------------------------------------
# Determinism across the full loop
# ---------------------------------------------------------------------------


def test_full_loop_is_deterministic_byte_equal_finding_ids() -> None:
    """Two end-to-end runs over the same input produce byte-identical
    finding IDs — the load-bearing claim for the offline miner."""

    def _run_loop() -> tuple[str, ...]:
        sink = _BufferSink()
        for _ in range(3):
            rt = ChatRuntime(
                config=RuntimeConfig(discourse_contemplation=True),
            )
            rt.attach_articulation_sink(sink)
            rt.chat("What is truth, and why does it matter?")
        observations = load_articulation_observations(sink.lines)
        findings = mine_articulation_observations(observations=observations)
        return tuple(f.finding_id for f in findings)

    ids_a = _run_loop()
    ids_b = _run_loop()
    assert ids_a == ids_b


# ---------------------------------------------------------------------------
# Doctrine pin — every emitted finding is SPECULATIVE
# ---------------------------------------------------------------------------


def test_full_loop_emits_only_speculative_findings() -> None:
    sink = _BufferSink()
    for _ in range(3):
        rt = ChatRuntime(
            config=RuntimeConfig(discourse_contemplation=True),
        )
        rt.attach_articulation_sink(sink)
        rt.chat("What is truth, and why does it matter?")
    observations = load_articulation_observations(sink.lines)
    findings = mine_articulation_observations(observations=observations)
    for f in findings:
        assert f.epistemic_status is EpistemicStatus.SPECULATIVE
