"""RAT-1 — live end-to-end admission tests on the canonical pack.

These tests verify the full ratify → compile → load → match → consult
→ admit chain fires on the canonical en_core_math_v1 pack — no synthetic
fixture overrides. The earlier ME-1..ME-5 integration tests verified
the wiring with synthetic packs; RAT-1 closes the chain on production.

Specifically, after ratifying ``bound(count) × bound(unit_cost)`` under
``multiplicative_composition`` AND seeding the matching
``currency_per_unit_composition`` RecognizerSpec, statements of the
form ``"X bought N items at $C each"`` and the cross-sentence
``"... requires N items, which cost $C each"`` (with prior-sentence
proper-noun subject) admit through ``parse_and_solve`` instead of
refusing with "recognizer matched but produced no injection".
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
)
from generate.recognizer_registry import clear_registry_cache


def setup_function(_):
    clear_composition_cache()
    clear_registry_cache()


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    while here.parent != here and not (here / "pyproject.toml").exists():
        here = here.parent
    return here


def _verify_seed_present() -> bool:
    """Return True iff the canonical pack has the composition + the
    matching ratified RecognizerSpec for currency_per_unit_composition.

    These artifacts must have been seeded once via the RAT-1 operator
    workflow (``core teaching compile-pack`` + ``core teaching
    seed-recognizer``). When absent, tests skip — the wiring is still
    verified by the synthetic-pack ME-5 integration test.
    """
    from generate.recognizer_registry import load_ratified_registry
    from generate.comprehension.composition_registry import load_composition_registry

    reg = load_ratified_registry()
    has_recognizer = any(
        r.canonical_pattern.get("anchor_kind") == "currency_per_unit_composition"
        for r in reg
    )
    comp = load_composition_registry()
    has_pattern = "bound(count) × bound(unit_cost)" in comp.by_pattern
    return has_recognizer and has_pattern


def test_canonical_pack_admits_composition_statement_when_seeded():
    """After RAT-1 seed, a clean composition statement admits."""
    if not _verify_seed_present():
        pytest.skip(
            "RAT-1 seed not present on canonical pack; "
            "run: core teaching seed-recognizer --shape-category rate_with_currency "
            "--anchor-kind currency_per_unit_composition "
            "--observed-currency-symbols '$' --observed-per-units each "
            "AND ratify bound(count) × bound(unit_cost) under multiplicative_composition"
        )

    from generate.math_candidate_graph import parse_and_solve

    # Statement-only canary: the statement should NOT trigger
    # "recognizer matched but produced no injection" — composition
    # admits at the statement layer. (The question layer is a separate
    # bottleneck not under RAT-1 scope.)
    problem = "Maria bought 3 books at $5 each. How much did she pay?"
    r = parse_and_solve(problem)
    # Question parser is the new blocker — assert the failure is on the
    # question, NOT on the composition statement.
    if r.refusal_reason:
        assert "Maria bought 3 books at $5 each" not in r.refusal_reason, (
            f"Statement should have admitted via composition path; "
            f"got: {r.refusal_reason!r}"
        )


def test_canonical_pack_admits_cross_sentence_composition_when_seeded():
    """Case 0019 sentence 1 admits via cross-sentence subject binding."""
    if not _verify_seed_present():
        pytest.skip("RAT-1 seed not present on canonical pack")

    from generate.math_candidate_graph import parse_and_solve

    problem = (
        "John adopts a dog from a shelter.  "
        "The dog ends up having health problems and this requires "
        "3 vet appointments, which cost $400 each.  "
        "How much did John pay?"
    )
    r = parse_and_solve(problem)
    # The composition sentence (sentence 1) should NOT be the refusal
    # site — discourse subject "John" should reach the cross-sentence
    # matcher and produce admission.
    if r.refusal_reason:
        assert "3 vet appointments" not in r.refusal_reason, (
            f"Composition sentence should have admitted via cross-sentence subject; "
            f"got: {r.refusal_reason!r}"
        )


def test_wrong_zero_preserved_on_train_sample():
    """The full train_sample eval must preserve wrong == 0 after RAT-1."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "evals.gsm8k_math.train_sample.v1.runner",
         "--use-reader"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
    )
    report_path = (
        _repo_root() / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json"
    )
    assert report_path.exists(), "train_sample runner must emit report.json"
    report = json.loads(report_path.read_text())
    counts = report["counts"]
    assert counts["wrong"] == 0, f"wrong-zero invariant violated: {counts}"


def test_case_0050_remains_refused_after_rat1():
    """Hazard pin: case 0050 must not admit after any RAT-1 wiring."""
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "-m", "evals.gsm8k_math.train_sample.v1.runner",
         "--use-reader"],
        cwd=_repo_root(),
        capture_output=True,
    )
    report_path = (
        _repo_root() / "evals" / "gsm8k_math" / "train_sample" / "v1" / "report.json"
    )
    report = json.loads(report_path.read_text())
    case = next(
        (c for c in report["per_case"] if c["case_id"].endswith("-0050")),
        None,
    )
    assert case is not None, "case 0050 must exist in train_sample report"
    assert case["verdict"] == "refused", (
        f"case 0050 hazard pin violated: verdict={case['verdict']!r}"
    )
