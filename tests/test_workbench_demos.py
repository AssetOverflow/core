from __future__ import annotations

from pathlib import Path

from workbench.api import WorkbenchApi
from workbench import readers


def _demo_out_dirs() -> dict[str, bool]:
    root = Path("demos")
    return {
        path.as_posix(): path.exists()
        for path in sorted(root.glob("*/out"))
    }


def test_list_demos_projects_closed_registry() -> None:
    demos = readers.list_demos()

    ids = {demo.demo_id for demo in demos}
    assert "proof_carrying_promotion" in ids
    assert "deductive_entailment_authority" in ids
    assert all(demo.read_only is True for demo in demos)
    assert all(demo.scenario_count == len(demo.scenarios) for demo in demos)
    assert all(s.what_this_proves for demo in demos for s in demo.scenarios)


def test_run_demo_compares_against_committed_expected_artifacts() -> None:
    result = readers.run_demo("deductive_entailment_authority")

    assert result.demo_id == "deductive_entailment_authority"
    assert result.all_passed is True
    assert result.what_this_proves
    assert any(s.proposer_wrong for s in result.scenarios)
    assert all(s.response for s in result.scenarios)


def test_proof_carrying_promotion_projects_all_scenarios_as_dags() -> None:
    result = readers.run_demo("proof_carrying_promotion")

    assert len(result.scenarios) == 8
    assert all(s.evidence_dag is not None for s in result.scenarios)
    for scenario in result.scenarios:
        assert scenario.evidence_dag is not None
        assert scenario.evidence_dag.graph_kind == "proof_carrying_promotion"
        assert scenario.evidence_dag.source_digest
        node_ids = {node.node_id for node in scenario.evidence_dag.nodes}
        assert {"request", "validate", "claim", "certify", "apply", "outcome"}.issubset(
            node_ids
        )
        assert all(
            edge.from_node in node_ids and edge.to_node in node_ids
            for edge in scenario.evidence_dag.edges
        )


def test_deductive_entailment_projects_trace_as_dag_when_engine_ran() -> None:
    result = readers.run_demo("deductive_entailment_authority")

    traced = [
        s
        for s in result.scenarios
        if isinstance(s.response, dict) and s.response.get("entailment_trace")
    ]
    assert traced
    assert all(s.evidence_dag is not None for s in traced)
    for scenario in traced:
        assert scenario.evidence_dag is not None
        assert scenario.evidence_dag.graph_kind == "deductive_entailment"
        node_ids = {node.node_id for node in scenario.evidence_dag.nodes}
        assert {
            "conjunction",
            "query",
            "engine_check",
            "oracle_check",
            "decision",
        }.issubset(node_ids)
        assert all(
            edge.from_node in node_ids and edge.to_node in node_ids
            for edge in scenario.evidence_dag.edges
        )


def test_demo_api_refuses_unknown_or_unsafe_ids() -> None:
    api = WorkbenchApi()

    unknown = api.handle("POST", "/demos/not_registered/run", b"")
    unsafe = api.handle("POST", "/demos/../proof_carrying_promotion/run", b"")

    assert unknown.status == 404
    assert unknown.payload["error"]["code"] == "not_found"
    assert unsafe.status == 400
    assert unsafe.payload["error"]["code"] == "bad_request"


def test_demo_run_endpoint_does_not_write_demo_out_dirs() -> None:
    before = _demo_out_dirs()
    api = WorkbenchApi()

    response = api.handle("POST", "/demos/proof_carrying_promotion/run", b"")

    assert response.status == 200
    assert response.payload["data"]["all_passed"] is True
    assert _demo_out_dirs() == before
