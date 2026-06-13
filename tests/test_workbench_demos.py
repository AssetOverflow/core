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
