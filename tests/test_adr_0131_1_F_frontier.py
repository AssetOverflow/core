"""ADR-0131.1.F — frontier-baseline comparison methodology pins.

These tests assert the *methodology* is intact. They never call a
live API. The head-to-head numbers, when run, are deterministic
artifacts (cached responses + comparison JSON) — those become
inspectable evidence; the tests here pin the contract that produces
them.

Contracts pinned:

- Every adjacent-benchmark citation has the required fields and a
  well-shaped HTTPS URL.
- The provider registry has the three vendors B1's promotion gate
  cares about (anthropic / openai / google) plus a documented env-key
  per provider.
- ``parse_provider_verdict`` is conservative: ambiguity collapses to
  ``refused`` (never confabulates a polarized verdict).
- ``run_frontier`` reads from cache only when invoked with no API
  key and no override (the contributor-machine path).
- ``build_comparison`` produces a deterministic JSON shape with
  ``schema_version`` and the scope disclaimer.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from evals.math_symbolic_equivalence.v1.frontier import (
    ADJACENT_BENCHMARK_CITATIONS,
    FrontierRunError,
    PROVIDERS,
    build_comparison,
    parse_provider_verdict,
    run_frontier,
)


# ---------------------------------------------------------------------------
# Adjacent-benchmark citations
# ---------------------------------------------------------------------------


_REQUIRED_CITATION_KEYS = {
    "vendor", "model", "benchmark", "score", "metric",
    "source_url", "source_date", "note",
}

_HTTPS_RE = re.compile(r"^https?://[^\s]+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@pytest.mark.parametrize("citation", ADJACENT_BENCHMARK_CITATIONS)
def test_citations_well_formed(citation: dict[str, Any]) -> None:
    keys = set(citation.keys())
    assert _REQUIRED_CITATION_KEYS.issubset(keys), (
        f"citation missing keys: {_REQUIRED_CITATION_KEYS - keys}"
    )
    assert isinstance(citation["vendor"], str) and citation["vendor"]
    assert isinstance(citation["model"], str) and citation["model"]
    assert isinstance(citation["benchmark"], str) and citation["benchmark"]
    assert isinstance(citation["score"], float) and 0.0 <= citation["score"] <= 1.0
    assert citation["metric"] in {"exact_match", "pass_at_1", "accuracy"}
    assert _HTTPS_RE.match(str(citation["source_url"])), citation["source_url"]
    assert _DATE_RE.match(str(citation["source_date"])), citation["source_date"]
    assert isinstance(citation["note"], str) and citation["note"]


def test_citations_cover_three_major_vendors() -> None:
    vendors = {c["vendor"] for c in ADJACENT_BENCHMARK_CITATIONS}
    assert {"Anthropic", "OpenAI", "Google"}.issubset(vendors)


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------


def test_provider_registry_has_three_cloud_vendors() -> None:
    # Three cloud-frontier vendors required by the architecture-aligned
    # gate; additional local providers (e.g. ollama) may be added but
    # do not displace the cloud-frontier baseline.
    assert {"anthropic", "openai", "google"}.issubset(set(PROVIDERS))


@pytest.mark.parametrize("provider_id", sorted(PROVIDERS))
def test_provider_env_key_documented(provider_id: str) -> None:
    spec = PROVIDERS[provider_id]
    assert spec.env_key.startswith("FRONTIER_"), spec.env_key
    # Cloud providers use _KEY (API secret); local providers (e.g.
    # ollama) use _URL (server endpoint, not a secret).
    assert spec.env_key.endswith(("_KEY", "_URL")), spec.env_key
    assert spec.default_model, "default_model must be non-empty"


def test_unknown_provider_refuses() -> None:
    with pytest.raises(FrontierRunError, match="unknown provider"):
        run_frontier("not_a_real_provider", cases=[])


# ---------------------------------------------------------------------------
# Verdict parser (the load-bearing free-text → closed-vocab boundary)
# ---------------------------------------------------------------------------


def test_verdict_parser_clean_equivalent() -> None:
    assert parse_provider_verdict("EQUIVALENT") == "equivalent"
    assert parse_provider_verdict("equivalent") == "equivalent"
    assert parse_provider_verdict("Answer: EQUIVALENT.") == "equivalent"


def test_verdict_parser_clean_not_equivalent() -> None:
    assert parse_provider_verdict("NOT_EQUIVALENT") == "not_equivalent"
    assert parse_provider_verdict("not_equivalent") == "not_equivalent"


def test_verdict_parser_clean_refused() -> None:
    assert parse_provider_verdict("REFUSED") == "refused"


def test_verdict_parser_empty_collapses_to_refused() -> None:
    assert parse_provider_verdict("") == "refused"
    assert parse_provider_verdict("   ") == "refused"


def test_verdict_parser_no_sentinel_collapses_to_refused() -> None:
    # The provider didn't follow instructions — never confabulate a
    # polarized verdict from prose.
    assert parse_provider_verdict("I'm not sure about this one.") == "refused"
    assert parse_provider_verdict("Both look the same to me.") == "refused"


def test_verdict_parser_chain_of_thought_last_token_wins() -> None:
    # Frontier models often deliberate then conclude.
    reply = (
        "Let me think. Expanding (x+1)^2 gives x^2+2x+1. "
        "So at first glance NOT_EQUIVALENT, but actually EQUIVALENT."
    )
    assert parse_provider_verdict(reply) == "equivalent"


def test_verdict_parser_non_string_input() -> None:
    assert parse_provider_verdict(None) == "refused"  # type: ignore[arg-type]
    assert parse_provider_verdict(123) == "refused"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# run_frontier — contributor-machine and stub-injection paths
# ---------------------------------------------------------------------------


def test_run_frontier_with_stub_invoke_does_not_need_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Make sure no real env key bleeds in.
    monkeypatch.delenv("FRONTIER_ANTHROPIC_KEY", raising=False)
    monkeypatch.setattr(
        "evals.math_symbolic_equivalence.v1.frontier.frontier_runner._RESPONSES_DIR",
        _isolated_responses_dir(monkeypatch),
    )

    def fake_invoke(prompt: str, api_key: str, model: str) -> str:
        # Stub: always say EQUIVALENT to exercise the scoring path.
        return "EQUIVALENT"

    cases = [
        {"case_id": "stub-001", "expression_a": "x+1", "expression_b": "1+x"},
        {"case_id": "stub-002", "expression_a": "x", "expression_b": "x+1"},
    ]
    results = run_frontier(
        "anthropic",
        model="stub-model",
        cases=cases,
        invoke_override=fake_invoke,
    )
    assert len(results) == 2
    assert all(r["verdict"] == "equivalent" for r in results)
    assert all(r["provider"] == "anthropic" for r in results)


def test_run_frontier_caches_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    responses_dir = _isolated_responses_dir(monkeypatch)
    monkeypatch.setattr(
        "evals.math_symbolic_equivalence.v1.frontier.frontier_runner._RESPONSES_DIR",
        responses_dir,
    )

    call_count = {"n": 0}

    def fake_invoke(prompt: str, api_key: str, model: str) -> str:
        call_count["n"] += 1
        return "REFUSED"

    cases = [{"case_id": "stub-003", "expression_a": "x", "expression_b": "x"}]
    first = run_frontier(
        "anthropic", model="stub-model", cases=cases, invoke_override=fake_invoke,
    )
    second = run_frontier(
        "anthropic", model="stub-model", cases=cases, invoke_override=fake_invoke,
    )
    assert first == second
    assert call_count["n"] == 1, "second run must hit cache, not re-invoke"


def test_run_frontier_refuses_without_key_or_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FRONTIER_ANTHROPIC_KEY", raising=False)
    monkeypatch.setattr(
        "evals.math_symbolic_equivalence.v1.frontier.frontier_runner._RESPONSES_DIR",
        _isolated_responses_dir(monkeypatch),
    )
    cases = [{"case_id": "x", "expression_a": "x", "expression_b": "x"}]
    with pytest.raises(FrontierRunError, match="FRONTIER_ANTHROPIC_KEY"):
        run_frontier("anthropic", model="stub-model", cases=cases)


# ---------------------------------------------------------------------------
# build_comparison — deterministic JSON shape
# ---------------------------------------------------------------------------


def test_build_comparison_no_providers_includes_core_and_citations() -> None:
    comparison = build_comparison(providers=[])
    assert comparison["schema_version"] == 1
    assert comparison["adr"] == "0131.1.F"
    assert comparison["scope_disclaimer"]
    assert comparison["core"]["lane"] == "math_symbolic_equivalence_v1"
    assert comparison["core"]["refusal_correctness"] == 1.0
    assert comparison["core"]["deterministic"] is True
    assert comparison["frontier_head_to_head"] == []
    assert len(comparison["adjacent_benchmark_citations"]) == len(
        ADJACENT_BENCHMARK_CITATIONS,
    )


def test_build_comparison_deterministic() -> None:
    a = build_comparison(providers=[])
    b = build_comparison(providers=[])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _isolated_responses_dir(monkeypatch: pytest.MonkeyPatch):
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp(prefix="frontier-responses-"))
    return tmp
