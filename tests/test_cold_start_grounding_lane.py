"""Contract tests for the ``cold_start_grounding`` eval lane.

This lane commits the 44-prompt routing probe described in
``evals/cold_start_grounding/contract.md``.  The probe is the durable,
replayable artifact behind the 2026-05-19 lift from 52% "I don't know"
responses to 0% (out of 44 realistic conversational prompts).

These tests pin:

  - Case-set integrity (count, required fields, valid enum values).
  - Lane discovery (framework can find and load the lane).
  - Pass thresholds (intent / grounding / subject all >= 0.95 / 0.95 / 0.90).
  - The deliberate non-fallback for CAUSE / VERIFICATION without
    teaching chains: those cases expect ``grounding_source='none'``.
  - Cold-start invariant: a fresh ``ChatRuntime()`` is used per case.
"""

from __future__ import annotations

import json
from pathlib import Path

from evals.framework import (
    discover_lanes,
    get_lane,
    load_cases,
    load_lane_runner,
    run_lane,
)


LANE_NAME = "cold_start_grounding"
_EVAL_ROOT = Path(__file__).resolve().parent.parent / "evals" / LANE_NAME
_PUBLIC_CASES = _EVAL_ROOT / "public" / "v1" / "cases.jsonl"
_DEV_CASES = _EVAL_ROOT / "dev" / "cases.jsonl"

_VALID_GROUNDING = frozenset({"pack", "teaching", "oov", "none", "vault", "partial"})
_VALID_INTENTS = frozenset({
    "definition", "cause", "procedure", "comparison", "correction",
    "recall", "verification", "transitive_query", "frame_transfer",
    "narrative", "example", "unknown",
})


class TestCaseSetIntegrity:
    def test_public_cases_file_exists(self) -> None:
        assert _PUBLIC_CASES.exists()

    def test_public_case_count(self) -> None:
        cases = load_cases(_PUBLIC_CASES)
        assert len(cases) == 44

    def test_every_case_has_required_fields(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            for field in ("id", "prompt", "category",
                          "expected_intent", "expected_grounding_source"):
                assert field in case, (case["id"], field)
                assert isinstance(case[field], str) and case[field], (case["id"], field)

    def test_every_grounding_source_is_valid(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            assert case["expected_grounding_source"] in _VALID_GROUNDING, case

    def test_every_intent_is_valid(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            assert case["expected_intent"] in _VALID_INTENTS, case

    def test_case_ids_unique(self) -> None:
        ids = [c["id"] for c in load_cases(_PUBLIC_CASES)]
        assert len(ids) == len(set(ids))

    def test_dev_cases_subset_of_categories(self) -> None:
        """Dev split must use the same case schema as public."""
        cases = load_cases(_DEV_CASES)
        assert len(cases) >= 1
        for case in cases:
            assert case["expected_grounding_source"] in _VALID_GROUNDING


class TestLaneDiscovery:
    def test_lane_is_discoverable(self) -> None:
        names = {lane.name for lane in discover_lanes()}
        assert LANE_NAME in names

    def test_lane_has_v1_version(self) -> None:
        lane = get_lane(LANE_NAME)
        assert "v1" in lane.versions

    def test_lane_runner_loads(self) -> None:
        lane = get_lane(LANE_NAME)
        runner = load_lane_runner(lane)
        assert hasattr(runner, "run_lane")


class TestPassThresholds:
    """The lane must satisfy its contract thresholds on the public set.

    Thresholds (from ``contract.md``):

      - intent_accuracy    >= 0.95
      - grounding_accuracy >= 0.95
      - subject_accuracy   >= 0.90
    """

    def test_public_v1_passes_thresholds(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        metrics = result.metrics
        assert metrics["intent_accuracy"] >= 0.95, metrics
        assert metrics["grounding_accuracy"] >= 0.95, metrics
        assert metrics["subject_accuracy"] >= 0.90, metrics

    def test_distributions_match_expected(self) -> None:
        """When pass thresholds are 100%, the actual grounding
        distribution must match the expected distribution exactly.
        Drift here means a regression in intent routing."""
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        actual = result.metrics["grounding_distribution_actual"]
        expected = result.metrics["grounding_distribution_expected"]
        assert actual == expected, (
            f"grounding distribution drifted: actual={actual} expected={expected}"
        )


class TestArchitecturalInvariants:
    """Pins two doctrine invariants the case set encodes:

      1. ``oov_control`` cases ground as ``oov`` (genuinely unknown).
      2. ``cause_no_teaching_chain`` cases stay ``none`` (the
         deliberate non-fallback that preserves the discovery-gap
         signal).
    """

    def test_oov_control_cases_route_to_oov(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            if case.get("category") == "oov_control":
                assert case["expected_grounding_source"] == "oov", case

    def test_cause_no_chain_cases_route_to_none(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            if case.get("category") == "cause_no_teaching_chain":
                assert case["expected_grounding_source"] == "none", case
                assert case["expected_intent"] == "cause", case


class TestColdStartInvariant:
    """The runner must construct a fresh ``ChatRuntime()`` per case.

    Without this invariant the metric drifts: vault accumulation from
    earlier turns can override the pack source on later turns and
    produce garbled surfaces (this was the bug observed during the
    2026-05-19 probe before the fresh-runtime-per-prompt fix).
    """

    def test_runner_module_uses_fresh_runtime(self) -> None:
        runner_src = (_EVAL_ROOT / "runner.py").read_text(encoding="utf-8")
        # Cold-start invariant must appear as code, not just a docstring.
        # The runner constructs ChatRuntime() inside _run_case.
        assert "ChatRuntime()" in runner_src
        # And the construction must be inside the per-case helper,
        # not module-scope (which would share runtime across cases).
        # We assert the absence of a module-level instance binding.
        for line in runner_src.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("_RUNTIME ", "_runtime ", "RUNTIME ")):
                if "ChatRuntime(" in stripped:
                    raise AssertionError(
                        "module-scope ChatRuntime instance breaks the "
                        "cold-start invariant"
                    )


class TestResultSerialization:
    """The lane report must be JSON-serializable end-to-end."""

    def test_metrics_round_trip(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        payload = json.dumps(result.as_dict(), sort_keys=True)
        reloaded = json.loads(payload)
        assert reloaded["metrics"]["cases"] == 44
