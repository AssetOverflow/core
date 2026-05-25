from __future__ import annotations

import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "core.cli", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_capability_chains_json() -> None:
    res = _run("capability", "chains", "--json")
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert "active_chains" in body
    assert "formula" in body
    assert body["formula"]["chains_required"] == 200
    assert body["formula"]["chains_present"] == body["active_chains"]
    assert body["missing_target_intent_shapes"] == []
    assert body["by_domain_operator_family"]["hebrew_greek_textual_reasoning"]["causal"] >= 8
    assert body["by_domain_operator_family"]["hebrew_greek_textual_reasoning"]["contradiction"] >= 8
    assert body["by_domain_operator_family"]["philosophy_theology"]["modal"] >= 8
    assert body["by_domain_operator_family"]["philosophy_theology"]["contradiction"] >= 8


def test_capability_flags_json() -> None:
    res = _run("capability", "flags", "--json")
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert "flag_shipped_default_off" in body


def test_capability_ledger_json() -> None:
    res = _run("capability", "ledger", "--json")
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert "domains" in body
    assert isinstance(body["domains"], list)
    by_domain = {row["domain"]: row for row in body["domains"]}
    for domain in (
        "systems_software",
        "mathematics_logic",
        "physics",
        "hebrew_greek_textual_reasoning",
        "philosophy_theology",
    ):
        assert by_domain[domain]["status"] in {"reasoning-capable", "audit-passed", "expert"}
        assert by_domain[domain]["open_gaps"] == []
    he_grc = by_domain["hebrew_greek_textual_reasoning"]
    assert he_grc["predicates"]["seeded"] is True
    assert he_grc["status"] == "reasoning-capable"
    assert "gap:grc_he_glosses_absent" not in he_grc["open_gaps"]
    assert "gap:he_core_cognition_v1_gloss_coverage_below_threshold" not in he_grc["open_gaps"]
    assert he_grc["open_gaps"] == []
    assert all(
        "chains_present" in coverage and "chains_required" in coverage
        for coverage in he_grc["operator_chain_coverage"].values()
    )


def test_capability_artifact_json_404() -> None:
    res = _run(
        "capability",
        "artifact",
        "--lane",
        "cognition",
        "--split",
        "public",
        "--version",
        "v999",
        "--json",
    )
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["exists"] is False
    assert "artifact_id" in body


def test_capability_artifact_json_existing_is_content_addressed() -> None:
    res = _run(
        "capability",
        "artifact",
        "--lane",
        "cognition",
        "--split",
        "public",
        "--version",
        "v1",
        "--json",
    )
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["exists"] is True
    assert len(body["artifact_id"]) == 64
    assert len(body["result_sha256"]) == 64


def test_capability_domain_contract_json_absent_contract_is_noop() -> None:
    """Packs without a domain contract pass the legacy structural-only
    path. ADR-0093 added the default predicate-running mode; this test
    pins the legacy shape under ``--structural-only``.
    """
    res = _run(
        "capability",
        "domain-contract",
        "--pack-id",
        "en_core_cognition_v1",
        "--json",
        "--structural-only",
    )
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["present"] is False
    assert body["valid"] is True


def test_capability_evidence_plan_json() -> None:
    res = _run("capability", "evidence-plan", "--json")
    assert res.returncode == 0, res.stderr
    body = json.loads(res.stdout)
    assert body["workers_promote_packs"] is False
    assert body["jobs"]
    assert all(job["mutates_packs"] is False for job in body["jobs"])
