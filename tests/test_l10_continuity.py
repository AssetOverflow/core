"""L10 continuity spike — foundation lane (P1, P2a, P2b, P3).

Two kinds of test per predicate:

- a ``*_holds`` test that drives the REAL turn loop over a short soak and asserts
  the predicate passes on genuine evidence, and
- a ``*_bites`` test that feeds the predicate a single mutated record and asserts
  it FAILS — the schema-as-proof obligation (CLAUDE.md): a predicate that cannot
  fail under the violation it nominally catches is decoration, not proof.

The soak-running tests use a small N and a tmp engine-state dir; they are NOT in
the default smoke suite (this is a soak lane, run on demand / nightly).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from evals.l10_continuity.corpus import prompt_at, scripted_corpus
from evals.l10_continuity.predicates import (
    VERSOR_CEILING,
    evaluate_p1_closure,
    evaluate_p2a_determinism,
    evaluate_p2b_reboot_transparency,
    evaluate_p3_bounded_resources,
    evaluate_p4_commit_point,
    evaluate_p4_recovery_determinism,
    evaluate_p5a_recall_precision,
    evaluate_p5b_anchor_stability,
    evaluate_p5c_coherence,
)
from evals.l10_continuity.runner import (
    ProbeRecord,
    SoakResult,
    TurnRecord,
    read_recovered_turn_count,
    run_soak,
)

_SOAK_N = 6  # short horizon: enough to cycle the corpus and cross a reboot


# --------------------------------------------------------------------------- #
# Synthetic-evidence helpers (fast; no pipeline) — used by the *_bites tests.   #
# --------------------------------------------------------------------------- #
def _rec(
    i: int,
    *,
    trace_hash: str | None = None,
    versor_condition: float = 1e-13,
    vault_size: int | None = None,
    booted_segment: int = 0,
    surface: str | None = None,
    dist_to_anchor: float = 5.0,
    turn_movement: float = 1.0,
) -> TurnRecord:
    return TurnRecord(
        turn_index=i,
        input_text=prompt_at(i),
        trace_hash=trace_hash if trace_hash is not None else f"hash-{i}",
        versor_condition=versor_condition,
        surface=surface if surface is not None else f"surface-{i}",
        vault_size=vault_size if vault_size is not None else 2 * (i + 1),
        peak_rss_raw=1_000_000,
        booted_segment=booted_segment,
        dist_to_anchor=dist_to_anchor,
        turn_movement=turn_movement,
    )


def _synthetic(
    records: list[TurnRecord],
    reboot_at: tuple[int, ...] = (),
    probe_records: tuple[ProbeRecord, ...] = (),
) -> SoakResult:
    return SoakResult(
        n_turns=len(records),
        reboot_at=reboot_at,
        records=tuple(records),
        probe_records=probe_records,
    )


# --------------------------------------------------------------------------- #
# Corpus determinism                                                            #
# --------------------------------------------------------------------------- #
def test_corpus_is_deterministic_and_total() -> None:
    assert scripted_corpus(10) == scripted_corpus(10)
    assert prompt_at(0) == prompt_at(6)  # ring of length 6 cycles
    assert scripted_corpus(3) == tuple(prompt_at(i) for i in range(3))
    with pytest.raises(ValueError):
        prompt_at(-1)


# --------------------------------------------------------------------------- #
# P1 — closure                                                                  #
# --------------------------------------------------------------------------- #
def test_p1_closure_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_soak(_SOAK_N, engine_state_dir=tmp_path / "es")
    outcome = evaluate_p1_closure(result)
    assert outcome.passed, outcome.detail
    assert outcome.metrics["worst_versor_condition"] < VERSOR_CEILING


def test_p1_closure_bites_on_breached_versor() -> None:
    bad = _synthetic([_rec(0), _rec(1, versor_condition=1e-3), _rec(2)])
    outcome = evaluate_p1_closure(bad)
    assert not outcome.passed
    assert (1, 1e-3) in outcome.metrics["violations"]


# --------------------------------------------------------------------------- #
# P2a — pipeline determinism (two independent no-reboot runs)                    #
# --------------------------------------------------------------------------- #
def test_p2a_determinism_holds_across_independent_runtimes(tmp_path: Path) -> None:
    run_a = run_soak(_SOAK_N, engine_state_dir=tmp_path / "a")
    run_b = run_soak(_SOAK_N, engine_state_dir=tmp_path / "b")
    outcome = evaluate_p2a_determinism(run_a, run_b)
    assert outcome.passed, outcome.detail
    # And the trace_hashes are genuinely populated (not all empty strings).
    assert all(h for h in run_a.trace_hashes()), "pipeline must produce trace_hashes"


def test_p2a_determinism_bites_on_perturbed_hash() -> None:
    base = [_rec(i) for i in range(4)]
    perturbed = [_rec(i) for i in range(4)]
    perturbed[2] = _rec(2, trace_hash="DIVERGED")
    outcome = evaluate_p2a_determinism(_synthetic(base), _synthetic(perturbed))
    assert not outcome.passed
    assert outcome.metrics["first_divergence"] == 2


# --------------------------------------------------------------------------- #
# P2b — reboot transparency (the diagnostic)                                     #
# --------------------------------------------------------------------------- #
def test_p2b_pre_reboot_invariant_holds_on_real_soak(tmp_path: Path) -> None:
    reboot_turn = 3
    rebooted = run_soak(
        _SOAK_N, engine_state_dir=tmp_path / "r", reboot_at=(reboot_turn,)
    )
    baseline = run_soak(_SOAK_N, engine_state_dir=tmp_path / "base")
    outcome, transparency = evaluate_p2b_reboot_transparency(rebooted, baseline)
    # The structural invariant ALWAYS holds: a reboot cannot change earlier turns.
    assert outcome.passed, outcome.detail
    assert transparency.pre_reboot_identical
    # Diagnostic record: whatever the persistence story, a divergence (if any)
    # must not appear before the reboot turn.
    if transparency.first_divergence is not None:
        assert transparency.first_divergence >= reboot_turn


def test_p2b_reboot_is_transparent(tmp_path: Path) -> None:
    """Resume-as-same-life: a reboot is FULLY transparent.

    With Shape B+ persistence wired (SessionContext.snapshot/restore ->
    engine_state schema v2), the lived field/vault/anchor/graph/referents survive
    a reboot, so [run K -> reboot -> run M] is byte-identical to the
    uninterrupted [run K+M]. This is the load-bearing L10 proof — it FLIPPED from
    the Shape-B 'many lives sharing a checkpoint' gap the moment persistence
    landed. If this regresses to non-transparent, resume-as-same-life broke.
    """
    reboot_turn = 3
    rebooted = run_soak(
        _SOAK_N, engine_state_dir=tmp_path / "r", reboot_at=(reboot_turn,)
    )
    baseline = run_soak(_SOAK_N, engine_state_dir=tmp_path / "base")
    outcome, transparency = evaluate_p2b_reboot_transparency(rebooted, baseline)
    assert outcome.passed, outcome.detail
    assert transparency.post_reboot_transparent, (
        "Reboot is no longer transparent — the lived field/vault stopped "
        "surviving reboot. Resume-as-same-life regressed."
    )
    assert transparency.first_divergence is None


def test_p2b_bites_on_pre_reboot_divergence() -> None:
    reboot_turn = 3
    baseline = [_rec(i) for i in range(6)]
    # A rebooted run that (wrongly) differs BEFORE the reboot point.
    rebooted_records = [_rec(i) for i in range(6)]
    rebooted_records[1] = _rec(1, trace_hash="LEAKED-BACKWARD")
    outcome, transparency = evaluate_p2b_reboot_transparency(
        _synthetic(rebooted_records, reboot_at=(reboot_turn,)),
        _synthetic(baseline),
    )
    assert not outcome.passed
    assert not transparency.pre_reboot_identical
    assert transparency.first_divergence == 1


# --------------------------------------------------------------------------- #
# P3 — bounded resources                                                        #
# --------------------------------------------------------------------------- #
def test_p3_bounded_resources_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_soak(_SOAK_N, engine_state_dir=tmp_path / "es")
    outcome = evaluate_p3_bounded_resources(result)
    assert outcome.passed, outcome.detail
    assert outcome.metrics["vault_monotonic"]


def test_p3_bounded_resources_bites_on_unbounded_vault() -> None:
    records = [_rec(i) for i in range(5)]
    # Simulate an unbounded store: turn 4 holds far more than ceiling*turns.
    records[4] = _rec(4, vault_size=10_000)
    outcome = evaluate_p3_bounded_resources(_synthetic(records))
    assert not outcome.passed
    assert (4, 10_000) in outcome.metrics["vault_breaches"]


# --------------------------------------------------------------------------- #
# P4 — kill-9 crash recovery (ADR-0156 atomicity + WAL commit boundary)         #
# --------------------------------------------------------------------------- #
def test_p4_atomic_write_survives_mid_replace_kill(tmp_path: Path, monkeypatch) -> None:
    """ADR-0156: a kill at the os.replace instant leaves the PRIOR checkpoint
    fully intact and no partial target behind."""
    import engine_state
    from engine_state import EngineStateStore

    store = EngineStateStore(tmp_path)
    store.save_manifest(turn_count=7)  # a good prior checkpoint
    good = (tmp_path / "manifest.json").read_bytes()

    def _boom(*_args, **_kwargs):  # simulate SIGKILL between fsync and rename
        raise OSError("killed mid-replace")

    monkeypatch.setattr(engine_state.os, "replace", _boom)
    with pytest.raises(OSError):
        store.save_manifest(turn_count=8)

    # Prior target intact; no orphan .tmp left in place by the except cleanup.
    assert (tmp_path / "manifest.json").read_bytes() == good
    assert not list(tmp_path.glob(".manifest.json.*.tmp"))


def test_p4_recovered_checkpoint_is_valid_prior(tmp_path: Path) -> None:
    """A reboot after an orphan-leaving crash loads the valid prior turn_count."""
    state_dir = tmp_path / "es"
    k = 4
    run_soak(k, engine_state_dir=state_dir)  # K committed turns
    # Simulate the torn write, then verify the loader recovers turn_count == K.
    from evals.l10_continuity.runner import _inject_orphan_tmp

    _inject_orphan_tmp(state_dir)
    recovered = read_recovered_turn_count(state_dir)
    outcome = evaluate_p4_commit_point(recovered, expected_turn_count=k)
    assert outcome.passed, outcome.detail


def test_p4_recovery_is_deterministic_across_orphan_crash(tmp_path: Path) -> None:
    reboot_turn = 3
    rec_a = run_soak(
        _SOAK_N,
        engine_state_dir=tmp_path / "a",
        reboot_at=(reboot_turn,),
        inject_orphan_tmp_at_reboot=True,
    )
    rec_b = run_soak(
        _SOAK_N,
        engine_state_dir=tmp_path / "b",
        reboot_at=(reboot_turn,),
        inject_orphan_tmp_at_reboot=True,
    )
    outcome = evaluate_p4_recovery_determinism(rec_a, rec_b)
    assert outcome.passed, outcome.detail
    assert outcome.metrics["recovered_tail_len"] == _SOAK_N - reboot_turn


def test_p4_recovery_determinism_bites_on_divergent_tail() -> None:
    """Synthetic bite for the predicate itself: two recoveries whose post-reboot
    tails differ MUST fail (the corrupt-checkpoint test below exercises system
    atomicity, not this predicate's logic)."""
    reboot_turn = 2
    base = [_rec(i, booted_segment=0 if i < reboot_turn else 1) for i in range(5)]
    div = [_rec(i, booted_segment=0 if i < reboot_turn else 1) for i in range(5)]
    div[3] = _rec(3, trace_hash="DIVERGED", booted_segment=1)  # post-reboot index 1
    outcome = evaluate_p4_recovery_determinism(
        _synthetic(base, reboot_at=(reboot_turn,)),
        _synthetic(div, reboot_at=(reboot_turn,)),
    )
    assert not outcome.passed
    assert outcome.metrics["first_divergence"] == 1


def test_p4_commit_point_bites_on_missing_or_partial_checkpoint() -> None:
    # No checkpoint at all → recovered count is None → not the committed count.
    assert not evaluate_p4_commit_point(None, expected_turn_count=5).passed
    # A checkpoint that recorded fewer turns than were committed (non-atomic).
    assert not evaluate_p4_commit_point(3, expected_turn_count=5).passed


def test_p4_recovery_bites_on_corrupt_checkpoint(tmp_path: Path) -> None:
    """In-place corruption (the thing atomicity prevents) MUST fail recovery
    loudly — proving the atomic write is load-bearing, not decoration."""
    from chat.runtime import ChatRuntime
    from core.config import RuntimeConfig

    state_dir = tmp_path / "es"
    run_soak(3, engine_state_dir=state_dir)
    (state_dir / "manifest.json").write_text("{ torn-write garbage <<<", encoding="utf-8")
    with pytest.raises(Exception):
        ChatRuntime(config=RuntimeConfig(), engine_state_path=state_dir)


# --------------------------------------------------------------------------- #
# P5 — semantic quality over the horizon (the T-experience gate)                #
# --------------------------------------------------------------------------- #

# P5a — vault recall precision (cross-reboot)

def test_p5a_recall_precision_holds_on_real_soak(tmp_path: Path) -> None:
    """P5a *holds*: a probe registered pre-reboot is recalled at rank ≤ top_k
    after a reboot, confirming the float32 serialisation round-trip preserves
    the exact-match guarantee in ``_exact_index``."""
    n = _SOAK_N
    reboot_turn = 3
    result = run_soak(
        n,
        engine_state_dir=tmp_path / "es",
        reboot_at=(reboot_turn,),
        probe_at=(1,),
        verify_probes_at=(n - 1,),
    )
    assert result.probe_records, "run_soak must collect at least one ProbeRecord"
    outcome = evaluate_p5a_recall_precision(result.probe_records)
    assert outcome.passed, outcome.detail
    # Every probe must be found within top_k.
    assert all(p.rank is not None and p.rank <= p.top_k for p in result.probe_records)
    # At least one probe crosses the reboot boundary.
    assert any(p.across_reboot for p in result.probe_records)


def test_p5a_recall_precision_bites_on_missing_entry() -> None:
    """P5a *bites*: a ProbeRecord with rank=None (entry not found in vault)
    makes the predicate fail — it is not decoration."""
    missing = ProbeRecord(
        registered_at=1,
        verified_at=5,
        rank=None,
        top_k=5,
        across_reboot=True,
    )
    outcome = evaluate_p5a_recall_precision((missing,))
    assert not outcome.passed
    assert outcome.metrics["failures"]


def test_p5a_recall_precision_bites_on_no_reboot_probe() -> None:
    """P5a *bites*: if all probes are same-segment (no reboot crossed), the
    predicate fails — cross-reboot verification is the primary claim."""
    same_segment = ProbeRecord(
        registered_at=0,
        verified_at=2,
        rank=1,
        top_k=5,
        across_reboot=False,   # no reboot between registration and verification
    )
    outcome = evaluate_p5a_recall_precision((same_segment,))
    assert not outcome.passed
    assert "cross-reboot" in outcome.detail


def test_p5a_recall_precision_bites_on_empty_probe_records() -> None:
    """P5a *bites*: an empty probe_records tuple fails rather than trivially
    passing — the runner must be configured to collect evidence."""
    outcome = evaluate_p5a_recall_precision(())
    assert not outcome.passed


def test_p5b_anchor_stability_holds_on_real_soak(tmp_path: Path) -> None:
    result = run_soak(12, engine_state_dir=tmp_path / "es")
    outcome = evaluate_p5b_anchor_stability(result)
    assert outcome.passed, outcome.detail
    assert outcome.metrics["min_steady_dist_to_anchor"] > 1.0


def test_p5b_bites_on_anchor_collapse() -> None:
    # dist_to_anchor monotonically collapsing to ~0 → field swallowed by anchor.
    records = [
        _rec(i, dist_to_anchor=max(0.0, 5.0 - i), turn_movement=1.0) for i in range(8)
    ]
    outcome = evaluate_p5b_anchor_stability(_synthetic(records))
    assert not outcome.passed
    assert "COLLAPSE" in outcome.detail


def test_p5b_bites_on_field_freeze() -> None:
    # turn_movement ~0 → field stopped moving with content (frozen attractor).
    records = [_rec(i, dist_to_anchor=5.0, turn_movement=0.0) for i in range(8)]
    outcome = evaluate_p5b_anchor_stability(_synthetic(records))
    assert not outcome.passed
    assert "FREEZE" in outcome.detail


def test_p5c_coherence_holds_over_multiple_corpus_cycles(tmp_path: Path) -> None:
    # Span >2 corpus cycles (ring length 6) so the horizon exercises REPETITION,
    # not just 6 unique prompts — a total output collapse across cycles would
    # drop distinct_surfaces toward 1 and trip the predicate.
    from evals.l10_continuity.corpus import base_prompts

    n = len(base_prompts()) * 2 + 2  # 14 turns over a 6-prompt ring
    result = run_soak(n, engine_state_dir=tmp_path / "es")
    outcome = evaluate_p5c_coherence(result)
    assert outcome.passed, outcome.detail
    assert n > len(base_prompts()), "horizon must exceed one cycle to be meaningful"


def test_p5c_bites_on_empty_surfaces() -> None:
    records = [_rec(i, surface="") for i in range(4)]
    outcome = evaluate_p5c_coherence(_synthetic(records))
    assert not outcome.passed


def test_p5c_bites_on_frozen_single_surface() -> None:
    records = [_rec(i, surface="the same thing") for i in range(6)]
    outcome = evaluate_p5c_coherence(_synthetic(records))
    assert not outcome.passed
    assert outcome.metrics["distinct_surfaces"] == 1


# --------------------------------------------------------------------------- #
# Report panel + freeze-gate digest                                             #
# --------------------------------------------------------------------------- #
def test_report_panel_passes_and_records_not_covered(tmp_path: Path) -> None:
    from evals.l10_continuity.report import NOT_COVERED, build_report

    report = build_report(n_turns=8, reboot_turn=3, engine_state_root=tmp_path)
    assert report.all_gates_pass(), [
        (p.name, p.detail) for p in report.predicates if not p.passed
    ]
    # P5a is now a live predicate — NOT_COVERED is empty.
    assert NOT_COVERED == ()
    assert report.not_covered == ()
    # P5a must appear in the predicate panel and pass.
    p5a = next((p for p in report.predicates if p.name == "P5a_recall_precision"), None)
    assert p5a is not None, "P5a_recall_precision must be in the predicate panel"
    assert p5a.passed, p5a.detail
    # The deterministic digest is a 64-hex SHA-256.
    assert len(report.deterministic_digest) == 64
    # The report serializes cleanly (for the on-disk artifact).
    d = report.to_dict()
    assert d["all_gates_pass"] is True
    assert any(p["name"] == "P2b_reboot_transparency" for p in d["predicates"])
    assert any(p["name"] == "P5a_recall_precision" for p in d["predicates"])


def test_report_digest_is_pure_and_bites() -> None:
    from evals.l10_continuity.predicates import evaluate_p1_closure
    from evals.l10_continuity.report import deterministic_digest

    baseline = _synthetic([_rec(i) for i in range(5)])
    outcomes = (evaluate_p1_closure(baseline),)
    a = deterministic_digest(baseline, outcomes)
    b = deterministic_digest(baseline, outcomes)
    assert a == b  # pure
    # A flipped verdict changes the digest (the freeze handle bites).
    flipped = (evaluate_p1_closure(_synthetic([_rec(0, versor_condition=1e-3)])),)
    assert deterministic_digest(baseline, flipped) != a
