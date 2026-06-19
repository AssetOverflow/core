"""Guard against new legacy raw-text parsing in derivation paths."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Current serving legacy surfaces — explicit allowlist while migrations proceed.
ALLOWLISTED_LEGACY_DERIVATION_FILES: frozenset[str] = frozenset({
    "generate/derivation/affine_comparative_inversion_total.py",
    "generate/derivation/affine_fraction_delta.py",
    "generate/derivation/bounded_rate_projection.py",
    "generate/derivation/calendar_grounding.py",
    "generate/derivation/clauses.py",
    "generate/derivation/closed_reference_affine_aggregate.py",
    "generate/derivation/comparatives.py",
    "generate/derivation/compose.py",
    "generate/derivation/duration_segment_total.py",
    "generate/derivation/extract.py",
    "generate/derivation/fraction_decrease.py",
    "generate/derivation/giveaway_target_residual.py",
    "generate/derivation/goal_residual.py",
    "generate/derivation/loose_crayon_box_capacity.py",
    "generate/derivation/multistep.py",
    "generate/derivation/nested_fraction_remainder_total.py",
    "generate/derivation/percent_partition.py",
    "generate/derivation/piecewise_daily_hours_total.py",
    "generate/derivation/product_bridge.py",
    "generate/derivation/question_bound_product.py",
    "generate/derivation/r1_reconstruction.py",
    "generate/derivation/round_trip_trip_duration.py",
    "generate/derivation/search.py",
    "generate/derivation/sequential_comparative_scale.py",
    "generate/derivation/state/bind.py",
    "generate/derivation/state/source.py",
    "generate/derivation/survey_rate_earnings.py",
    "generate/derivation/target.py",
    "generate/derivation/temporal_tariff.py",
    "generate/math_candidate_parser.py",
    "generate/math_candidate_graph.py",
    "generate/math_completeness.py",
    "generate/math_roundtrip.py",
})

_REGEX_USAGE = re.compile(
    r"\bre\.(?:compile|search|match|findall|finditer|sub|split)\b"
)

_SCAN_ROOTS = (
    _REPO_ROOT / "generate" / "derivation",
    _REPO_ROOT / "generate" / "math_candidate_parser.py",
    _REPO_ROOT / "generate" / "math_candidate_graph.py",
    _REPO_ROOT / "generate" / "math_completeness.py",
    _REPO_ROOT / "generate" / "math_roundtrip.py",
)


def _iter_scanned_files() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        for path in sorted(root.rglob("*.py")):
            if path.name == "__init__.py":
                continue
            files.append(path)
    return files


def test_no_new_legacy_derivation_regex_without_exception() -> None:
    violations: list[str] = []

    for path in _iter_scanned_files():
        rel = path.relative_to(_REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if not _REGEX_USAGE.search(text):
            continue
        if rel in ALLOWLISTED_LEGACY_DERIVATION_FILES:
            continue
        if "LEGACY_EXCEPTION" in text:
            continue
        violations.append(rel)

    assert not violations, (
        "New legacy raw-text regex surfaces detected. Either migrate to "
        "ProblemFrame/substrate extraction or add an explicit LEGACY_EXCEPTION "
        f"with migration rationale:\n" + "\n".join(violations)
    )


def test_allowlist_covers_current_legacy_derivation_regex_files() -> None:
    """Ensure the allowlist stays aligned with scanned legacy regex files."""
    regex_files = {
        path.relative_to(_REPO_ROOT).as_posix()
        for path in _iter_scanned_files()
        if _REGEX_USAGE.search(path.read_text(encoding="utf-8"))
    }
    missing = sorted(regex_files - ALLOWLISTED_LEGACY_DERIVATION_FILES)
    assert not missing, (
        "Allowlist missing current legacy regex files — update "
        "ALLOWLISTED_LEGACY_DERIVATION_FILES:\n" + "\n".join(missing)
    )