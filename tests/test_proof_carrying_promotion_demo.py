"""ADR-0218 PR D — proof-carrying coherence promotion demo.

Proves the demo envelope end-to-end: closed schema, pinned expected
artifacts, double-run determinism, proposer-garbage immunity, vault-owned
mutation only, and the INV-21/INV-29 discipline of the demo files themselves
(demos/ is scanned by both invariants — the demo must add no vault writer
and no status-transition site).
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from demos.proof_carrying_promotion import authority
from demos.proof_carrying_promotion import run_demo as demo_runner
from generate.proof_chain.engine_pin import DEDUCTIVE_ENGINE_PIN

DEMO_DIR = Path(authority.__file__).resolve().parent
FIXTURES_DIR = DEMO_DIR / "fixtures"
EXPECTED_DIR = DEMO_DIR / "expected"
REPO_ROOT = DEMO_DIR.parents[1]

SCENARIOS = {
    "entailed-promotes": ("promoted", "promoted_entailed_from_coherent_premises"),
    "proposer-status-ignored": ("refused", "refused_not_entailed"),
    "non-coherent-premise-refuses": ("refused", "refused_premise_not_coherent"),
    "uncertified-reading-refuses": ("refused", "refused_premise_reading_uncertified"),
    "tampered-certificate-refuses": ("refused", "certificate_replay_failed"),
    "stale-premise-status-refuses": ("refused", "premise_not_coherent"),
    "non-sequitur-refuses": ("refused", "refused_not_entailed"),
    "invalid-state-smuggling-attempt": ("invalid", "invalid_payload"),
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


def test_all_scenarios_match_status_and_reason():
    for name, (status, reason) in SCENARIOS.items():
        response = _run(name)
        assert response["status"] == status, name
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
# Promotion semantics inside the envelope
# ---------------------------------------------------------------------------

def test_entailed_promotes_only_through_the_vault_owner():
    response = _run("entailed-promotes")
    assert response["promoted"] is True
    assert response["before_status"] == "speculative"
    assert response["after_status"] == "coherent"
    assert response["engine_pin"] == DEDUCTIVE_ENGINE_PIN
    assert response["trace_summary"]["apply_reason"] == "applied"
    # The authority path names the real decider, the real owner, and replay.
    assert "teaching.proof_promotion.certify_promotion" in response["authority_path"]
    assert (
        "vault.store.VaultStore.apply_certified_promotion"
        in response["authority_path"]
    )


def test_refused_scenarios_mutate_nothing():
    for name, (status, _) in SCENARIOS.items():
        if status != "refused":
            continue
        response = _run(name)
        assert response["promoted"] is False, name
        assert response["before_status"] == "speculative", name
        assert response["after_status"] == "speculative", name


def test_refuted_does_not_demote_in_demo_envelope():
    """A refuted claim stays SPECULATIVE — no demotion authority exists."""
    payload = _arguments("entailed-promotes")
    payload["store"]["entries"][1]["propositional_form"] = "p -> ~q"
    response = authority.run_authority(payload)
    assert response["status"] == "refused"
    assert response["trace_summary"]["engine_decision"] == "refuted"
    assert response["after_status"] == "speculative"


def test_stale_refusal_uses_the_same_honest_certificate():
    """Staleness is a LIVE-state refusal: the certificate (and digest) is the
    same honest artifact the entailed scenario promotes with."""
    promoted = _run("entailed-promotes")
    stale = _run("stale-premise-status-refuses")
    assert stale["certificate_digest"] == promoted["certificate_digest"]
    assert stale["promoted"] is False
    assert stale["trace_summary"]["apply_reason"] == "premise_not_coherent"


def test_tampered_certificate_digest_differs_from_honest_one():
    response = _run("tampered-certificate-refuses")
    assert response["trace_summary"]["certify_promoted"] is True
    assert (
        response["certificate_digest"]
        != response["trace_summary"]["certify_certificate_digest"]
    )
    assert response["trace_summary"]["apply_reason"] == "certificate_replay_failed"


# ---------------------------------------------------------------------------
# Proposer attachments are data, never authority
# ---------------------------------------------------------------------------

def test_proposer_garbage_is_recorded_and_decision_invariant():
    adorned = _run("proposer-status-ignored")
    assert adorned["proposer_ignored_fields"] == [
        "certificate",
        "confidence",
        "proof",
        "status",
        "trace_hash",
    ]

    bare_payload = _arguments("proposer-status-ignored")
    proposer = dict(bare_payload["proposer"])
    for field in ("proof", "status", "confidence", "certificate", "trace_hash"):
        proposer.pop(field, None)
    bare_payload["proposer"] = proposer
    bare = authority.run_authority(bare_payload)

    # The decision-bearing fields are identical with and without the garbage;
    # the certificate digest in particular proves the proof evidence cannot
    # depend on anything the proposer attached.
    for field in (
        "status",
        "promoted",
        "decision_reason",
        "certificate_digest",
        "before_status",
        "after_status",
    ):
        assert bare[field] == adorned[field], field
    assert bare["proposer_ignored_fields"] == []


def test_proposer_garbage_cannot_rescue_promotion_on_entailed_setup_either():
    """Garbage on a PROMOTABLE setup changes nothing: same digest, same flip."""
    payload = _arguments("entailed-promotes")
    proposer = dict(payload["proposer"])
    proposer.pop("proof", None)
    proposer.pop("status", None)
    proposer.pop("confidence", None)
    payload["proposer"] = proposer
    bare = authority.run_authority(payload)
    adorned = _run("entailed-promotes")
    assert bare["promoted"] is adorned["promoted"] is True
    assert bare["certificate_digest"] == adorned["certificate_digest"]


# ---------------------------------------------------------------------------
# Invalid payloads fail closed before evaluation
# ---------------------------------------------------------------------------

def test_invalid_smuggling_rejected_before_evaluation(monkeypatch):
    def _explode(_payload: dict[str, object]) -> dict[str, object]:
        raise AssertionError("promotion evaluation ran for an invalid payload")

    monkeypatch.setattr(authority, "evaluate_promotion", _explode)
    response = _run("invalid-state-smuggling-attempt")
    assert response["status"] == "invalid"
    assert response["promoted"] is False
    assert response["certificate_digest"] is None
    assert response["engine_pin"] is None
    assert response["trace_summary"]["authority_evaluated"] is False
    for forged in (
        "promoted",
        "final_status",
        "authority_path",
        "certificate_digest",
        "trace_hash",
        "evidence_ledger",
    ):
        assert f"unexpected property '{forged}'" in response["invalid_reason"]


def test_proposer_cannot_set_output_fields_at_root():
    payload = _arguments("entailed-promotes")
    payload["after_status"] = "coherent"
    response = authority.run_authority(payload)
    assert response["status"] == "invalid"
    assert "unexpected property 'after_status'" in response["invalid_reason"]


def test_unknown_and_duplicate_store_entries_refuse():
    payload = _arguments("entailed-promotes")
    payload["store"]["claim_entry"] = "no-such-entry"
    response = authority.run_authority(payload)
    assert response["status"] == "refused"
    assert response["decision_reason"] == "unknown_store_entry"
    assert response["certificate_digest"] is None

    duplicated = _arguments("entailed-promotes")
    entries = duplicated["store"]["entries"]
    entries.append(dict(entries[0]))
    response = authority.run_authority(duplicated)
    assert response["status"] == "refused"
    assert response["decision_reason"] == "duplicate_store_entry_ids"


# ---------------------------------------------------------------------------
# Trace integrity
# ---------------------------------------------------------------------------

def _recomputed_trace_hash(response: dict[str, object]) -> str:
    body = {key: value for key, value in response.items() if key != "trace_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_trace_hash_recomputes_and_folds_certificate_digest():
    response = _run("entailed-promotes")
    assert response["trace_hash"] == _recomputed_trace_hash(response)
    # The certificate digest is inside the hashed body: flipping it must
    # change the recomputed trace hash (D4 folding).
    forged = dict(response)
    forged["certificate_digest"] = "0" * 64
    assert _recomputed_trace_hash(forged) != response["trace_hash"]


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
    scenario_id = "entailed-promotes"
    ref = EXPECTED_DIR / f"{scenario_id}.json"
    original = ref.read_text(encoding="utf-8")
    try:
        ref.write_text(original.replace("coherent", "contested", 1), encoding="utf-8")
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


def test_demo_uses_the_real_promoter_not_a_reimplementation():
    """The decider import is teaching.proof_promotion and no demo function
    redefines certify/apply names — no parallel promotion logic."""
    tree = ast.parse((DEMO_DIR / "authority.py").read_text(encoding="utf-8"))
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert "teaching" in imports or any(
        module.startswith("teaching") for module in imports
    )
    defined = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert "certify_promotion" not in defined
    assert "apply_certified_promotion" not in defined
