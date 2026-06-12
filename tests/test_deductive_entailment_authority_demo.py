"""Deductive entailment authority demo — the demo envelope end-to-end.

Proves: closed schema, pinned expected artifacts, double-run determinism,
proposer-garbage immunity (the decision is recomputed, never echoed),
independent oracle cross-check (code-disjoint from the engine; disagreement
refuses defensively), no-vacuous-entailment refusal on inconsistent
premises, by-design out-of-regime refusal, and the INV-21/INV-24/INV-29
discipline of the demo files themselves (demos/ is scanned by the
invariants — the demo must add no vault writer, no recall, and no
status-transition site).
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from demos.deductive_entailment_authority import authority
from demos.deductive_entailment_authority import run_demo as demo_runner
from generate.proof_chain.engine_pin import DEDUCTIVE_ENGINE_PIN

DEMO_DIR = Path(authority.__file__).resolve().parent
FIXTURES_DIR = DEMO_DIR / "fixtures"
EXPECTED_DIR = DEMO_DIR / "expected"
REPO_ROOT = DEMO_DIR.parents[1]
ORACLE_PATH = REPO_ROOT / "evals" / "deductive_logic" / "oracle.py"

# scenario -> (status, decision, decision_reason)
SCENARIOS = {
    "entailed-modus-ponens": ("decided", "entailed", "tautological_implication"),
    "refuted-negation": ("decided", "refuted", "tautological_refutation"),
    "unknown-non-sequitur": ("decided", "unknown", "undetermined"),
    "refused-inconsistent-premises": ("refused", None, "inconsistent_premises"),
    "refused-out-of-regime-formula": ("refused", None, "out_of_regime_or_malformed"),
    "proposer-wrong-unknown": ("decided", "unknown", "undetermined"),
    "proposer-wrong-refuted": ("decided", "refuted", "tautological_refutation"),
}


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def _arguments(name: str) -> dict[str, object]:
    return _fixture(name)["arguments"]


def _run(name: str) -> dict[str, object]:
    return authority.run_authority(_arguments(name))


# ---------------------------------------------------------------------------
# Schema and scenario conformance
# ---------------------------------------------------------------------------

def test_schema_is_closed_recursively():
    schema = authority.load_schema()["inputSchema"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False

    def _assert_closed(spec: dict[str, object], path: str) -> None:
        node_type = spec.get("type")
        if node_type == "object":
            assert spec.get("additionalProperties") is False, f"{path} is not closed"
            for name, child in spec.get("properties", {}).items():
                _assert_closed(child, f"{path}.{name}")
        elif node_type == "array":
            _assert_closed(spec["items"], f"{path}[]")

    _assert_closed(schema, "inputSchema")


def test_all_scenarios_match_status_decision_and_reason():
    for name, (status, decision, reason) in SCENARIOS.items():
        response = _run(name)
        assert response["status"] == status, name
        assert response["decision"] == decision, name
        assert response["decision_reason"] == reason, name


def test_all_scenarios_match_committed_expected_artifacts():
    for name in SCENARIOS:
        response = _run(name)
        rendered = json.dumps(response, sort_keys=True, indent=2) + "\n"
        expected = (EXPECTED_DIR / f"{name}.json").read_text(encoding="utf-8")
        assert rendered == expected, f"{name} drifted from its expected artifact"


def test_double_run_outputs_byte_identical():
    for name in SCENARIOS:
        payload = _arguments(name)
        run_a = authority.run_authority(payload)
        run_b = authority.run_authority(payload)
        assert (
            json.dumps(run_a, sort_keys=True, separators=(",", ":"))
            == json.dumps(run_b, sort_keys=True, separators=(",", ":"))
        ), name


# ---------------------------------------------------------------------------
# Outcome taxonomy — decided / refused / invalid separated cleanly
# ---------------------------------------------------------------------------

def test_outcomes_separated_cleanly():
    for name, (status, _, _) in SCENARIOS.items():
        response = _run(name)
        assert response["decision"] != "refused", name  # refusal is never a decision
        if status == "decided":
            assert response["decision"] in {"entailed", "refuted", "unknown"}, name
            assert response["refusal_reason"] is None, name
        else:
            assert response["decision"] is None, name
            assert response["refusal_reason"] == response["decision_reason"], name
        assert response["invalid_reason"] is None, name
        assert response["engine_pin"] == DEDUCTIVE_ENGINE_PIN, name


def test_decision_is_recomputed_not_echoed():
    """The jaw-dropper scenarios: the proposer asserts `entailed`; CORE
    recomputes and proves the opposite (or underdetermination)."""
    for name, computed in (
        ("refuted-negation", "refuted"),
        ("proposer-wrong-refuted", "refuted"),
        ("proposer-wrong-unknown", "unknown"),
    ):
        payload = _arguments(name)
        assert payload["proposer"]["verdict"] == "entailed", name
        response = _run(name)
        assert response["decision"] == computed, name
        assert "verdict" in response["proposer_ignored_fields"], name


def test_oracle_cross_check_agrees_on_all_committed_scenarios():
    """Inside the supported regime the engine and the independent oracle
    agree on every committed scenario — including both refusals."""
    for name in SCENARIOS:
        response = _run(name)
        assert response["oracle_agreement"] is True, name
        assert response["trace_summary"]["defensive_refusal"] is False, name


# ---------------------------------------------------------------------------
# Refusal semantics — no vacuous entailment, by-design regime boundary
# ---------------------------------------------------------------------------

def test_inconsistent_premises_refuse_no_vacuous_entailment():
    """From a contradiction everything follows classically; the engine
    declines instead — for the claim AND for its negation."""
    base = _arguments("refused-inconsistent-premises")
    for claim in ("pump_on", "~pump_on"):
        payload = copy.deepcopy(base)
        payload["claim"] = claim
        response = authority.run_authority(payload)
        assert response["status"] == "refused", claim
        assert response["decision"] is None, claim
        assert response["decision_reason"] == "inconsistent_premises", claim


def test_out_of_regime_or_malformed_refuses():
    """Quantified, predicate-application, and malformed input all refuse
    with the engine's typed reason — never a guessed decision."""
    base = _arguments("entailed-modus-ponens")
    for claim in ("forall x. mortal(x)", "exists y. open(y)", "(socrates_is_mortal"):
        payload = copy.deepcopy(base)
        payload["claim"] = claim
        response = authority.run_authority(payload)
        assert response["status"] == "refused", claim
        assert response["decision"] is None, claim
        assert response["decision_reason"] == "out_of_regime_or_malformed", claim


def test_atom_budget_refuses_before_either_procedure_runs():
    """The demo's explicit regime bound: a payload exceeding the distinct-atom
    budget refuses before the engine or the brute-force oracle is invoked
    (the oracle is O(2^atoms) by design; the authority honors its small-atom
    contract instead of churning)."""
    atoms = [f"atom_{i:02d}" for i in range(authority.MAX_DISTINCT_ATOMS + 1)]
    payload = _arguments("entailed-modus-ponens")
    payload["premises"] = [" | ".join(atoms[:7]), " | ".join(atoms[7:])]
    payload["claim"] = atoms[0]
    response = authority.run_authority(payload)
    assert response["status"] == "refused"
    assert response["decision"] is None
    assert response["decision_reason"] == "out_of_regime_or_malformed"
    assert response["trace_summary"]["regime_gate"] == "distinct_atom_budget"
    # Neither procedure ran: no engine trace, no oracle verdict, and the
    # authority path stops at the demo-local gate.
    assert response["entailment_trace"] is None
    assert response["oracle_verdict"] is None
    assert response["authority_path"] == [
        "demos.deductive_entailment_authority.authority.validate_payload",
        "demos.deductive_entailment_authority.authority.enforce_atom_budget",
    ]


# ---------------------------------------------------------------------------
# Proposer attachments are data, never authority
# ---------------------------------------------------------------------------

_DECISION_FIELDS = (
    "status",
    "decision",
    "decision_reason",
    "entailment_trace",
    "oracle_verdict",
    "oracle_agreement",
    "engine_pin",
    "refusal_reason",
)


def test_proposer_garbage_is_recorded_and_decision_invariant():
    adorned = _run("proposer-wrong-refuted")
    assert adorned["proposer_ignored_fields"] == [
        "confidence",
        "engine_pin",
        "proof",
        "trace_hash",
        "verdict",
    ]

    bare_payload = _arguments("proposer-wrong-refuted")
    proposer = dict(bare_payload["proposer"])
    for field in ("verdict", "confidence", "proof", "trace_hash", "engine_pin"):
        proposer.pop(field, None)
    bare_payload["proposer"] = proposer
    bare = authority.run_authority(bare_payload)

    for field in _DECISION_FIELDS:
        assert bare[field] == adorned[field], field
    assert bare["proposer_ignored_fields"] == []


def test_proposer_garbage_cannot_rescue_decision_on_entailed_setup_either():
    """Garbage on an ENTAILED setup changes nothing either: same decision,
    same engine trace, byte-identical decision-bearing fields."""
    payload = _arguments("entailed-modus-ponens")
    proposer = dict(payload["proposer"])
    proposer["verdict"] = "refuted"
    proposer["confidence"] = "1.0"
    proposer["proof"] = "this claim is impossible"
    payload["proposer"] = proposer
    adorned = authority.run_authority(payload)
    bare = _run("entailed-modus-ponens")
    for field in _DECISION_FIELDS:
        assert bare[field] == adorned[field], field
    assert adorned["decision"] == "entailed"
    assert adorned["proposer_ignored_fields"] == ["confidence", "proof", "verdict"]


# ---------------------------------------------------------------------------
# Oracle disagreement — test-only fault injection, defensive refusal
# ---------------------------------------------------------------------------

def test_oracle_disagreement_defensively_refuses(monkeypatch):
    """If the independent oracle ever failed to confirm the engine, CORE
    must refuse rather than serve a one-procedure decision.  This cannot
    happen inside the supported regime (both procedures are sound), so it is
    exercised by fault injection — NOT by a committed fixture."""
    payload = _arguments("proposer-wrong-unknown")  # engine computes `unknown`

    monkeypatch.setattr(authority, "oracle_entailment", lambda premises, query: "entailed")
    disagree = authority.run_authority(payload)
    assert disagree["status"] == "refused"
    assert disagree["decision"] is None
    assert disagree["decision_reason"] == "oracle_disagreement"
    assert disagree["refusal_reason"] == "oracle_disagreement"
    assert disagree["oracle_agreement"] is False
    assert disagree["trace_summary"]["defensive_refusal"] is True

    # An oracle REFUSAL against an engine decision is likewise never served.
    monkeypatch.setattr(authority, "oracle_entailment", lambda premises, query: "refused")
    refuse = authority.run_authority(payload)
    assert refuse["status"] == "refused"
    assert refuse["decision_reason"] == "oracle_disagreement"


def test_oracle_module_is_disjoint_from_core_proof_chain():
    """INV-25 posture, pinned at the demo boundary: the oracle is a second,
    independent decision procedure.  Its imports are stdlib-only — nothing
    from generate (the engine/canonicalizer), demos, or any CORE package."""
    from tests.test_architectural_invariants import (
        _imports_any_prefix,
        _module_imports,
    )

    mods = _module_imports(ORACLE_PATH)
    forbidden = _imports_any_prefix(
        mods,
        ("generate", "demos", "core", "vault", "teaching", "chat", "evals.lab"),
    )
    assert forbidden == [], f"oracle imports CORE code: {forbidden}"
    assert mods <= {"__future__", "itertools", "typing"}, mods


def test_demo_uses_the_real_engine_and_the_real_oracle():
    """The authority imports BOTH real procedures and reimplements neither —
    and it does not reach around the engine API into the canonicalizer."""
    tree = ast.parse((DEMO_DIR / "authority.py").read_text(encoding="utf-8"))
    from_imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "generate.proof_chain.entail" in from_imports
    assert "generate.proof_chain.engine_pin" in from_imports
    assert "evals.deductive_logic.oracle" in from_imports
    assert "generate.logic_canonical" not in from_imports
    defined = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert "evaluate_entailment_with_trace" not in defined
    assert "oracle_entailment" not in defined
    assert "canonicalize" not in defined


# ---------------------------------------------------------------------------
# Invalid payloads fail closed before evaluation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "forged_key",
    [
        "status",
        "decision",
        "trace_hash",
        "authority_path",
        "oracle_verdict",
        "oracle_agreement",
        "engine_pin",
        "entailment_trace",
        "evidence_ledger",
    ],
)
def test_output_smuggling_rejected_before_evaluation(forged_key, monkeypatch):
    def _explode(_payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError("entailment evaluation ran for an invalid payload")

    monkeypatch.setattr(authority, "evaluate_decision", _explode)
    payload = _arguments("entailed-modus-ponens")
    payload[forged_key] = "entailed"
    response = authority.run_authority(payload)
    assert response["status"] == "invalid"
    assert response["decision"] is None
    assert response["engine_pin"] is None
    assert response["trace_summary"]["authority_evaluated"] is False
    assert f"unexpected property '{forged_key}'" in response["invalid_reason"]


def test_unknown_proposer_keys_and_bad_shapes_are_invalid():
    smuggled = _arguments("entailed-modus-ponens")
    smuggled["proposer"] = dict(smuggled["proposer"], certainty="absolute")
    response = authority.run_authority(smuggled)
    assert response["status"] == "invalid"
    assert "unexpected property 'certainty'" in response["invalid_reason"]

    empty = _arguments("entailed-modus-ponens")
    empty["premises"] = []
    response = authority.run_authority(empty)
    assert response["status"] == "invalid"
    assert "fewer than 1 items" in response["invalid_reason"]

    oversized = _arguments("entailed-modus-ponens")
    oversized["premises"] = ["p"] * 9
    response = authority.run_authority(oversized)
    assert response["status"] == "invalid"
    assert "more than 8 items" in response["invalid_reason"]

    non_string = _arguments("entailed-modus-ponens")
    non_string["premises"] = ["p", 7]
    response = authority.run_authority(non_string)
    assert response["status"] == "invalid"


# ---------------------------------------------------------------------------
# Trace integrity
# ---------------------------------------------------------------------------

def _recomputed_trace_hash(response: dict[str, object]) -> str:
    body = {key: value for key, value in response.items() if key != "trace_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_trace_hash_recomputes_and_folds_trace_and_oracle_verdict():
    response = _run("entailed-modus-ponens")
    assert response["trace_hash"] == _recomputed_trace_hash(response)

    forged_oracle = copy.deepcopy(response)
    forged_oracle["oracle_verdict"] = "refuted"
    assert _recomputed_trace_hash(forged_oracle) != response["trace_hash"]

    forged_trace = copy.deepcopy(response)
    forged_trace["entailment_trace"]["conjunction_key"] = "tampered"
    assert _recomputed_trace_hash(forged_trace) != response["trace_hash"]


def test_entailment_trace_is_the_engine_evidence_replayed():
    """The embedded trace IS the engine's canonical evidence: recomputing
    from the fixture's formulas reproduces it byte-for-byte."""
    from generate.proof_chain.entail import evaluate_entailment_with_trace

    payload = _arguments("entailed-modus-ponens")
    response = _run("entailed-modus-ponens")
    recomputed = evaluate_entailment_with_trace(
        tuple(payload["premises"]), payload["claim"]
    )
    assert response["entailment_trace"] == json.loads(recomputed.canonical_json())


def test_engine_pin_is_the_pinned_deductive_lane_sha():
    """deductive_logic_v1 pin unchanged — the engine identity in every
    artifact is the lane SHA (registry sync is pinned by
    test_adr_0218_proof_promotion.py::test_engine_pin_matches_lane_registry)."""
    assert DEDUCTIVE_ENGINE_PIN == (
        "97a230949016e38d5e3f37a69e4245b320575ee70e5af92ff7607f7b05f74b5f"
    )
    response = _run("entailed-modus-ponens")
    assert response["engine_pin"] == DEDUCTIVE_ENGINE_PIN


# ---------------------------------------------------------------------------
# Runner hardening
# ---------------------------------------------------------------------------

def test_run_demo_all_passes_against_expected(tmp_path, monkeypatch):
    out_dir = tmp_path / "demo-out"
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", str(out_dir)])
    assert demo_runner.main() == 0


def test_run_demo_default_out_still_works(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_demo.py"])
    assert demo_runner.main() == 0


def test_expected_artifact_tampering_fails(tmp_path):
    scenario_id = "entailed-modus-ponens"
    ref = EXPECTED_DIR / f"{scenario_id}.json"
    original = ref.read_text(encoding="utf-8")
    try:
        ref.write_text(original.replace("entailed", "refuted", 1), encoding="utf-8")
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr("sys.argv", ["run_demo.py", "--out", str(tmp_path / "out")])
            assert demo_runner.main() == 1
    finally:
        ref.write_text(original, encoding="utf-8")


def test_run_demo_refuses_non_default_dir_without_marker(tmp_path, monkeypatch):
    out_dir = tmp_path / "missing-marker"
    out_dir.mkdir()
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", str(out_dir)])
    assert demo_runner.main() == 2


@pytest.mark.parametrize("target", [".", ".."])
def test_run_demo_refuses_parent_like_paths(target: str, monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_demo.py", "--out", target])
    assert demo_runner.main() == 2


# ---------------------------------------------------------------------------
# Structural discipline — no parallel path, no forbidden calls, INVs intact
# ---------------------------------------------------------------------------

_DEMO_SOURCES = [
    DEMO_DIR / "__init__.py",
    DEMO_DIR / "authority.py",
    DEMO_DIR / "run_demo.py",
]


def test_no_network_subprocess_eval_or_exec_imports_or_calls():
    forbidden_imports = {
        "subprocess", "socket", "requests", "httpx", "urllib", "urllib.request",
        "http", "http.client", "uuid", "random", "secrets", "time", "datetime",
        "os",
    }
    forbidden_calls = {
        "eval", "exec", "compile", "open_connection", "create_connection",
        "Popen", "system",
    }
    for path in _DEMO_SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden_imports, path.name
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "") not in forbidden_imports, path.name
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    assert node.func.id not in forbidden_calls, path.name
                elif isinstance(node.func, ast.Attribute):
                    assert node.func.attr not in forbidden_calls, path.name


def test_demo_adds_no_vault_writer_no_status_transition_no_recall():
    """demos/ is scanned by INV-21/INV-24/INV-29 — prove the demo files are
    clean with the invariants' own detectors."""
    from tests.test_architectural_invariants import (
        _file_has_vault_recall_call,
        _file_has_vault_store_call,
        _status_transition_writes,
    )

    for path in _DEMO_SOURCES:
        assert _file_has_vault_store_call(path) is False, path.name
        assert _file_has_vault_recall_call(path) is False, path.name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert _status_transition_writes(tree) == 0, path.name


def test_inv21_and_inv29_allowlists_are_unchanged():
    from tests.test_architectural_invariants import (
        ALLOWED_STATUS_TRANSITION_SITES,
        ALLOWED_VAULT_WRITERS,
    )

    assert ALLOWED_VAULT_WRITERS == frozenset({
        "session/context.py",
        "vault/store.py",
        "generate/proposition.py",
        "generate/realize/realize.py",
    })
    assert ALLOWED_STATUS_TRANSITION_SITES == frozenset({"vault/store.py"})


def test_no_private_strategy_or_named_company_terms():
    forbidden_terms = (
        "outreach", "investor", "xai", "tesla", "anthropic", "openai",
        "deepmind", "partnership",
    )
    scanned = sorted(
        list(DEMO_DIR.glob("*.py"))
        + list(DEMO_DIR.glob("*.md"))
        + list(DEMO_DIR.glob("*.json"))
        + list(FIXTURES_DIR.glob("*.json"))
        + list(EXPECTED_DIR.glob("*.json"))
    )
    assert scanned, "demo files missing — scan would be vacuous"
    for path in scanned:
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in text, f"{path.name} contains {term!r}"
