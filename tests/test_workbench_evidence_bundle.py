"""D3 shareable evidence bundle — non-vacuous determinism guards.

The bundle is the citable claim; the ``bundle_digest`` is its content address.
These tests fail under the violations that would make it a lie: a digest that
drifts on identical content, a digest that leaks journal position / wall-clock,
or a digest that does NOT move when the cognitive evidence changes.
"""

from __future__ import annotations

from workbench.evidence_bundle import build_evidence_bundle
from workbench.journal import TurnJournalEntry


def _entry(**overrides: object) -> TurnJournalEntry:
    base: dict[str, object] = dict(
        turn_id=1,
        timestamp="2026-06-13T00:00:00Z",
        trace_hash="th-abc",
        prompt="why",
        surface="because",
        articulation_surface=None,
        walk_surface=None,
        grounding_source="pack",
        epistemic_state="verified",
        normative_clearance="cleared",
        verdicts={},
        refusal_emitted=False,
        hedge_injected=False,
        proposal_candidates=[],
        turn_cost_ms=12,
        checkpoint_emitted=False,
        journal_digest="jd-1",
    )
    base.update(overrides)
    return TurnJournalEntry(**base)  # type: ignore[arg-type]


class TestBundleDigest:
    def test_same_content_is_reproducible(self) -> None:
        assert (
            build_evidence_bundle(_entry()).bundle_digest
            == build_evidence_bundle(_entry()).bundle_digest
        )

    def test_journal_position_and_wall_clock_are_excluded(self) -> None:
        # Same cognitive evidence, different journal position / wall-clock ->
        # SAME digest. This is the "reproducibility as a deliverable" claim.
        base = build_evidence_bundle(_entry())
        moved = build_evidence_bundle(
            _entry(
                turn_id=99,
                journal_digest="jd-DIFFERENT",
                timestamp="2099-01-01T00:00:00Z",
                turn_cost_ms=9999,
            )
        )
        assert base.bundle_digest == moved.bundle_digest
        # ...but the provenance fields ARE carried on the bundle.
        assert moved.turn_id == 99
        assert moved.journal_digest == "jd-DIFFERENT"

    def test_surface_change_flips_digest(self) -> None:
        assert (
            build_evidence_bundle(_entry()).bundle_digest
            != build_evidence_bundle(_entry(surface="something else")).bundle_digest
        )

    def test_trace_hash_change_flips_digest(self) -> None:
        assert (
            build_evidence_bundle(_entry()).bundle_digest
            != build_evidence_bundle(_entry(trace_hash="th-OTHER")).bundle_digest
        )

    def test_grounding_change_flips_digest(self) -> None:
        assert (
            build_evidence_bundle(_entry()).bundle_digest
            != build_evidence_bundle(_entry(grounding_source="oov")).bundle_digest
        )


class TestBundleShape:
    def test_carries_deterministic_evidence_and_reproducer(self) -> None:
        bundle = build_evidence_bundle(_entry())
        assert bundle.schema_version == "evidence_bundle_v1"
        assert bundle.generated_from == "turn_journal"
        assert bundle.trace_hash == "th-abc"
        assert bundle.bundle_digest.startswith("sha256:")
        assert "core replay turn 1" in bundle.replay_reproducer
        assert "th-abc" in bundle.replay_reproducer

    def test_missing_phase_c_evidence_is_honest_not_fabricated(self) -> None:
        bundle = build_evidence_bundle(_entry())
        # No pipeline/field/leeway persisted on this bare entry -> carried as null.
        assert bundle.pipeline_record is None
        assert bundle.field_evidence is None
        assert bundle.leeway_evidence is None
