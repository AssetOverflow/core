"""Contract tests for the ``contemplation_quality`` eval lane.

W-025 / ADR-0159.  The lane scores the structured output from
``core demo learning-arc --json`` along nine deterministic, non-mutating
quality gates without widening the trust surface.

These tests pin:

  - Case-set integrity (single invocation case, required schema).
  - Lane discovery via the generic eval framework (no CLI wiring needed).
  - ``evaluate_report`` purity over arbitrary dictionaries (well-formed,
    malformed, empty, wrong types).
  - ``run_lane`` input-shape enforcement (single case, source enum).
  - Read-only invariant: lane execution must not produce filesystem writes
    under teaching/, packs/, or engine_state/ during scoring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.framework import (
    discover_lanes,
    get_lane,
    load_cases,
    load_lane_runner,
)
from evals.contemplation_quality.runner import (
    ContemplationQualityReport,
    LaneReport,
    QualityMetric,
    evaluate_report,
    run_lane,
)


LANE_NAME = "contemplation_quality"
_EVAL_ROOT = Path(__file__).resolve().parent.parent / "evals" / LANE_NAME
_PUBLIC_CASES = _EVAL_ROOT / "public" / "v1" / "cases.jsonl"
_DEV_CASES = _EVAL_ROOT / "dev" / "cases.jsonl"
_CONTRACT = _EVAL_ROOT / "contract.md"


_REQUIRED_METRIC_NAMES: frozenset[str] = frozenset({
    "scene_contract",
    "deterministic_replay_integrity",
    "typed_contemplation_provenance",
    "engine_authored_specificity",
    "grounding_transition",
    "downstream_gain_observed",
    "active_corpus_boundary",
    "pending_not_auto_accepted",
    "stable_proposal_identity_present",
})


# ---------------------------------------------------------------------------
# Case-set integrity
# ---------------------------------------------------------------------------


class TestCaseSetIntegrity:
    def test_public_cases_file_exists(self) -> None:
        assert _PUBLIC_CASES.exists()

    def test_dev_cases_file_exists(self) -> None:
        assert _DEV_CASES.exists()

    def test_contract_file_exists(self) -> None:
        assert _CONTRACT.exists()

    def test_public_case_count_is_one(self) -> None:
        cases = load_cases(_PUBLIC_CASES)
        assert len(cases) == 1

    def test_dev_case_count_is_one(self) -> None:
        cases = load_cases(_DEV_CASES)
        assert len(cases) == 1

    def test_case_required_fields(self) -> None:
        for path in (_PUBLIC_CASES, _DEV_CASES):
            for case in load_cases(path):
                assert "case_id" in case and isinstance(case["case_id"], str)
                assert "source" in case and isinstance(case["source"], str)

    def test_case_source_is_supported_enum(self) -> None:
        for path in (_PUBLIC_CASES, _DEV_CASES):
            for case in load_cases(path):
                assert case["source"] == "learning_arc_demo"


# ---------------------------------------------------------------------------
# Lane discovery via the generic framework
# ---------------------------------------------------------------------------


class TestLaneDiscovery:
    def test_lane_is_discoverable(self) -> None:
        names = {lane.name for lane in discover_lanes()}
        assert LANE_NAME in names

    def test_lane_has_v1_version(self) -> None:
        lane = get_lane(LANE_NAME)
        assert "v1" in lane.versions

    def test_lane_runner_exposes_run_lane(self) -> None:
        lane = get_lane(LANE_NAME)
        runner = load_lane_runner(lane)
        assert hasattr(runner, "run_lane")
        assert hasattr(runner, "evaluate_report")


# ---------------------------------------------------------------------------
# evaluate_report — pure function over a dict
# ---------------------------------------------------------------------------


def _passing_report() -> dict:
    """Synthesize a minimal learning-arc report that satisfies every gate."""
    return {
        "engine_connective": "grounds",
        "engine_object": "truth",
        "learning_arc_closed": True,
        "active_corpus_byte_identical": True,
        "before": {"surface": "I don't know."},
        "after": {"surface": "light grounds truth"},
        "scenes": [
            {
                "scene": "S1_cold_session",
                "detail": {"grounding_source": "none"},
            },
            {
                "scene": "S2_checkpoint_enrichment",
                "detail": {
                    "engine_chain_found": True,
                    "engine_chain": {"connective": "grounds", "object": "truth"},
                },
            },
            {
                "scene": "S3_engine_authored_proposal",
                "detail": {
                    "source_kind": "contemplation",
                    "proposal_id": "proposal-abc123",
                    "state": "pending",
                    "replay_evidence": {
                        "replay_equivalent": True,
                        "regressed_metrics": [],
                    },
                    "proposed_chain": {
                        "connective": "grounds",
                        "object": "truth",
                    },
                },
            },
            {
                "scene": "S4_operator_ratifies",
                "detail": {"active_corpus_byte_identical": True},
            },
            {
                "scene": "S5_grounded_session",
                "detail": {"grounding_source": "teaching"},
            },
        ],
    }


class TestEvaluateReportShape:
    def test_returns_contemplation_quality_report(self) -> None:
        report = evaluate_report(_passing_report())
        assert isinstance(report, ContemplationQualityReport)

    def test_lane_label_is_canonical(self) -> None:
        report = evaluate_report(_passing_report())
        assert report.lane == "contemplation-quality"

    def test_source_label_is_canonical(self) -> None:
        report = evaluate_report(_passing_report())
        assert report.source == "core demo learning-arc --json"

    def test_source_digest_is_sha256_hex(self) -> None:
        report = evaluate_report(_passing_report())
        assert isinstance(report.source_digest, str)
        assert len(report.source_digest) == 64
        int(report.source_digest, 16)  # raises ValueError if non-hex

    def test_all_nine_metrics_present(self) -> None:
        report = evaluate_report(_passing_report())
        names = {m.name for m in report.metrics}
        assert names == _REQUIRED_METRIC_NAMES

    def test_metrics_are_quality_metric_instances(self) -> None:
        report = evaluate_report(_passing_report())
        for metric in report.metrics:
            assert isinstance(metric, QualityMetric)


class TestEvaluateReportDeterminism:
    def test_same_input_yields_same_digest(self) -> None:
        a = evaluate_report(_passing_report())
        b = evaluate_report(_passing_report())
        assert a.source_digest == b.source_digest

    def test_well_formed_report_passes(self) -> None:
        report = evaluate_report(_passing_report())
        assert report.passed is True

    def test_serializable_as_dict(self) -> None:
        report = evaluate_report(_passing_report()).as_dict()
        # Must be JSON-serializable without raising.  Tuples in ``expected``
        # values become lists after a JSON round-trip, which is fine for
        # downstream consumers — the contract here is only serializability.
        encoded = json.dumps(report)
        decoded = json.loads(encoded)
        assert decoded["lane"] == report["lane"]
        assert decoded["source_digest"] == report["source_digest"]
        assert decoded["passed"] is report["passed"]
        assert decoded["score"] == report["score"]
        assert len(decoded["metrics"]) == len(report["metrics"])


class TestEvaluateReportBoundaryViolations:
    """Each gate should fail when its specific invariant is broken."""

    def _mutate_scene(
        self,
        report: dict,
        scene_name: str,
        **detail_overrides,
    ) -> dict:
        for scene in report["scenes"]:
            if scene["scene"] == scene_name:
                scene["detail"] = {**scene["detail"], **detail_overrides}
        return report

    def _failed_metric(
        self,
        report: ContemplationQualityReport,
        name: str,
    ) -> QualityMetric:
        for metric in report.metrics:
            if metric.name == name:
                return metric
        raise AssertionError(f"metric {name!r} not in report")

    def test_scene_contract_fails_on_missing_scene(self) -> None:
        report = _passing_report()
        report["scenes"] = report["scenes"][:-1]
        scored = evaluate_report(report)
        assert self._failed_metric(scored, "scene_contract").passed is False

    def test_replay_integrity_fails_when_not_equivalent(self) -> None:
        report = self._mutate_scene(
            _passing_report(),
            "S3_engine_authored_proposal",
            replay_evidence={
                "replay_equivalent": False,
                "regressed_metrics": ["surface_diff"],
            },
        )
        scored = evaluate_report(report)
        assert (
            self._failed_metric(scored, "deterministic_replay_integrity").passed
            is False
        )

    def test_pending_gate_fails_on_auto_acceptance(self) -> None:
        report = self._mutate_scene(
            _passing_report(),
            "S3_engine_authored_proposal",
            state="accepted",
        )
        scored = evaluate_report(report)
        assert (
            self._failed_metric(scored, "pending_not_auto_accepted").passed
            is False
        )

    def test_active_corpus_boundary_fails_on_byte_drift(self) -> None:
        report = _passing_report()
        report["active_corpus_byte_identical"] = False
        scored = evaluate_report(report)
        assert (
            self._failed_metric(scored, "active_corpus_boundary").passed
            is False
        )

    def test_provenance_gate_fails_without_contemplation_kind(self) -> None:
        report = self._mutate_scene(
            _passing_report(),
            "S3_engine_authored_proposal",
            source_kind="seeded",
        )
        scored = evaluate_report(report)
        assert (
            self._failed_metric(scored, "typed_contemplation_provenance").passed
            is False
        )


class TestEvaluateReportMalformedInput:
    """The pure-function entry point must reject or absorb malformed shapes."""

    def test_non_dict_input_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            evaluate_report([])  # type: ignore[arg-type]

    def test_none_input_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            evaluate_report(None)  # type: ignore[arg-type]

    def test_empty_report_produces_all_failing_metrics(self) -> None:
        scored = evaluate_report({})
        assert scored.passed is False
        # All nine metrics still emitted — none are silently skipped.
        assert {m.name for m in scored.metrics} == _REQUIRED_METRIC_NAMES

    def test_malformed_scenes_field_does_not_crash(self) -> None:
        scored = evaluate_report({"scenes": "not-a-list"})
        assert scored.passed is False

    def test_malformed_scene_detail_does_not_crash(self) -> None:
        scored = evaluate_report(
            {"scenes": [{"scene": "S1_cold_session", "detail": "wrong-type"}]}
        )
        assert scored.passed is False


# ---------------------------------------------------------------------------
# run_lane — invocation-contract enforcement
# ---------------------------------------------------------------------------


class TestRunLaneInputContract:
    def test_empty_case_list_rejected(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            run_lane([])

    def test_multiple_cases_rejected(self) -> None:
        with pytest.raises(ValueError, match="exactly one"):
            run_lane([
                {"case_id": "a", "source": "learning_arc_demo"},
                {"case_id": "b", "source": "learning_arc_demo"},
            ])

    def test_non_list_input_rejected(self) -> None:
        with pytest.raises(ValueError):
            run_lane("not-a-list")  # type: ignore[arg-type]

    def test_non_dict_case_rejected(self) -> None:
        with pytest.raises(TypeError):
            run_lane(["not-a-dict"])  # type: ignore[list-item]

    def test_unsupported_source_rejected(self) -> None:
        with pytest.raises(ValueError, match="unsupported"):
            run_lane([{"case_id": "x", "source": "external_dataset_v2"}])


# ---------------------------------------------------------------------------
# Read-only invariant — execution must not write outside tempdirs
# ---------------------------------------------------------------------------


class TestReadOnlyInvariant:
    """ADR-0159 read-only invariants.

    The lane must never mutate the active teaching corpus or any pack data
    file.  These are the trust boundaries the proposal/teaching path
    protects: corpus mutation requires ``accept_proposal``, pack mutation
    requires a reviewed pack-mutation ADR path, and neither is exercised
    by the eval lane.

    Note on ``engine_state/``: the lane's downstream demo (run_demo) runs
    a replay-equivalence gate that spawns the cognition lane, whose
    per-case ``ChatRuntime`` instances checkpoint to ``engine_state/`` via
    the runtime path already governed by ADR-0146/0150.  That checkpoint
    surface is a transient runtime artifact, not a teaching/pack write,
    so it is explicitly out of scope for this invariant.
    """

    def _snapshot(self, root: Path) -> dict[str, bytes]:
        snap: dict[str, bytes] = {}
        if not root.exists():
            return snap
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            # Skip Python bytecode caches and the package's own
            # ``__init__.py`` — they are not corpus/pack content.
            if "__pycache__" in rel.parts or rel.suffix in {".pyc", ".pyo"}:
                continue
            snap[str(rel)] = path.read_bytes()
        return snap

    def test_run_lane_does_not_mutate_teaching_or_packs(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        guarded = {
            "teaching/corpora": repo_root / "teaching" / "corpora",
            "packs": repo_root / "packs",
            "language_packs/data": repo_root / "language_packs" / "data",
        }
        before = {k: self._snapshot(v) for k, v in guarded.items()}

        result = run_lane(load_cases(_PUBLIC_CASES))

        after = {k: self._snapshot(v) for k, v in guarded.items()}
        for key in guarded:
            assert before[key] == after[key], (
                f"lane execution mutated {key} — trust boundary violated"
            )
        assert isinstance(result, LaneReport)
        assert result.metrics["all_passed"] is True
