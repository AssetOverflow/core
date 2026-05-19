"""Contract tests for the ``deterministic_fluency`` eval lane.

The lane defines fluency as six deterministic structural predicates,
not as subjective quality.  Tests here pin:

  - Case-set integrity.
  - All six predicates are implemented and run cleanly.
  - The runner produces all required metrics.
  - Three hard invariants hold on current main (no_placeholder == 1,
    complete_punctuation == 1, finite_predicate >= 0.90).
  - The lift-target metrics (no_provenance_only, no_dotted_inventory)
    are recorded but NOT pinned to a threshold yet — they are the
    gloss feature's measurement substrate.

The six predicates are: no_placeholder, no_provenance_only,
complete_punctuation, finite_predicate_shape, no_dotted_inventory,
surface_provenance_match.
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


LANE_NAME = "deterministic_fluency"
_EVAL_ROOT = Path(__file__).resolve().parent.parent / "evals" / LANE_NAME
_PUBLIC_CASES = _EVAL_ROOT / "public" / "v1" / "cases.jsonl"

ALL_PREDICATES = (
    "no_placeholder",
    "no_provenance_only",
    "complete_punctuation",
    "finite_predicate_shape",
    "no_dotted_inventory",
    "surface_provenance_match",
)


class TestCaseSetIntegrity:
    def test_public_cases_file_exists(self) -> None:
        assert _PUBLIC_CASES.exists()

    def test_case_count(self) -> None:
        cases = load_cases(_PUBLIC_CASES)
        assert len(cases) >= 10

    def test_every_case_has_required_fields(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            assert "id" in case
            assert "prompt" in case
            assert "expected_predicates" in case
            assert isinstance(case["expected_predicates"], list)

    def test_expected_predicates_are_known(self) -> None:
        for case in load_cases(_PUBLIC_CASES):
            for pred in case["expected_predicates"]:
                assert pred in ALL_PREDICATES, (case["id"], pred)


class TestLaneDiscovery:
    def test_lane_is_discoverable(self) -> None:
        names = {lane.name for lane in discover_lanes()}
        assert LANE_NAME in names

    def test_lane_runner_loads(self) -> None:
        lane = get_lane(LANE_NAME)
        runner = load_lane_runner(lane)
        assert hasattr(runner, "run_lane")


class TestRunnerMetrics:
    def test_all_predicate_rates_present(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        for pred in ALL_PREDICATES:
            key = f"{pred}_rate"
            assert key in result.metrics, (
                f"missing metric {key!r}; got: {sorted(result.metrics)}"
            )

    def test_per_case_predicates_dict_present(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        for case in result.case_details:
            assert "predicates" in case
            assert isinstance(case["predicates"], dict)
            for pred in ALL_PREDICATES:
                assert pred in case["predicates"], (case["case_id"], pred)
                assert isinstance(case["predicates"][pred], bool)


class TestHardInvariants:
    """Three predicates have hard 1.00 / >=0.90 thresholds that should
    hold on current main.  These are the structural-completeness floor
    — any regression here is a doctrine violation, not a tunable."""

    def test_no_placeholder_rate_is_one(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        rate = result.metrics["no_placeholder_rate"]
        assert rate == 1.0, (
            f"no_placeholder_rate dropped below 1.0: {rate}. "
            f"A user-facing surface containing ..., <pending>, or <prior> "
            f"is a doctrine violation."
        )

    def test_complete_punctuation_rate_is_one(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        rate = result.metrics["complete_punctuation_rate"]
        assert rate == 1.0, (
            f"complete_punctuation_rate dropped below 1.0: {rate}"
        )

    def test_finite_predicate_rate_at_least_ninety(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        rate = result.metrics["finite_predicate_shape_rate"]
        assert rate >= 0.90, (
            f"finite_predicate_shape_rate dropped below 0.90: {rate}"
        )

    def test_expected_predicates_all_pass(self) -> None:
        """Every case must satisfy at least its OWN declared
        expected_predicates list.  Cases that include an
        as-yet-unmet predicate must move that predicate to
        post_gloss_predicates instead."""
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        rate = result.metrics["expected_predicates_pass_rate"]
        assert rate == 1.0, (
            f"some cases failed their own expected_predicates: rate={rate}"
        )


class TestLiftTargetMetricsAreRecorded:
    """The two metrics the gloss feature is designed to lift are
    recorded today but NOT pinned to a threshold.  When the gloss
    feature lands, these tests will be extended with thresholds."""

    def test_no_provenance_only_rate_present(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        assert "no_provenance_only_rate" in result.metrics

    def test_no_dotted_inventory_rate_present(self) -> None:
        lane = get_lane(LANE_NAME)
        result = run_lane(lane, version="v1", split="public")
        assert "no_dotted_inventory_rate" in result.metrics
        # Sanity check: should be a float in [0, 1].
        rate = result.metrics["no_dotted_inventory_rate"]
        assert 0.0 <= rate <= 1.0
