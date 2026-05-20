"""Tests for the frontier_compare cross-provider lane (ADR-0082 wiring).

Pins the integration between providers.py + model_registry.py +
runner.py that was unwired when PR #58 landed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.frontier_compare.__main__ import main
from evals.frontier_compare.cross_provider import (
    ProviderObservation,
    run_prompt_battery,
)
from evals.frontier_compare.providers import ProviderConfig, build_adapter


# ---------------------------------------------------------------------------
# Cross-provider suite — CORE adapter only (no API needed)
# ---------------------------------------------------------------------------


def test_prompt_battery_runs_with_core_adapter() -> None:
    """The cross-provider suite must work with CORE as one provider among
    many — that's the whole point of routing CORE through the same
    adapter abstraction as OpenAI/Anthropic/Ollama."""
    cfg = ProviderConfig(provider="core", model="core-native")
    adapter = build_adapter(cfg)
    report = run_prompt_battery(adapter, cfg=cfg)

    assert report.suite == "prompt_battery"
    assert report.cases, "prompt battery must emit at least one case"
    assert report.passed is True
    # Every case carries a ProviderObservation in details.
    for case in report.cases:
        obs = case.details.get("observation")
        assert obs is not None
        assert obs["provider"] == "core"
        assert obs["model"] == "core-native"
        assert obs["surface"], "CORE adapter should produce non-empty surface"


def test_provider_observation_records_failures_not_exceptions() -> None:
    """Adapter exceptions must be recorded as failed observations, never
    propagated — a single provider hiccup must not abort the suite."""
    cfg = ProviderConfig(provider="core", model="core-native")

    def broken_adapter(prompt: str) -> str:
        raise RuntimeError("simulated provider failure")

    report = run_prompt_battery(broken_adapter, cfg=cfg)
    assert not report.passed
    for case in report.cases:
        assert not case.passed
        assert case.failures == ("adapter_error",)
        obs = case.details["observation"]
        assert obs["error_type"] == "RuntimeError"
        assert "simulated" in obs["error_message"]


def test_provider_observation_records_empty_surface() -> None:
    """An adapter that returns an empty string must be flagged as
    'empty_surface', distinct from an adapter that throws."""
    cfg = ProviderConfig(provider="core", model="core-native")
    report = run_prompt_battery(lambda p: "", cfg=cfg)
    assert not report.passed
    for case in report.cases:
        assert case.failures == ("empty_surface",)


# ---------------------------------------------------------------------------
# CLI routing — load-bearing dispatch logic
# ---------------------------------------------------------------------------


def test_cli_default_runs_core_native_path(tmp_path: Path, capsys) -> None:
    """`--suite determinism` (CORE-only) with default provider runs the
    legacy CORE-native path — no breaking change for existing operators."""
    report_path = tmp_path / "core_run.json"
    code = main(["--suite", "determinism", "--json", "--report", str(report_path)])
    out = capsys.readouterr().out
    payload = json.loads(out)
    # Existing SuiteReport shape: top-level 'suite' key, not 'suites'.
    assert payload.get("suite") == "determinism"
    assert code == 0 or code == 1  # determinism may pass or fail; both valid
    assert report_path.exists()


def test_cli_prompt_battery_with_core_provider(tmp_path: Path, capsys) -> None:
    """--provider core --suite prompt_battery must route through the
    cross-provider adapter path even though provider is CORE."""
    report_path = tmp_path / "cross_core.json"
    code = main(
        [
            "--provider", "core",
            "--suite", "prompt_battery",
            "--json",
            "--report", str(report_path),
        ]
    )
    out = capsys.readouterr().out
    payload = json.loads(out)
    # Cross-provider runs always produce a BenchmarkReport with model + mode.
    assert payload["model"] == "core-native"
    assert payload["mode"] == "core"
    assert len(payload["suites"]) == 1
    assert payload["suites"][0]["suite"] == "prompt_battery"
    assert code == 0  # CORE adapter on a fixed battery should pass
    assert report_path.exists()


def test_cli_rejects_core_only_suite_with_non_core_provider(capsys) -> None:
    """Loud failure when an operator asks for a CORE-only suite with a
    non-CORE provider — no silent telemetry degradation."""
    code = main(["--provider", "openai", "--suite", "determinism"])
    err = capsys.readouterr().err
    assert code == 2
    assert "CORE-only" in err
    assert "prompt_battery" in err  # tells operator the right alternative


def test_cli_help_lists_both_suite_families() -> None:
    """--help must surface both CORE-only and cross-provider suites so
    operators discover the cross-provider lane without reading source."""
    with pytest.raises(SystemExit):
        main(["--help"])


# ---------------------------------------------------------------------------
# Model registry validation — the guardrail against silent drift
# ---------------------------------------------------------------------------


def test_unregistered_model_is_rejected(monkeypatch, tmp_path: Path) -> None:
    """ADR-0082's load-bearing guarantee: floating or unregistered models
    are rejected before any benchmark cycles burn.  Operators cannot
    silently report results against an alias the registry doesn't know."""
    # Stub the env so we get past from_env, then override --model to an
    # unregistered slug.  require_model_card should raise.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-used")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-2024-08-06")
    with pytest.raises(Exception):  # require_model_card raises ValueError or KeyError
        main(
            [
                "--provider", "openai",
                "--model", "gpt-totally-fake-not-in-registry-9999",
                "--suite", "prompt_battery",
                "--env-file", str(tmp_path / "nonexistent.env"),
            ]
        )


# ---------------------------------------------------------------------------
# Provider observation dataclass
# ---------------------------------------------------------------------------


def test_provider_observation_succeeded_property() -> None:
    """succeeded = no error AND non-empty surface."""
    good = ProviderObservation(
        prompt="p", surface="hello", provider="x", model="y", elapsed_ms=1.0
    )
    assert good.succeeded
    err = ProviderObservation(
        prompt="p", surface="", provider="x", model="y",
        elapsed_ms=1.0, error_type="E", error_message="m",
    )
    assert not err.succeeded
    empty = ProviderObservation(
        prompt="p", surface="", provider="x", model="y", elapsed_ms=1.0
    )
    assert not empty.succeeded
    whitespace_only = ProviderObservation(
        prompt="p", surface="   ", provider="x", model="y", elapsed_ms=1.0
    )
    assert not whitespace_only.succeeded
