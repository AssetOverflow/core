"""Project-root conftest — quarantine registry for known-failing tests.

The QUARANTINE set lists test IDs that are pre-existing failures
predating the substrate-liveness audit work (verified via bisect
against c1a1b7a, the commit immediately before the first W-* PR
of 2026-05-24). The CI gate at .github/workflows/full-pytest.yml
runs ``pytest -m "not quarantine"`` so these failures do not block
PRs, but the suite is a ratchet: a quarantined test removed from
this set must pass on its own merits.

See docs/test-debt-quarantine.md for cluster diagnoses, removal
policy, and the per-test rationale.

To remove a test from quarantine:
  1. Land a PR that makes the test pass.
  2. Delete its entry from QUARANTINE in the same PR.
  3. The full-pytest CI gate will now require it to keep passing.

Adding a test to QUARANTINE is strongly discouraged. If a new
failure surfaces, the right default is to fix it in the PR that
caused it — not to quarantine. The set should only shrink.
"""

from __future__ import annotations

import pytest

import engine_state


_USES_DEFAULT_ENGINE_STATE_MARKER = "uses_default_engine_state"


@pytest.fixture(autouse=True)
def _isolate_engine_state_default(request, tmp_path_factory, monkeypatch):
    """Isolate the default engine-state checkpoint dir per test.

    A bare ``ChatRuntime()`` (no ``engine_state_path``) falls back to
    ``engine_state._DEFAULT_DIR`` — the shared repo ``engine_state/`` directory.
    Tests must not share that mutable dir: one test's checkpoint (recognizers,
    candidates, the stamped engine-identity, and — under resume mode — the lived
    session_state) leaks into another test's fresh-state assumptions (and, since
    L11, raises spurious identity-continuity-break warnings when a later test
    boots under a different identity over the same dir). Point the default at a
    fresh per-test temp dir. Tests passing an explicit ``engine_state_path`` are
    unaffected; within one test, repeated ``ChatRuntime()`` share this dir.

    Two redirections, both pointed at the same per-test dir:

    1. ``engine_state._DEFAULT_DIR`` is monkeypatched directly. It is bound at
       import (``engine_state/__init__.py``), so an env var alone would NOT
       redirect an already-imported in-process runtime.
    2. ``CORE_ENGINE_STATE_DIR`` is set in the environment so subprocess / CLI
       tests that re-import ``engine_state`` in a child process inherit the same
       isolation. A child that sets its own ``CORE_ENGINE_STATE_DIR`` (e.g.
       ``tests/test_l10_always_on_daemon.py::test_real_sigterm_stops_the_daemon_cleanly``)
       still overrides this and wins.

    A test that intentionally exercises the real process-default dir (default-dir
    semantics, CLI fallback, legacy-flat migration) can opt out with
    ``@pytest.mark.uses_default_engine_state``; it then sees neither redirection.
    """
    if request.node.get_closest_marker(_USES_DEFAULT_ENGINE_STATE_MARKER):
        return
    isolated = tmp_path_factory.mktemp("engine_state_default")
    monkeypatch.setattr(engine_state, "_DEFAULT_DIR", isolated)
    monkeypatch.setenv("CORE_ENGINE_STATE_DIR", str(isolated))


QUARANTINE: frozenset[str] = frozenset()


# ---------------------------------------------------------------------------
# Slow-test registry — empirical test-infrastructure metadata, NOT test
# semantics, so it lives here beside QUARANTINE in one auditable place rather
# than as @pytest.mark.slow decorators spread across ~24 files.
#
# A handful of soak / bench / replay / proof / eval-matrix tests dominate the
# suite wall-clock: ~50 tests account for essentially the entire serial runtime
# (~73 min), while the other ~10k tests are near-instant.  Classifying them lets
# a developer run a fast lane locally.  Classification adds the ``slow`` marker
# ONLY — it never skips — so ``-m slow`` SELECTS these tests.  Choose a lane:
#
#   fast lane:  pytest -m "not quarantine and not slow"     (make test-fast)
#   slow lane:  pytest -m "slow and not quarantine"         (make test-slow)
#   full lane:  pytest -m "not quarantine"                  (make test-full; CI)
#
# CI is unchanged: smoke.yml and full-pytest.yml run ``-m "not quarantine"``,
# which still includes slow tests.  See docs/testing-lanes.md.
# ---------------------------------------------------------------------------

# Whole-file: the cost is carried by a module/session-scoped fixture, so marking
# individual tests is insufficient — skipping one just shifts the fixture cost to
# the next test that requests it.  The whole file is classified slow.
SLOW_FILES: frozenset[str] = frozenset({
    "tests/test_inner_loop_phase2.py",               # module fixture run_lane(): 9 cases x 4 conditions x 5-rerun determinism (~975s)
    "tests/test_cognition_eval_register_matrix.py",  # module fixtures: full register x invariant eval matrix
    "tests/test_articulation_bench.py",              # module fixture: articulation bench corpus
    "tests/test_register_invariant_grounding.py",    # module fixtures: per-register runtime grounding
    "tests/test_public_showcase.py",                 # module fixture: full showcase execution
    "tests/test_conversation_demo.py",               # module fixture: multi-turn demo run
    "tests/test_edge_budget_gate.py",                # module fixture: per-turn checkpoint cost soak
    "tests/test_phase5_corpus.py",                   # module fixtures: replay-determinism corpus
    "tests/test_realizer_guard_holdout.py",          # module fixture: holdout-cluster run
    "tests/test_teaching_loop_bench.py",             # module fixture: teaching-loop determinism bench
})

# Exact nodeids: mixed files where only specific tests are soak/bench scale.
# Listed individually so the file's fast (predicate / unit) coverage stays in the
# fast lane.  No scoped fixture carries the cost in these files, so per-test
# classification does not shift cost to a sibling.
SLOW_TESTS: frozenset[str] = frozenset({
    # test_l10_continuity.py — real-soak predicates among 28 mostly-fast tests
    "tests/test_l10_continuity.py::test_p1_closure_holds_on_real_soak",
    "tests/test_l10_continuity.py::test_p2a_determinism_holds_across_independent_runtimes",
    "tests/test_l10_continuity.py::test_p2b_pre_reboot_invariant_holds_on_real_soak",
    "tests/test_l10_continuity.py::test_p2b_reboot_is_transparent",
    "tests/test_l10_continuity.py::test_p4_recovery_is_deterministic_across_orphan_crash",
    "tests/test_l10_continuity.py::test_p5c_coherence_holds_over_multiple_corpus_cycles",
    "tests/test_l10_continuity.py::test_report_panel_passes_and_records_not_covered",
    # test_l10_arbitrary_interruption.py — partial/full generation interruption soak
    "tests/test_l10_arbitrary_interruption.py::test_p4_arbitrary_interruption_full_gen_before_swap_holds",
    "tests/test_l10_arbitrary_interruption.py::test_p4_arbitrary_interruption_partial_gen_holds",
    # test_register_tour_demo.py — per-register tour runs (5 fast structural tests remain)
    "tests/test_register_tour_demo.py::test_tour_grounding_sources_identical_across_registers",
    "tests/test_register_tour_demo.py::test_tour_returns_structured_report",
    "tests/test_register_tour_demo.py::test_tour_terse_substantively_differs_from_neutral",
    "tests/test_register_tour_demo.py::test_tour_trace_hashes_identical_across_registers",
    # test_register_firing_diagnostic.py — multi-register marker-engagement report
    "tests/test_register_firing_diagnostic.py::test_build_report_records_marker_engagement_for_register_subset",
    # test_operator_calibration_replay.py — replay/calibration proof tests
    "tests/test_operator_calibration_replay.py::TestCalibrationRejectsInvariantRegression::test_versor_closure_must_not_regress",
    "tests/test_operator_calibration_replay.py::TestCalibrationReportHasBeforeAfterMetrics::test_calibrate_returns_result",
    # test_pack_measurements_phase2.py — falsifiability lane (ALSO run by CI smoke via
    # -m "not quarantine", which does not exclude slow; classifying it is safe)
    "tests/test_pack_measurements_phase2.py::TestRefusalCalibrationPackRunner::test_grounding_gate_is_pack_invariant",
    "tests/test_pack_measurements_phase2.py::TestRefusalCalibrationPackRunner::test_no_fabrication_under_any_pack",
    "tests/test_pack_measurements_phase2.py::TestRefusalCalibrationPackRunner::test_report_schema_is_stable",
    # test_thread_context.py — eviction-over-capacity soak (19 fast tests remain)
    "tests/test_thread_context.py::test_runtime_default_capacity_evicts_old_turns",
    # test_correction_telemetry.py — cross-run determinism (6 fast tests remain)
    "tests/test_correction_telemetry.py::test_correction_event_is_deterministic_across_runs",
    # test_cold_start_grounding_lane.py — distribution lane (15 fast tests remain)
    "tests/test_cold_start_grounding_lane.py::TestPassThresholds::test_distributions_match_expected",
    # test_engine_state_session_persistence.py — reboot/restore soak (4 fast tests remain)
    "tests/test_engine_state_session_persistence.py::test_chat_runtime_restores_lived_state_across_reboot",
    "tests/test_engine_state_session_persistence.py::test_no_load_state_runtime_starts_fresh",
    # test_cli_demo.py — combined-run demo subprocess (16 lighter demo tests remain)
    "tests/test_cli_demo.py::TestDemoPreambles::test_all_preamble_explains_combined_run",
    # test_identity_continuity_proof.py — byte-identical resumed-life proof
    "tests/test_identity_continuity_proof.py::test_resumed_life_is_byte_identical_and_same_identity",
    # test_warmed_session_lane.py — pipeline-override gate invariant
    "tests/test_warmed_session_lane.py::TestPipelineOverrideGateInvariants::test_no_placeholder_rate_is_one",
})


def _is_slow(nodeid: str) -> bool:
    """True if ``nodeid`` is classified slow by the SLOW_FILES / SLOW_TESTS registry.

    ``nodeid`` is expected pre-normalized to forward slashes (the caller does this
    once).  Splitting on ``"::"`` yields exactly the file path, so the whole-file
    check is an O(1) set lookup with no substring-prefix edge cases (e.g.
    ``..._phase2.py`` can never match ``..._phase2_extra.py``).  Exact-nodeid
    match handles mixed files.
    """
    if nodeid in SLOW_TESTS:
        return True
    file_path = nodeid.split("::", 1)[0]
    return file_path in SLOW_FILES


def pytest_collection_modifyitems(config, items):
    """Stamp the ``quarantine`` and ``slow`` markers from the conftest registries.

    - QUARANTINE nodeids get ``quarantine`` (CI runs ``-m "not quarantine"``).
    - SLOW_FILES / SLOW_TESTS get ``slow`` — classification ONLY, never skipped
      here, so ``-m slow`` SELECTS them.  Lanes are chosen explicitly:
        fast: pytest -m "not quarantine and not slow"
        slow: pytest -m "slow and not quarantine"
        full: pytest -m "not quarantine"
    """
    _ = config  # pluggy hook signature requires the name `config`; not used here
    quarantine_marker = pytest.mark.quarantine
    slow_marker = pytest.mark.slow
    for item in items:
        # Normalize once: pytest nodeids are forward-slash, but normalize
        # defensively so both registries match on Windows backslash nodeids too.
        nodeid = item.nodeid.replace("\\", "/")
        if nodeid in QUARANTINE:
            item.add_marker(quarantine_marker)
        if _is_slow(nodeid):
            item.add_marker(slow_marker)
