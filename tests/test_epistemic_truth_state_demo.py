from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from core.epistemic_state import EpistemicState, NormativeClearance
from demos.epistemic_truth_state import authority
from demos.epistemic_truth_state import run_demo as demo_runner

DEMO_DIR = Path(authority.__file__).resolve().parent
FIXTURES_DIR = DEMO_DIR / "fixtures"
EXPECTED_DIR = DEMO_DIR / "expected"

SCENARIOS = {
    "verified-supported-claim": ("assigned", "verified"),
    "evidenced-but-not-verified-claim": ("assigned", "evidenced"),
    "inferred-from-bounded-evidence": ("assigned", "inferred"),
    "unrelated-premise-still-undetermined": ("assigned", "undetermined"),
    "undetermined-insufficient-evidence": ("assigned", "undetermined"),
    "refused-outside-scope": ("refused", "scope_boundary"),
    "invalid-state-smuggling-attempt": ("invalid", None),
}


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _arguments(name: str) -> dict[str, object]:
    return _fixture(f"{name}.json")["arguments"]


def _run(name: str) -> dict[str, object]:
    return authority.run_authority(_arguments(name))


def test_schema_is_closed_recursively():
    schema = authority.load_schema()["inputSchema"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["proposer"]["additionalProperties"] is False
    assert schema["properties"]["claim"]["additionalProperties"] is False
    assert schema["properties"]["evidence"]["items"]["additionalProperties"] is False
    assert schema["properties"]["inference"]["additionalProperties"] is False

    # Every nested object in the input schema is closed, recursively.
    def _assert_closed(spec: dict[str, object], path: str) -> None:
        node_type = spec.get("type")
        if node_type == "object":
            assert spec.get("additionalProperties") is False, f"{path} is not closed"
            for name, child in spec.get("properties", {}).items():
                _assert_closed(child, f"{path}.{name}")
        elif node_type == "array":
            _assert_closed(spec["items"], f"{path}[]")

    _assert_closed(schema, "inputSchema")


def test_all_scenarios_work():
    for name, (status, assigned_state) in SCENARIOS.items():
        response = _run(name)
        assert response["status"] == status, name
        assert response["assigned_state"] == assigned_state, name


def test_uses_canonical_epistemic_state_enum():
    # authority.py imports the canonical taxonomy and defines no parallel enum.
    tree = ast.parse((DEMO_DIR / "authority.py").read_text(encoding="utf-8"))
    imported_from_core = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            base_names = {
                base.id for base in node.bases if isinstance(base, ast.Name)
            } | {
                base.attr for base in node.bases if isinstance(base, ast.Attribute)
            }
            assert "Enum" not in base_names, "demo must not define a parallel enum"
        if isinstance(node, ast.ImportFrom) and node.module == "core.epistemic_state":
            names = {alias.name for alias in node.names}
            assert {"EpistemicState", "coerce_epistemic_state"} <= names
            imported_from_core = True
    assert imported_from_core

    # Every emitted state/clearance is a member of the canonical enums.
    valid_states = {state.value for state in EpistemicState}
    valid_clearances = {clearance.value for clearance in NormativeClearance}
    for name in SCENARIOS:
        artifact = json.loads((EXPECTED_DIR / f"{name}.json").read_text(encoding="utf-8"))
        if artifact["assigned_state"] is not None:
            assert artifact["assigned_state"] in valid_states, name
        if artifact["normative_clearance"] is not None:
            assert artifact["normative_clearance"] in valid_clearances, name


def test_verified_requires_matching_evidence():
    response = _run("verified-supported-claim")
    assert response["assigned_state"] == "verified"
    # This demo runs no normative/safety/ethics clearance pass, so even a
    # verified claim stays UNASSESSABLE rather than positively cleared.
    assert response["normative_clearance"] == "unassessable"
    assert response["evidence_ledger"] == ["ev-a1-replay", "ev-a1-trace"]

    # Drop one independent record: a single supporting record cannot verify.
    one_record = _arguments("verified-supported-claim")
    one_record["evidence"] = one_record["evidence"][:1]
    downgraded = authority.run_authority(one_record)
    assert downgraded["assigned_state"] == "evidenced"
    assert downgraded["decision_reason"] == "evidence_present_but_not_verifying"

    # A corpus reference for a different subject/predicate is not matching
    # evidence at all.
    mismatched = _arguments("verified-supported-claim")
    mismatched["evidence"] = _arguments("undetermined-insufficient-evidence")["evidence"]
    none_match = authority.run_authority(mismatched)
    assert none_match["assigned_state"] == "undetermined"
    assert none_match["decision_reason"] == "insufficient_evidence"


def test_proposer_cannot_supply_support_or_independence_labels():
    payload = _arguments("verified-supported-claim")
    payload["evidence"][0]["supports"] = True
    payload["evidence"][0]["independent"] = True
    response = authority.run_authority(payload)
    assert response["status"] == "invalid"
    assert "payload.evidence[0] unexpected property 'supports'" in response["invalid_reason"]
    assert "payload.evidence[0] unexpected property 'independent'" in response["invalid_reason"]


def test_evidence_reference_hash_mismatch_is_invalid():
    payload = _arguments("verified-supported-claim")
    payload["evidence"][0]["content_sha256"] = "0" * 64
    response = authority.run_authority(payload)
    assert response["status"] == "invalid"
    assert response["decision_reason"] == "invalid_evidence_reference"
    assert "content hash mismatch for evidence reference 'ev-a1-trace'" in response["invalid_reason"]


def test_clearance_is_unassessable_for_all_non_invalid_outputs():
    # The demo assigns epistemic truth-state only; it runs no normative/safety/
    # ethics clearance pass, so it must never positively clear anything.
    for name in SCENARIOS:
        response = _run(name)
        if response["status"] == "invalid":
            assert response["normative_clearance"] is None, name
        else:
            assert response["normative_clearance"] == "unassessable", name


def test_evidenced_state_for_single_support():
    response = _run("evidenced-but-not-verified-claim")
    assert response["status"] == "assigned"
    assert response["assigned_state"] == "evidenced"
    assert response["decision_reason"] == "evidence_present_but_not_verifying"
    assert response["evidence_ledger"] == ["ev-b1-log"]


def test_inferred_is_decided_by_entailment_engine_with_oracle_agreement():
    response = _run("inferred-from-bounded-evidence")
    assert response["assigned_state"] == "inferred"
    assert response["decision_reason"] == "entailed_from_resolved_premises"
    assert response["inference_basis"] == [
        "ev-c1-branch-from-main",
        "ev-c1-rule-reachability",
        "ev-c1-tag-on-main",
    ]
    assert response["evidence_ledger"] == response["inference_basis"]

    inference = response["trace_summary"]["inference"]
    assert inference["consulted"] is True
    assert inference["outcome"] == "entailed"
    assert inference["reason"] == "tautological_implication"
    assert inference["oracle_verdict"] == "entailed"
    assert inference["engine_oracle_agreement"] is True
    # The ROBDD proof evidence is present: the implication check canonicalized
    # to the tautology node.
    assert inference["entailment_trace"]["entailment_check_key"] == "T"

    # Both deciders appear in the authority path only because they were consulted.
    assert "generate.proof_chain.entail.evaluate_entailment_with_trace" in (
        response["authority_path"]
    )
    assert "evals.deductive_logic.oracle.oracle_entailment" in response["authority_path"]


def test_unrelated_premise_cannot_mint_inferred():
    # The hazard this leg exists to prevent: a claim with no support, citing a
    # resolvable but logically UNRELATED record as a premise, must not be
    # assigned `inferred`.  The engine decides `unknown`; the state falls to
    # `undetermined`.
    response = _run("unrelated-premise-still-undetermined")
    assert response["assigned_state"] == "undetermined"
    assert response["decision_reason"] == "insufficient_evidence"
    inference = response["trace_summary"]["inference"]
    assert inference["consulted"] is True
    assert inference["outcome"] == "unknown"
    assert inference["oracle_verdict"] == "unknown"


def test_premises_without_the_rule_do_not_entail():
    # Dropping the rule record from the premises leaves two atoms that cannot
    # entail the claim: the engine decides `unknown`, no inferred state.
    payload = _arguments("inferred-from-bounded-evidence")
    payload["inference"]["premise_ids"] = ["ev-c1-tag-on-main", "ev-c1-branch-from-main"]
    response = authority.run_authority(payload)
    assert response["assigned_state"] == "undetermined"
    inference = response["trace_summary"]["inference"]
    assert inference["outcome"] == "unknown"
    assert inference["engine_oracle_agreement"] is True


def test_engine_oracle_disagreement_refuses(monkeypatch):
    # Defensive fail-closed: if the independent oracle ever disagreed with the
    # ROBDD engine, the demo must refuse rather than assign an inferred state.
    monkeypatch.setattr(authority, "oracle_entailment", lambda premises, query: "unknown")
    payload = _arguments("inferred-from-bounded-evidence")
    response = authority.run_authority(payload)
    assert response["status"] == "refused"
    assert response["refusal_reason"] == "entailment_oracle_disagreement"
    assert response["assigned_state"] is None


def test_unconsulted_entailment_engine_not_in_authority_path():
    response = _run("verified-supported-claim")
    assert "generate.proof_chain.entail.evaluate_entailment_with_trace" not in (
        response["authority_path"]
    )
    assert response["trace_summary"]["inference"] == {
        "consulted": False,
        "detail": "no_inference_block",
    }


def test_corpus_seal_is_pinned_in_traces():
    response = _run("verified-supported-claim")
    assert response["trace_summary"]["corpus_sha256"] == authority.corpus_file_sha256()
    assert response["trace_summary"]["corpus_id"] == (
        "demo.epistemic_truth_state.evidence_corpus.v1"
    )


def test_inference_with_unresolved_premise_does_not_infer():
    payload = _arguments("inferred-from-bounded-evidence")
    payload["inference"]["premise_ids"] = ["ev-c1-tag-on-main", "does-not-exist"]
    response = authority.run_authority(payload)
    assert response["assigned_state"] == "undetermined"
    assert response["trace_summary"]["inference"]["detail"] == "premise_unresolved"


def test_undetermined_emits_question():
    response = _run("undetermined-insufficient-evidence")
    assert response["assigned_state"] == "undetermined"
    assert response["evidence_ledger"] == []
    assert "insufficient grounded evidence" in response["question"]


def test_scope_boundary_refuses_without_consulting_corpus():
    response = _run("refused-outside-scope")
    assert response["status"] == "refused"
    assert response["assigned_state"] == "scope_boundary"
    assert response["refusal_reason"] == "outside_epistemic_envelope"
    assert response["decision_reason"] == "outside_epistemic_envelope"
    assert response["evidence_ledger"] == []
    # An out-of-envelope claim is refused before the corpus is consulted.
    assert response["trace_summary"]["evidence_resolution"] == "not_consulted"
    assert "demos.epistemic_truth_state.authority.resolve_evidence_refs" not in (
        response["authority_path"]
    )


def test_proposer_cannot_set_assigned_state():
    payload = _arguments("verified-supported-claim")
    payload["assigned_state"] = "verified"
    response = authority.run_authority(payload)
    assert response["status"] == "invalid"
    assert "payload unexpected property 'assigned_state'" in response["invalid_reason"]


def test_proposer_cannot_smuggle_root_authority_fields():
    response = _run("invalid-state-smuggling-attempt")
    assert response["status"] == "invalid"
    assert response["assigned_state"] is None
    assert response["normative_clearance"] is None
    for forged in ("assigned_state", "status", "evidence_ledger", "authority_path", "trace_hash"):
        assert f"unexpected property '{forged}'" in response["invalid_reason"]


def test_proposer_trace_hash_is_ignored():
    payload = _arguments("verified-supported-claim")
    response = authority.run_authority(payload)
    assert response["trace_summary"]["proposer_trace_hash_ignored"] is True
    assert response["trace_hash"] != payload["proposer"]["trace_hash"]


def test_proposer_proposed_state_is_ignored():
    # Proposer claims "verified" but supplies zero evidence: CORE assigns undetermined.
    payload = _arguments("undetermined-insufficient-evidence")
    payload["proposer"]["proposed_state"] = "verified"
    payload["evidence"] = []
    response = authority.run_authority(payload)
    assert response["trace_summary"]["proposer_state_ignored"] is True
    assert response["assigned_state"] == "undetermined"


def test_invalid_payload_fails_before_state_evaluation(monkeypatch):
    def _explode(_payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError("state evaluation ran for an invalid payload")

    monkeypatch.setattr(authority, "assign_epistemic_state", _explode)
    response = _run("invalid-state-smuggling-attempt")
    assert response["status"] == "invalid"
    assert response["trace_summary"]["authority_evaluated"] is False


def test_double_run_outputs_byte_identical():
    for name in SCENARIOS:
        payload = _arguments(name)
        run_a = authority.run_authority(payload)
        run_b = authority.run_authority(payload)
        rendered_a = json.dumps(run_a, sort_keys=True, indent=2)
        rendered_b = json.dumps(run_b, sort_keys=True, indent=2)
        assert rendered_a == rendered_b, name


def test_expected_artifact_tampering_fails(tmp_path):
    scenario_id = "verified-supported-claim"
    ref = EXPECTED_DIR / f"{scenario_id}.json"
    original = ref.read_text(encoding="utf-8")
    try:
        ref.write_text(original.replace("verified", "evidenced", 1), encoding="utf-8")
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("sys.argv", ["run_demo.py", "--out", str(tmp_path / "out")])
            assert demo_runner.main() == 1
    finally:
        ref.write_text(original, encoding="utf-8")


def test_run_demo_all_passes_against_expected(tmp_path, monkeypatch):
    out_dir = tmp_path / "demo-out"
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", str(out_dir)])
    assert demo_runner.main() == 0


def test_run_demo_default_out_still_works(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_demo.py"])
    assert demo_runner.main() == 0


def test_run_demo_refuses_non_default_dir_without_marker(tmp_path, monkeypatch):
    out_dir = tmp_path / "missing-marker"
    out_dir.mkdir()
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", str(out_dir)])
    assert demo_runner.main() == 2


@pytest.mark.parametrize("target", [".", ".."])
def test_run_demo_refuses_parent_like_paths(target: str, monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", target])
    assert demo_runner.main() == 2


def test_no_network_subprocess_eval_or_exec_imports_or_calls():
    forbidden_imports = {"subprocess", "socket", "requests", "httpx", "urllib", "urllib.request"}
    forbidden_calls = {"eval", "exec", "compile", "open_connection", "create_connection", "Popen", "run"}
    scanned = [
        DEMO_DIR / "__init__.py",
        DEMO_DIR / "authority.py",
        DEMO_DIR / "run_demo.py",
    ]
    for path in scanned:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_imports
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "") not in forbidden_imports
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in forbidden_calls
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in forbidden_calls
