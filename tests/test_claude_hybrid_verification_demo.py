"""No-bypass proof obligations for the Claude-to-CORE hybrid verification demo.

The demo's claim is a *boundary* claim — a Claude/Fable-style System 1 proposer
gets no execution authority over CORE's System 2 — so every test here is written
to fail if exactly one bypass were silently introduced (the schema-defined
proof-obligation discipline from CLAUDE.md):

* the typed boundary rejects answer/handle/directive smuggling, and an invalid
  payload executes **no** derivation;
* ``verified`` can only come from a live pool commit that survives the commit-law
  and faithfulness audits AND the committed gold-audited envelope pin — a forged
  commit, an out-of-envelope commit, and a pinned-reference mismatch all refuse;
* the ASK leg serves only a producer-written, content-hash-verified question
  artifact, stays dark under the default gate, and fails closed on tampering;
* responses are deterministic and byte-match the committed expected artifacts;
* structurally, the demo modules import nothing from ``generate.*`` (or any
  other commit surface) — proven by an AST scan with a predicate self-test.
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from demos.claude_hybrid_verification import run_demo as demo_runner
from demos.claude_hybrid_verification import verify_tool
from demos.claude_hybrid_verification.schema import load_tool_schema, validate_payload
from demos.claude_hybrid_verification.verify_tool import (
    DemoAskServingConfig,
    TOOL_NAME,
    run_tool,
)

DEMO_DIR = Path(verify_tool.__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parents[1]

SARA = (
    "Sara has 32 dollars. Sara earns 15 dollars. She uses 21 dollars. "
    "How many dollars does Sara have left?"
)
BUS = (
    "Each large bus holds 50 students and each small bus holds 30 students. "
    "The buses carry 260 students in total. How many large buses are there?"
)
JACK = "Jack has 17 toy cars. His dad buys him 8 more. How many toy cars does Jack have?"


def _args(text: str, **extra: object) -> dict[str, object]:
    return {"problem_text": text, **extra}


# --------------------------------------------------------------------------- #
# 1. The typed boundary
# --------------------------------------------------------------------------- #


def test_input_schema_is_a_closed_no_smuggling_object():
    """The committed schema itself must be the no-smuggling contract: a closed
    object whose only required seat is the problem text, with no seat that could
    carry an answer, a derivation, a handle, or an acceptance decision."""
    schema = load_tool_schema()["inputSchema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["problem_text"]
    assert set(schema["properties"]) == {
        "problem_text",
        "domain_hint",
        "request_id",
        "return_trace",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"problem_text": "x", "proposed_answer": 42},
        {"problem_text": "x", "answer": 42},
        {"problem_text": "x", "derivation": {"steps": []}},
        {"problem_text": "x", "handle": {"question_path": "/tmp/q.json"}},
        {"problem_text": "x", "status": "verified"},
        {"problem_text": "x", "confidence": "high"},
    ],
)
def test_smuggling_payloads_are_rejected(payload, tmp_path):
    assert validate_payload(payload)
    response = run_tool(payload, out_dir=tmp_path)
    assert response["status"] == "invalid"
    assert response["answer"] is None
    assert response["trace"] is None


@pytest.mark.parametrize(
    "payload",
    [
        "not an object",
        {},
        {"problem_text": ""},
        {"problem_text": "x" * 2001},
        {"problem_text": 42},
        {"problem_text": "x", "domain_hint": "general_web"},
        {"problem_text": "x", "request_id": "bad id with spaces"},
        {"problem_text": "x", "return_trace": "yes"},
    ],
)
def test_malformed_payloads_are_rejected(payload):
    assert validate_payload(payload)


def test_invalid_path_does_not_reflect_untrusted_request_id(tmp_path):
    """The invalid path echoes request_id only when it satisfies the schema
    pattern — arbitrary caller text must not round-trip into the response."""
    hostile = {"problem_text": "x", "answer": 1, "request_id": "x" * 5000 + "\n<script>"}
    response = run_tool(hostile, out_dir=tmp_path)
    assert response["status"] == "invalid"
    assert response["request_id"] is None

    clean = {"problem_text": "x", "answer": 1, "request_id": "ok-id-1"}
    assert run_tool(clean, out_dir=tmp_path)["request_id"] == "ok-id-1"


def test_invalid_payload_executes_no_derivation(monkeypatch, tmp_path):
    """Fail-fast at the boundary: a rejected payload must never reach the engine."""

    def _explode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("derivation executed for an invalid payload")

    monkeypatch.setattr(verify_tool, "problem_trace", _explode)
    response = run_tool({"problem_text": "x", "answer": 1}, out_dir=tmp_path)
    assert response["status"] == "invalid"


# --------------------------------------------------------------------------- #
# 2. Verifier/pool/envelope authority over "verified"
# --------------------------------------------------------------------------- #


def test_pool_refusal_can_never_be_verified(monkeypatch, tmp_path):
    """If the pool refuses, no demo logic may mint an answer — even on a problem
    the envelope authorizes."""
    import evals.gsm8k_math.equivalence.trace as trace_module

    monkeypatch.setattr(trace_module, "resolve_pooled", lambda _text: None)
    response = run_tool(_args(SARA), out_dir=tmp_path)
    assert response["status"] != "verified"
    assert response["answer"] is None


def test_forged_pool_commit_is_caught_by_the_commit_law(monkeypatch, tmp_path):
    """A tampered authority is detectable from the trace itself: a forged
    resolution that disagrees with the classified candidates trips
    ``authority_violations`` and the demo refuses rather than serves."""
    import evals.gsm8k_math.equivalence.trace as trace_module

    real = trace_module.resolve_pooled(SARA)
    assert real is not None, "fixture drift: the Sara problem must pool-commit"
    forged = dataclasses.replace(real, answer=999.0)
    monkeypatch.setattr(trace_module, "resolve_pooled", lambda _text: forged)

    response = run_tool(_args(SARA), out_dir=tmp_path)
    assert response["status"] == "refused"
    assert response["refusal_reason"] == "authority_violation_detected"
    assert response["answer"] is None


def test_pool_commit_outside_envelope_is_refused(tmp_path):
    """The doctrine scenario: the pool commits (and the answer even matches lane
    gold), but the demo refuses because no audited envelope entry licenses it."""
    response = run_tool(_args(JACK), out_dir=tmp_path)
    assert response["status"] == "refused"
    assert response["refusal_reason"] == "outside_demo_serving_envelope"
    assert response["trace_summary"]["pool_committed"] is True
    assert response["answer"] is None


def test_envelope_pinned_reference_mismatch_is_refused(monkeypatch, tmp_path):
    """An envelope entry whose pinned trace does not byte-match the live
    derivation must not serve — the pin is an authorization, not a decoration."""
    envelope = json.loads(json.dumps(verify_tool._envelope()))  # deep copy
    for entry in envelope["entries"].values():
        entry["derivation_trace_sha"] = "0" * 64
    monkeypatch.setattr(verify_tool, "_envelope", lambda: envelope)

    response = run_tool(_args(SARA), out_dir=tmp_path)
    assert response["status"] == "refused"
    assert response["refusal_reason"] == "replay_drift_from_pinned_reference"


#: The only lanes an envelope entry may cite as its gold source — a canonical,
#: committed gold corpus, so the audit's reference cannot be a file the entry
#: author invented.
_CANONICAL_GOLD_LANES = frozenset(
    {
        "evals/gsm8k_math/public/v1/cases.jsonl",
        "evals/gsm8k_math/dev/cases.jsonl",
        "evals/gsm8k_math/holdout_dev/v1/cases.jsonl",
        "evals/gsm8k_math/train_sample/v1/cases.jsonl",
        "evals/gsm8k_math/practice/v1/cases.jsonl",
    }
)


def test_every_envelope_entry_is_gold_audited_and_reproducible():
    """Re-audit the committed envelope: every entry must (a) cite a canonical
    gold lane, (b) name a real case there whose gold matches the pinned answer,
    and (c) be reproduced bit-exactly by a live derivation run (sha, answer,
    unit)."""
    import evals.gsm8k_math.equivalence.trace as trace_module

    envelope = json.loads(verify_tool.ENVELOPE_PATH.read_text(encoding="utf-8"))
    assert envelope["entries"], "an empty envelope makes the verified leg dead"
    for problem_sha, entry in envelope["entries"].items():
        gold = entry["gold"]
        assert gold["lane"] in _CANONICAL_GOLD_LANES, gold["lane"]
        lane_path = REPO_ROOT / gold["lane"]
        case = next(
            (
                json.loads(line)
                for line in lane_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
                and json.loads(line).get("id", json.loads(line).get("case_id"))
                == gold["case_id"]
            ),
            None,
        )
        assert case is not None, f"{gold['case_id']} not found in {gold['lane']}"
        text = case.get("problem") or case.get("question")
        assert hashlib.sha256(text.encode()).hexdigest() == problem_sha
        lane_gold = float(case.get("expected_answer", case.get("answer_numeric")))
        assert abs(lane_gold - float(entry["answer"])) < 1e-9
        assert abs(float(gold["expected_answer"]) - float(entry["answer"])) < 1e-9

        live = trace_module.problem_trace(text)
        live_sha = hashlib.sha256(trace_module.trace_line(live).encode()).hexdigest()
        assert live_sha == entry["derivation_trace_sha"]
        assert live["resolution"] is not None
        assert abs(float(live["resolution"]["answer"]) - float(entry["answer"])) < 1e-9
        assert live["resolution"]["answer_unit"] == entry["answer_unit"]


# --------------------------------------------------------------------------- #
# 3. The ASK leg
# --------------------------------------------------------------------------- #


def test_ask_serves_a_producer_written_content_addressed_question(tmp_path):
    response = run_tool(_args(BUS), out_dir=tmp_path)
    assert response["status"] == "ask"
    ask = response["trace"]["ask"]
    assert ask["detail"] == "served"
    assert ask["blocking_reason"] == "missing_total_count"

    artifact = tmp_path / ask["question_ref"]
    assert artifact.is_file()
    body = json.loads(artifact.read_text(encoding="utf-8"))
    # The served text is the artifact's text, verbatim — never demo-authored.
    assert response["question"] == body["question"]["text"]
    assert response["surface"] == body["question"]["text"]
    # The artifact re-hashes to its own content address (the handle-seam law).
    digest = hashlib.sha256(
        f"{body['blocking_reason']}:{body['question']['slot_name']}:"
        f"{body['question']['text']}".encode("utf-8")
    ).hexdigest()
    assert digest == ask["content_hash"] == artifact.stem


def test_ask_gate_is_dark_by_default_and_side_effect_free(tmp_path):
    """With the repo-default (dark) gate the demo must refuse, perform no organ
    calls, write nothing, and name no ASK authority — mirroring the seam's
    gate-first law."""
    response = run_tool(
        _args(BUS), out_dir=tmp_path, ask_config=DemoAskServingConfig(False)
    )
    assert response["status"] == "refused"
    assert response["trace"]["ask"]["detail"] == "gate_disabled"
    assert not (tmp_path / "questions").exists()
    assert not _ask_tokens(response)


def _ask_tokens(response) -> list[str]:
    return [
        token
        for token in response["authority_path"]
        if token.startswith(("core.comprehension_attempt", "core.epistemic"))
    ]


def test_authority_path_names_only_consulted_ask_authorities(tmp_path):
    """The honesty contract on ``authority_path``: the ASK suffix is exactly the
    pipeline prefix that ran.  A refusal with no ask-mapped organ names only the
    router and the limitation gate; a served ask names the full six-stage chain;
    an unrenderable ask stops at the producer."""
    # No ask-mapped attempt (Sara is a pool *commit*; use a refusal: Tom's cat).
    tom = (
        "Tom’s cat is 8 years old.  His rabbit is half the age of his cat.  "
        "His dog is three times as old as his rabbit.  How old is the dog?"
    )
    refused = run_tool(_args(tom), out_dir=tmp_path / "a")
    assert refused["trace"]["ask"]["detail"] == "no_ask_mapped_attempt"
    assert _ask_tokens(refused) == [
        "core.comprehension_attempt.router.route_setup",
        "core.epistemic_disclosure.limitation.assess_from_attempt",
    ]
    # Served ask: the full chain.
    served = run_tool(_args(BUS), out_dir=tmp_path / "b")
    assert served["trace"]["ask"]["detail"] == "served"
    assert len(_ask_tokens(served)) == 6


def test_unrenderable_ask_falls_back_to_refusal(monkeypatch, tmp_path):
    """The D2 guard, demo-side: if the producer declines to render, the demo
    stays refused with the pool's reason and names no serving authority."""
    monkeypatch.setattr(verify_tool, "emit_question", lambda *_a, **_k: None)
    response = run_tool(_args(BUS), out_dir=tmp_path)
    assert response["status"] == "refused"
    assert response["question"] is None
    assert response["trace"]["ask"]["detail"] == "question_unrenderable_fell_back"
    assert len(_ask_tokens(response)) == 3


def test_multiple_ask_mapped_attempts_refuse_rather_than_pick(monkeypatch, tmp_path):
    """Fail-closed plumbing: if more than one organ maps to ask_question, the
    demo refuses to choose a 'best question' and stays refused."""
    from types import SimpleNamespace

    monkeypatch.setattr(
        verify_tool,
        "assess_from_attempt",
        lambda attempt: SimpleNamespace(
            resolution_action="ask_question",
            blocking_reason="missing_total_count",
            owner_organ=attempt.organ,
        ),
    )
    response = run_tool(_args(BUS), out_dir=tmp_path)
    assert response["status"] == "refused"
    assert response["trace"]["ask"]["detail"] == "multiple_ask_mapped_attempts"
    assert len(_ask_tokens(response)) == 2


def test_tampered_question_artifact_fails_closed(monkeypatch, tmp_path):
    """An artifact whose body does not re-hash to its content address must never
    be served: the carried-handle seam rejects it and the demo stays refused."""
    real_emit = verify_tool.emit_question

    def _tampering_emit(assessment, *, root):
        path = real_emit(assessment, root=root)
        assert path is not None
        body = json.loads(path.read_text(encoding="utf-8"))
        body["question"]["text"] = "What is your favorite color?"
        path.write_text(json.dumps(body, indent=2, sort_keys=True), encoding="utf-8")
        return path

    monkeypatch.setattr(verify_tool, "emit_question", _tampering_emit)
    response = run_tool(_args(BUS), out_dir=tmp_path)
    assert response["status"] == "refused"
    assert response["question"] is None
    assert (
        response["trace"]["ask"]["detail"] == "handle_not_resolved:content_hash_mismatch"
    )


# --------------------------------------------------------------------------- #
# 4. Determinism and the committed pins
# --------------------------------------------------------------------------- #


def test_double_run_is_byte_identical(tmp_path):
    first = run_tool(_args(BUS, request_id="det-1"), out_dir=tmp_path / "a")
    second = run_tool(_args(BUS, request_id="det-1"), out_dir=tmp_path / "b")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_trace_hash_is_stable_across_trace_suppression(tmp_path):
    """``trace_hash`` always covers the full trace envelope, so suppressing the
    trace body cannot change (or hide) what the hash attests to."""
    with_trace = run_tool(_args(SARA, return_trace=True), out_dir=tmp_path / "a")
    without = run_tool(_args(SARA, return_trace=False), out_dir=tmp_path / "b")
    assert without["trace"] is None
    assert with_trace["trace"] is not None
    assert with_trace["trace_hash"] == without["trace_hash"]


def test_committed_expected_artifacts_are_current(tmp_path):
    """The demo-local replay pin: every committed scenario artifact must be
    reproduced byte-for-byte by a live run, and carry the scenario's expected
    status.  A change here requires a reviewed --update-expected diff."""
    scenarios = demo_runner.load_scenarios()
    assert {s["scenario_id"] for s in scenarios} == {
        "s1-verified-grounded-chain",
        "s2-refused-disagreement",
        "s3-ask-missing-total",
        "s4-refused-outside-envelope",
        "s5-invalid-answer-smuggling",
    }
    for scenario in scenarios:
        response = demo_runner.run_scenario(scenario, tmp_path / scenario["scenario_id"])
        assert response["status"] == scenario["expected_status"], scenario["scenario_id"]
        committed = demo_runner.expected_path(scenario["scenario_id"])
        assert committed.is_file(), f"missing pinned artifact for {scenario['scenario_id']}"
        assert demo_runner.render_artifact(response) == committed.read_text(
            encoding="utf-8"
        ), f"{scenario['scenario_id']} drifted from its pinned artifact"


def test_status_is_coherent_with_pool_resolution(tmp_path):
    """The asymmetry that keeps reason-labeling harmless: ``verified`` requires a
    live pool resolution + envelope authorization; everything else must carry no
    answer.  Checked over every committed scenario."""
    for scenario in demo_runner.load_scenarios():
        arguments = scenario["system1"]["tool_call"]["arguments"]
        response = run_tool(arguments, out_dir=tmp_path / scenario["scenario_id"])
        if response["status"] == "verified":
            assert response["trace"]["derivation"]["resolution"] is not None
            assert response["trace_summary"]["demo_envelope"] == "authorized"
            assert response["trace_summary"]["commit_law_violations"] == 0
            assert response["trace_summary"]["faithfulness_violations"] == 0
        else:
            assert response["answer"] is None
            assert response["answer_unit"] is None


# --------------------------------------------------------------------------- #
# 5. Structural no-bypass (with predicate self-test)
# --------------------------------------------------------------------------- #

_DEMO_MODULES = ("schema.py", "verify_tool.py", "run_demo.py", "__init__.py")

#: Exactly the first-party modules each demo file may import.  ``generate.*`` is
#: absent on purpose: the derivation lane is reachable only through the audited
#: ADR-0184 trace facade, so the proposer-facing code cannot even name the pool.
_ALLOWED_FIRST_PARTY: dict[str, frozenset[str]] = {
    "schema.py": frozenset(),
    "verify_tool.py": frozenset(
        {
            "core.comprehension_attempt.router",
            "core.epistemic_disclosure.ask_acquisition",
            "core.epistemic_disclosure.ask_handle",
            "core.epistemic_disclosure.limitation",
            "core.epistemic_questions.delivery",
            "core.epistemic_questions.serving_gate",
            "evals.gsm8k_math.equivalence.trace",
            "demos.claude_hybrid_verification.schema",
        }
    ),
    "run_demo.py": frozenset({"demos.claude_hybrid_verification.verify_tool"}),
    "__init__.py": frozenset(),
}

_FIRST_PARTY_ROOTS = (
    "algebra",
    "chat",
    "core",
    "demos",
    "evals",
    "field",
    "generate",
    "language_packs",
    "sensorium",
    "teaching",
    "vault",
)

#: Names whose *binding or call* in demo code would be a commit-surface bypass.
#: (String literals — e.g. authority-path tokens — are deliberately not flagged.)
_FORBIDDEN_NAMES = frozenset(
    {
        "resolve_pooled",
        "pooled_candidates",
        "select_self_verified",
        "classify_derivation",
        "self_verifies",
        "Resolution",
        "GroundedDerivation",
        "replay_accumulation_ledger",
        "build_accumulation_ledger",
        "semantic_state_candidates",
        "render_question",
        "evaluate_served_ask",
    }
)


def _imported_modules(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def _bound_names(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            found.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Attribute):
            found.add(node.attr)
    return found


def test_scanner_self_test_catches_a_planted_bypass():
    """Non-vacuity: the same predicates used below must flag a planted bypass."""
    planted = ast.parse("from generate.derivation.pool import resolve_pooled\n")
    imported = _imported_modules(planted)
    assert any(m.split(".")[0] == "generate" for m in imported)
    assert _FORBIDDEN_NAMES & _bound_names(planted)


@pytest.mark.parametrize("filename", _DEMO_MODULES)
def test_demo_module_imports_are_allowlisted(filename):
    tree = ast.parse((DEMO_DIR / filename).read_text(encoding="utf-8"))
    first_party = {
        module
        for module in _imported_modules(tree)
        if module.split(".")[0] in _FIRST_PARTY_ROOTS
    }
    assert first_party == set(_ALLOWED_FIRST_PARTY[filename]), filename
    assert not any(m.split(".")[0] == "generate" for m in first_party)
    assert not any(m.split(".")[0] == "chat" for m in first_party)


@pytest.mark.parametrize("filename", _DEMO_MODULES)
def test_demo_module_never_binds_a_commit_surface(filename):
    tree = ast.parse((DEMO_DIR / filename).read_text(encoding="utf-8"))
    assert not (_FORBIDDEN_NAMES & _bound_names(tree)), filename


def test_authority_path_tokens_resolve_to_real_objects():
    """The dotted authority tokens are labels for real deciders; an upstream
    rename must rot loudly, not silently."""
    import importlib

    for token in (
        *verify_tool._AUTHORITIES_DERIVATION,
        *verify_tool._AUTHORITIES_ASK,
    ):
        if "(" in token:  # pseudo-tokens name artifacts, not importables
            continue
        module_name, _, attribute = token.rpartition(".")
        module = importlib.import_module(module_name)
        assert hasattr(module, attribute), token


def test_tool_name_and_status_vocabulary_match_schema():
    schema = load_tool_schema()
    assert schema["name"] == TOOL_NAME == "core.semantic_derivation.verify"
    assert set(schema["outputSchema"]["properties"]["status"]["enum"]) == {
        "verified",
        "refused",
        "ask",
        "invalid",
    }
