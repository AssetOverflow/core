"""ADR-0119.4 — frontier-baseline comparison tests.

Pinning tests for the gsm8k_math frontier-baseline comparison files.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


def test_frontier_json_schema() -> None:
    """(a) frontier.json loads as valid JSON with schema_version == 1."""
    root = Path(__file__).resolve().parents[1]
    frontier_path = root / "evals/gsm8k_math/baselines/frontier.json"
    assert frontier_path.exists()

    with open(frontier_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == 1
    assert "issued_at" in data
    assert "note" in data
    assert "baselines" in data
    assert "core_lane_note" in data


def test_frontier_baseline_entries() -> None:
    """(b) Every baseline entry has system / task / source / url / reported_accuracy_pct."""
    root = Path(__file__).resolve().parents[1]
    frontier_path = root / "evals/gsm8k_math/baselines/frontier.json"

    with open(frontier_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    baselines = data["baselines"]
    assert len(baselines) >= 3

    for entry in baselines:
        assert "system" in entry
        assert isinstance(entry["system"], str)
        assert "task" in entry
        assert entry["task"] == "GSM8K"
        assert "source" in entry
        assert isinstance(entry["source"], str)
        assert "url" in entry
        assert isinstance(entry["url"], str)
        assert "reported_accuracy_pct" in entry
        assert isinstance(entry["reported_accuracy_pct"], (int, float))
        assert 0.0 <= entry["reported_accuracy_pct"] <= 100.0


def test_frontier_urls_valid() -> None:
    """(c) Every URL is a valid http(s) URL string (no broken format)."""
    root = Path(__file__).resolve().parents[1]
    frontier_path = root / "evals/gsm8k_math/baselines/frontier.json"

    with open(frontier_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for entry in data["baselines"]:
        url = entry["url"]
        parsed = urlparse(url)
        assert parsed.scheme in ("http", "https")
        assert parsed.netloc != ""


def test_comparison_json_schema() -> None:
    """(d) comparison_v1.json includes both core_measurement and frontier_citations."""
    root = Path(__file__).resolve().parents[1]
    comparison_path = root / "evals/gsm8k_math/baselines/comparison_v1.json"
    assert comparison_path.exists()

    with open(comparison_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema_version"] == 1
    assert "generated_at" in data
    assert "core_measurement" in data
    assert "frontier_citations" in data
    assert "disclaimer" in data

    core = data["core_measurement"]
    assert core["split"] == "public"
    assert core["cases_total"] == 150
    assert "correct" in core
    assert "wrong" in core
    assert "refused" in core
    assert "correct_rate" in core
    assert "wrong_rate" in core
    assert "refused_rate" in core

    assert len(data["frontier_citations"]) >= 3


def test_disclaimer_content() -> None:
    """(e) The disclaimer field is non-empty and mentions both the CORE-original split AND the actual-GSM8K-test caveat."""
    root = Path(__file__).resolve().parents[1]
    comparison_path = root / "evals/gsm8k_math/baselines/comparison_v1.json"

    with open(comparison_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    disclaimer = data["disclaimer"]
    assert isinstance(disclaimer, str)
    assert len(disclaimer) > 0

    # Mentions both "CORE-original" (or "CORE" and "public split") and "actual GSM8K test" (or "actual GSM8K" or similar)
    disclaimer_lower = disclaimer.lower()
    assert "core-original" in disclaimer_lower or "core" in disclaimer_lower
    assert "public split" in disclaimer_lower or "original" in disclaimer_lower
    assert "actual gsm8k" in disclaimer_lower or "actual-gsm8k-test" in disclaimer_lower
    assert "caveat" in disclaimer_lower or "not strictly comparable" in disclaimer_lower or "different" in disclaimer_lower
