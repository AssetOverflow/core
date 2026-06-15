"""W2-R — Arbitrary-interruption recovery harness.

Tests the ``evaluate_p4_arbitrary_interruption`` predicate empirically against
the ADR-0219 generation-dir checkpoint model (W1-A).  Each cut-point has a
``*_holds`` test (real soak) and a ``*_bites`` mutation test (synthetic evidence
that would make the predicate fail).

Cut-points tested:
- ``PARTIAL_GEN``: gen-9997 exists with one file; ``current`` unchanged.
  Loader follows ``current``, ignores the partial dir, loads prior committed gen.
- ``FULL_GEN_BEFORE_SWAP``: gen-9997 exists with all four files; ``current``
  unchanged.  Loader still ignores the unreferenced complete gen dir.
- ``AFTER_SWAP``: no injection (the normal clean-commit control case); verifies
  that the control case passes under the generation-dir model.

Per CLAUDE.md schema-as-proof discipline: a predicate that cannot fail under
the violation it nominally catches is decoration, not proof.
"""

from __future__ import annotations

from pathlib import Path

from evals.l10_continuity.predicates import (
    CutPointEvidence,
    evaluate_p4_arbitrary_interruption,
)
from evals.l10_continuity.runner import (
    InterruptionCutPoint,
    _inject_at_cutpoint,
    _inject_full_gen_dir_before_swap,
    _inject_partial_gen_dir,
    read_recovered_turn_count,
    run_soak,
)


# ---------------------------------------------------------------------------
# Injection function unit tests (no soak needed)
# ---------------------------------------------------------------------------


def test_inject_partial_gen_dir_creates_orphan(tmp_path: Path):
    _inject_partial_gen_dir(tmp_path)
    orphan = tmp_path / "gen-9997"
    assert orphan.is_dir()
    assert (orphan / "manifest.json").exists()
    # Must NOT contain all four files (it's PARTIAL).
    assert not (orphan / "session_state.json").exists()


def test_inject_full_gen_dir_before_swap_creates_all_four_files(tmp_path: Path):
    _inject_full_gen_dir_before_swap(tmp_path)
    orphan = tmp_path / "gen-9997"
    assert orphan.is_dir()
    for fname in ("recognizers.jsonl", "discovery_candidates.jsonl", "session_state.json", "manifest.json"):
        assert (orphan / fname).exists(), f"expected {fname} in full-gen orphan"


def test_inject_at_cutpoint_after_swap_is_noop(tmp_path: Path):
    _inject_at_cutpoint(tmp_path, InterruptionCutPoint.AFTER_SWAP)
    # AFTER_SWAP injects nothing — directory should be empty (no orphan gen).
    gen_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith("gen-")]
    assert len(gen_dirs) == 0


# ---------------------------------------------------------------------------
# Holds tests — real soaks exercise each cut-point
# ---------------------------------------------------------------------------


def test_p4_arbitrary_interruption_partial_gen_holds(tmp_path: Path):
    """PARTIAL_GEN: orphan partial gen dir is ignored, prior gen loaded, recoveries converge."""
    cp = InterruptionCutPoint.PARTIAL_GEN
    reboot_turn = 3
    n_turns = 6

    # Commit-probe: verify loader reads prior committed gen (not the orphan).
    probe_dir = tmp_path / "cp_probe"
    run_soak(reboot_turn, engine_state_dir=probe_dir)
    _inject_at_cutpoint(probe_dir, cp)
    recovered_tc = read_recovered_turn_count(probe_dir)
    assert recovered_tc == reboot_turn, (
        f"PARTIAL_GEN: expected committed turn_count={reboot_turn}, got {recovered_tc}"
    )

    # Recovery soaks: two independent soaks with PARTIAL_GEN injection must converge.
    rec_a = run_soak(n_turns, engine_state_dir=tmp_path / "a", reboot_at=(reboot_turn,), cutpoint_at_reboot=cp)
    rec_b = run_soak(n_turns, engine_state_dir=tmp_path / "b", reboot_at=(reboot_turn,), cutpoint_at_reboot=cp)
    tail_a = tuple(r.trace_hash for r in rec_a.post_reboot_records())
    tail_b = tuple(r.trace_hash for r in rec_b.post_reboot_records())
    assert tail_a == tail_b, "PARTIAL_GEN: two recovery soaks diverged"

    # Full predicate.
    evidence = (
        CutPointEvidence(
            cut_point=cp.value,
            recovered_turn_count=recovered_tc,
            expected_turn_count=reboot_turn,
            tail_hashes_a=tail_a,
            tail_hashes_b=tail_b,
            all_versor_conditions=rec_a.versor_conditions() + rec_b.versor_conditions(),
        ),
    )
    outcome = evaluate_p4_arbitrary_interruption(evidence)
    assert outcome.passed, outcome.detail


def test_p4_arbitrary_interruption_full_gen_before_swap_holds(tmp_path: Path):
    """FULL_GEN_BEFORE_SWAP: complete but unreferenced gen dir is ignored."""
    cp = InterruptionCutPoint.FULL_GEN_BEFORE_SWAP
    reboot_turn = 3
    n_turns = 6

    probe_dir = tmp_path / "cp_probe"
    run_soak(reboot_turn, engine_state_dir=probe_dir)
    _inject_at_cutpoint(probe_dir, cp)
    recovered_tc = read_recovered_turn_count(probe_dir)
    assert recovered_tc == reboot_turn, (
        f"FULL_BEFORE_SWAP: expected committed turn_count={reboot_turn}, got {recovered_tc}"
    )

    rec_a = run_soak(n_turns, engine_state_dir=tmp_path / "a", reboot_at=(reboot_turn,), cutpoint_at_reboot=cp)
    rec_b = run_soak(n_turns, engine_state_dir=tmp_path / "b", reboot_at=(reboot_turn,), cutpoint_at_reboot=cp)
    tail_a = tuple(r.trace_hash for r in rec_a.post_reboot_records())
    tail_b = tuple(r.trace_hash for r in rec_b.post_reboot_records())
    assert tail_a == tail_b, "FULL_BEFORE_SWAP: two recovery soaks diverged"

    evidence = (
        CutPointEvidence(
            cut_point=cp.value,
            recovered_turn_count=recovered_tc,
            expected_turn_count=reboot_turn,
            tail_hashes_a=tail_a,
            tail_hashes_b=tail_b,
            all_versor_conditions=rec_a.versor_conditions() + rec_b.versor_conditions(),
        ),
    )
    outcome = evaluate_p4_arbitrary_interruption(evidence)
    assert outcome.passed, outcome.detail


# ---------------------------------------------------------------------------
# Bites tests — synthetic evidence that trips each gate bullet
# ---------------------------------------------------------------------------


def test_p4_arbitrary_interruption_bites_on_wrong_recovered_turn_count():
    """Wrong turn_count: orphan gen loaded instead of committed gen → predicate fails."""
    evidence = (
        CutPointEvidence(
            cut_point=InterruptionCutPoint.PARTIAL_GEN.value,
            recovered_turn_count=0,    # wrong: orphan's manifest was read (0 turns)
            expected_turn_count=3,
            tail_hashes_a=("abc",),
            tail_hashes_b=("abc",),
            all_versor_conditions=(1e-13,),
        ),
    )
    outcome = evaluate_p4_arbitrary_interruption(evidence)
    assert not outcome.passed, "predicate must fail when recovered_turn_count != expected"


def test_p4_arbitrary_interruption_bites_on_diverging_recovery_tails():
    """Diverging tails: two independent recoveries produce different trace_hashes → fails."""
    evidence = (
        CutPointEvidence(
            cut_point=InterruptionCutPoint.FULL_GEN_BEFORE_SWAP.value,
            recovered_turn_count=3,
            expected_turn_count=3,
            tail_hashes_a=("hash_a1", "hash_a2"),
            tail_hashes_b=("hash_b1", "hash_b2"),  # different → divergence
            all_versor_conditions=(1e-13, 1e-13),
        ),
    )
    outcome = evaluate_p4_arbitrary_interruption(evidence)
    assert not outcome.passed, "predicate must fail when recovery tails diverge"


def test_p4_arbitrary_interruption_bites_on_versor_condition_violation():
    """Closure violation: versor_condition >= 1e-6 in a recovery soak → fails."""
    evidence = (
        CutPointEvidence(
            cut_point=InterruptionCutPoint.PARTIAL_GEN.value,
            recovered_turn_count=3,
            expected_turn_count=3,
            tail_hashes_a=("abc",),
            tail_hashes_b=("abc",),
            all_versor_conditions=(1e-6,),  # at the ceiling → violation
        ),
    )
    outcome = evaluate_p4_arbitrary_interruption(evidence)
    assert not outcome.passed, "predicate must fail when versor_condition >= 1e-6"


def test_p4_arbitrary_interruption_bites_on_empty_tails():
    """Empty recovery tails: no post-reboot evidence → fails."""
    evidence = (
        CutPointEvidence(
            cut_point=InterruptionCutPoint.PARTIAL_GEN.value,
            recovered_turn_count=3,
            expected_turn_count=3,
            tail_hashes_a=(),   # empty: no post-reboot records
            tail_hashes_b=(),
            all_versor_conditions=(),
        ),
    )
    outcome = evaluate_p4_arbitrary_interruption(evidence)
    assert not outcome.passed, "predicate must fail with empty recovery tails"
