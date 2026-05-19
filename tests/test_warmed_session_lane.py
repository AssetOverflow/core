"""Contract tests for the ``warmed_session_consistency`` eval lane.

This lane catches a bug class the design-review-2026-05-19 named:

  > pipeline overrode a runtime surface with a placeholder realizer
  > surface because realized_plan.surface was non-empty, even though it
  > contained '...'.  The runtime audit log still held a different
  > surface.

These tests pin:

  - Case-set integrity (turn sequence + expected grounding per turn).
  - Lane discovery (framework can find and load the lane).
  - The runner produces every required metric (no_placeholder_rate,
    telemetry_consistency_rate, warm_grounding_stability,
    grounding_match_rate).
  - The runner uses ONE warmed ``ChatRuntime`` per case (warmed-session
    invariant — the asymmetric counterpart to cold_start_grounding's
    fresh-runtime invariant).

NOTE: Pass-threshold assertions (``no_placeholder_rate == 1.0`` etc.)
are deliberately NOT pinned here yet — they will land green only after
the Phase B1 pipeline-override usefulness gate is in place.  The
contract.md documents the targets; this lane's role at present is to
PROVIDE the regression substrate for that fix.
"""

from __future__ import annotations

from pathlib import Path

from evals.framework import (
    discover_lanes,
    get_lane,
    load_cases,
    load_lane_runner,
    run_lane,
)


LANE_NAME = "warmed_session_consistency"
_EVAL_ROOT = Path(__file__).resolve().parent.parent / "evals" / LANE_NAME
_PUBLIC_CASES = _EVAL_ROOT / "public" / "v1" / "cases.jsonl"


class TestCaseSetIntegrity:
    def test_public_cases_file_exists(self) -> None:
        assert _PUBLIC_CASES.exists()

    def test_every_case_has_turn_sequence(self) -> None:
        cases = load_cases(_PUBLIC_CASES)
        assert len(cases) >= 4
        for case in cases:
            assert "id" in case and isinstance(case["id"], str)
            assert "turns" in case and isinstance(case["turns"], list)
            assert len(case["turns"]) >= 1, case
            for turn in case["turns"]:
                assert "prompt" in turn and isinstance(turn["prompt"], str)
                assert "expected_grounding_source" in turn

    def test_at_least_one_case_has_replay_pattern(self) -> None:
        """At least one case must replay the same prompt across turns
        so the ``warm_grounding_stability`` metric has something to
        measure."""
        cases = load_cases(_PUBLIC_CASES)
        for case in cases:
            prompts = [t["prompt"] for t in case["turns"]]
            if len(prompts) > 1 and len(set(prompts)) < len(prompts):
                return  # found one
        raise AssertionError("no case carries a repeated-prompt sequence")


class TestLaneDiscovery:
    def test_lane_is_discoverable(self) -> None:
        names = {lane.name for lane in discover_lanes()}
        assert LANE_NAME in names

    def test_lane_runner_loads(self) -> None:
        lane = get_lane(LANE_NAME)
        runner = load_lane_runner(lane)
        assert hasattr(runner, "run_lane")


class TestPipelineOverrideGateInvariants:
    """Phase B1 hard floors — these were red before the
    pipeline-override usefulness gate landed and must never regress.

    - no_placeholder_rate         floor 1.00 (no ... / <pending> / <prior>)
    - telemetry_consistency_rate  floor 1.00 (turn_log surface == pipeline result)
    """

    def test_no_placeholder_rate_is_one(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        rate = result.metrics["no_placeholder_rate"]
        assert rate == 1.0, (
            f"no_placeholder_rate regressed below 1.0: {rate} — "
            f"the pipeline override usefulness gate has been weakened. "
            f"Surfaces containing ... / <pending> / <prior> are a "
            f"doctrine violation."
        )

    def test_telemetry_consistency_rate_is_one(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        rate = result.metrics["telemetry_consistency_rate"]
        assert rate == 1.0, (
            f"telemetry_consistency_rate regressed below 1.0: {rate} — "
            f"the pipeline is mutating surface AFTER runtime telemetry "
            f"is emitted.  TurnEvent.surface no longer equals "
            f"pipeline.run().surface, which breaks audit/replay trust."
        )


class TestRunnerMetrics:
    """The runner must emit every metric the contract.md names, even
    when the values are red.  Missing-metric drift would make the
    Phase B1 regression catch silent."""

    REQUIRED_METRICS = (
        "cases",
        "total_turns",
        "no_placeholder_rate",
        "telemetry_consistency_rate",
        "warm_grounding_stability",
        "grounding_match_rate",
    )

    def test_all_required_metrics_present(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        for name in self.REQUIRED_METRICS:
            assert name in result.metrics, (
                f"missing metric {name!r}; got keys: {sorted(result.metrics)}"
            )

    def test_per_turn_details_carry_all_signals(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        assert result.case_details
        # Every per-turn dict must carry the four binary signals.
        for case in result.case_details:
            for turn in case["turns"]:
                for key in (
                    "no_placeholder", "telemetry_match",
                    "grounding_match", "surface",
                ):
                    assert key in turn, (case["case_id"], turn["turn_index"], key)


class TestWarmedRuntimeInvariant:
    """The runner must construct ONE ChatRuntime+pipeline per case and
    play the full turn sequence through it — the inverse of
    cold_start_grounding's fresh-per-case invariant.

    Static check: the runner's _run_case helper instantiates ChatRuntime
    inside the function (one per case), NOT at module scope (which
    would share state across cases — wrong invariant) and NOT inside
    the per-turn loop (which would defeat the warmed-session purpose).
    """

    def test_runner_constructs_runtime_per_case_not_per_turn(self) -> None:
        src = (_EVAL_ROOT / "runner.py").read_text(encoding="utf-8")
        # Module-level ChatRuntime instances would share state across
        # cases — forbidden.
        for line in src.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("_RUNTIME ", "RUNTIME ", "_PIPELINE ", "PIPELINE ")):
                if "ChatRuntime(" in stripped or "CognitiveTurnPipeline(" in stripped:
                    raise AssertionError(
                        "module-scope ChatRuntime/pipeline instance "
                        "breaks the warmed-per-case invariant"
                    )
        # Runtime must be constructed exactly once per case (inside
        # _run_case, before the per-turn loop).
        assert "runtime = ChatRuntime()" in src
        # And the per-turn body must NOT re-construct it.
        in_for_loop = False
        for line in src.splitlines():
            if "for idx, turn in enumerate(turns_spec):" in line:
                in_for_loop = True
                continue
            if in_for_loop and line.startswith("def "):
                break
            if in_for_loop and "ChatRuntime(" in line:
                raise AssertionError(
                    "ChatRuntime construction inside per-turn loop "
                    "defeats warmed-session invariant"
                )
