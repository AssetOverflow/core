"""ME-5 — integration smoke test across all three SAFE_COMPOSITION_CATEGORIES.

Exercises the complete matcher → registry → injector → admission chain
for each of the three SAFE categories in one test run. Verifies the
ME-1 through ME-4 stack composes cleanly when all three category
ratifications are present in the same pack.

This is the milestone canary: when this test passes, the math
composition flywheel's matcher half is operational end-to-end across
all admissible categories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
)
from generate.math_candidate_parser import CandidateInitial
from generate.recognizer_anchor_inject import inject_from_match
from generate.recognizer_match import (
    RecognizerMatch,
    _match_multiplicative_aggregation,
    _match_rate_with_currency,
)
from language_packs.compile_compositions import compile_compositions
from teaching.math_composition_ratification import SAFE_COMPOSITION_CATEGORIES


def setup_function(_):
    clear_composition_cache()


def _stage_pack_all_three(tmp_path: Path) -> Path:
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)

    entries = [
        (
            "multiplicative_composition.jsonl",
            {
                "surface_pattern": "bound(count) × bound(unit_cost)",
                "composition_category": "multiplicative_composition",
                "polarity": "affirms",
                "provenance": "test_me5",
                "evidence_hashes": [],
            },
        ),
        (
            "additive_composition.jsonl",
            {
                "surface_pattern": "bound(qty_a) + bound(qty_b)",
                "composition_category": "additive_composition",
                "polarity": "affirms",
                "provenance": "test_me5",
                "evidence_hashes": [],
            },
        ),
        (
            "subtractive_composition.jsonl",
            {
                "surface_pattern": "bound(initial) − bound(removed)",
                "composition_category": "subtractive_composition",
                "polarity": "affirms",
                "provenance": "test_me5",
                "evidence_hashes": [],
            },
        ),
    ]
    for filename, entry in entries:
        (comp_dir / filename).write_text(json.dumps(entry) + "\n", encoding="utf-8")

    _, sha = compile_compositions(pack)
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "en_core_math_v1",
                "checksum": "x",
                "composition_checksum": sha,
            }
        ),
        encoding="utf-8",
    )
    return pack


def _patch_pack_root(monkeypatch, pack_path: Path) -> None:
    from generate.comprehension import composition_registry as cr

    monkeypatch.setattr(cr, "_DEFAULT_PACK_RELPATH", pack_path)
    monkeypatch.setattr(cr, "_repo_root", lambda: Path("/"))


def _make_match(anchors, category: ShapeCategory) -> RecognizerMatch:
    class _R:
        spec_id = "test_me5"

    return RecognizerMatch(
        recognizer=_R(),  # type: ignore[arg-type]
        category=category,
        outcome="admissible",
        graph_intent="rate",
        parsed_anchors=anchors,
    )


def test_all_three_canaries_admit_through_full_pipeline(monkeypatch, tmp_path):
    """End-to-end: one canary per SAFE category, all admit."""
    pack = _stage_pack_all_three(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    # Multiplicative canary (ME-1)
    mult_spec: Mapping[str, Any] = {
        "anchor_kind": "currency_per_unit_composition",
        "observed_currency_symbols": ["$"],
        "observed_per_units": ["each", "apiece"],
    }
    mult_stmt = "Maria bought 3 vet appointments at $400 each."
    mult_result = _match_rate_with_currency(mult_stmt, mult_spec)
    assert mult_result is not None
    mult_match = _make_match(mult_result[0], ShapeCategory.RATE_WITH_CURRENCY)
    mult_emit = inject_from_match(mult_match, mult_stmt)
    assert len(mult_emit) == 1
    assert isinstance(mult_emit[0], CandidateInitial)
    assert mult_emit[0].initial.entity == "Maria"
    assert mult_emit[0].initial.quantity.value == 1200
    assert mult_emit[0].initial.quantity.unit == "dollars"

    # Additive canary (ME-3)
    add_spec: Mapping[str, Any] = {
        "anchor_kind": "additive_quantity_composition",
        "observed_units": ["dollars"],
    }
    add_stmt = "Sam earned 100 dollars and 50 dollars."
    add_result = _match_multiplicative_aggregation(add_stmt, add_spec)
    assert add_result is not None
    add_match = _make_match(add_result[0], ShapeCategory.MULTIPLICATIVE_AGGREGATION)
    add_emit = inject_from_match(add_match, add_stmt)
    assert len(add_emit) == 1
    assert add_emit[0].initial.entity == "Sam"
    assert add_emit[0].initial.quantity.value == 150
    assert add_emit[0].initial.quantity.unit == "dollars"

    # Subtractive canary (ME-4)
    sub_spec: Mapping[str, Any] = {
        "anchor_kind": "subtractive_quantity_composition",
        "observed_units": ["apples", "apple"],
    }
    sub_stmt = "Tom had 10 apples and lost 4 apples."
    sub_result = _match_multiplicative_aggregation(sub_stmt, sub_spec)
    assert sub_result is not None
    sub_match = _make_match(sub_result[0], ShapeCategory.MULTIPLICATIVE_AGGREGATION)
    sub_emit = inject_from_match(sub_match, sub_stmt)
    assert len(sub_emit) == 1
    assert sub_emit[0].initial.entity == "Tom"
    assert sub_emit[0].initial.quantity.value == 6
    assert sub_emit[0].initial.quantity.unit == "apples"


def test_partial_pack_only_admits_present_categories(monkeypatch, tmp_path):
    """If only multiplicative is ratified, additive + subtractive refuse."""
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "multiplicative_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": "bound(count) × bound(unit_cost)",
                "composition_category": "multiplicative_composition",
                "polarity": "affirms",
                "provenance": "test_me5_partial",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, sha = compile_compositions(pack)
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "en_core_math_v1",
                "checksum": "x",
                "composition_checksum": sha,
            }
        ),
        encoding="utf-8",
    )
    _patch_pack_root(monkeypatch, pack)

    # Multiplicative admits...
    mult_result = _match_rate_with_currency(
        "Maria bought 3 vet appointments at $400 each.",
        {
            "anchor_kind": "currency_per_unit_composition",
            "observed_currency_symbols": ["$"],
            "observed_per_units": ["each"],
        },
    )
    assert mult_result is not None
    mult_match = _make_match(mult_result[0], ShapeCategory.RATE_WITH_CURRENCY)
    mult_emit = inject_from_match(mult_match, "Maria bought 3 vet appointments at $400 each.")
    assert len(mult_emit) == 1

    # ...but additive refuses because no additive entry in this pack.
    add_result = _match_multiplicative_aggregation(
        "Sam earned 100 dollars and 50 dollars.",
        {
            "anchor_kind": "additive_quantity_composition",
            "observed_units": ["dollars"],
        },
    )
    assert add_result is not None
    add_match = _make_match(add_result[0], ShapeCategory.MULTIPLICATIVE_AGGREGATION)
    add_emit = inject_from_match(add_match, "Sam earned 100 dollars and 50 dollars.")
    assert add_emit == ()  # refusal-preferring


def test_all_safe_categories_have_extension_admission():
    """Every entry in SAFE_COMPOSITION_CATEGORIES has a corresponding
    matcher extension path. This pin breaks if a future ADR widens the
    allowlist without also shipping a matcher extension — operator must
    decide consciously."""
    expected = {
        "multiplicative_composition",
        "additive_composition",
        "subtractive_composition",
    }
    assert SAFE_COMPOSITION_CATEGORIES == frozenset(expected), (
        "ME-5 covers exactly these three categories — widening "
        "SAFE_COMPOSITION_CATEGORIES requires adding a matcher extension "
        "and updating this pin."
    )


def test_falsifies_uniformly_suppresses_across_categories(monkeypatch, tmp_path):
    """polarity='falsifies' suppresses for any category."""
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    for filename, category, shape in [
        (
            "multiplicative_composition.jsonl",
            "multiplicative_composition",
            "bound(count) × bound(unit_cost)",
        ),
        (
            "additive_composition.jsonl",
            "additive_composition",
            "bound(qty_a) + bound(qty_b)",
        ),
        (
            "subtractive_composition.jsonl",
            "subtractive_composition",
            "bound(initial) − bound(removed)",
        ),
    ]:
        (comp_dir / filename).write_text(
            json.dumps(
                {
                    "surface_pattern": shape,
                    "composition_category": category,
                    "polarity": "falsifies",
                    "provenance": "test_me5_falsifies",
                    "evidence_hashes": [],
                }
            )
            + "\n",
            encoding="utf-8",
        )
    _, sha = compile_compositions(pack)
    (pack / "manifest.json").write_text(
        json.dumps(
            {"pack_id": "en_core_math_v1", "checksum": "x", "composition_checksum": sha}
        ),
        encoding="utf-8",
    )
    _patch_pack_root(monkeypatch, pack)

    # All three matchers extract anchors but inject_from_match suppresses.
    mult = _match_rate_with_currency(
        "Maria bought 3 vet appointments at $400 each.",
        {
            "anchor_kind": "currency_per_unit_composition",
            "observed_currency_symbols": ["$"],
            "observed_per_units": ["each"],
        },
    )
    assert mult is not None
    assert (
        inject_from_match(
            _make_match(mult[0], ShapeCategory.RATE_WITH_CURRENCY),
            "Maria bought 3 vet appointments at $400 each.",
        )
        == ()
    )

    add = _match_multiplicative_aggregation(
        "Sam earned 100 dollars and 50 dollars.",
        {"anchor_kind": "additive_quantity_composition", "observed_units": ["dollars"]},
    )
    assert add is not None
    assert (
        inject_from_match(
            _make_match(add[0], ShapeCategory.MULTIPLICATIVE_AGGREGATION),
            "Sam earned 100 dollars and 50 dollars.",
        )
        == ()
    )

    sub = _match_multiplicative_aggregation(
        "Tom had 10 apples and lost 4 apples.",
        {
            "anchor_kind": "subtractive_quantity_composition",
            "observed_units": ["apples"],
        },
    )
    assert sub is not None
    assert (
        inject_from_match(
            _make_match(sub[0], ShapeCategory.MULTIPLICATIVE_AGGREGATION),
            "Tom had 10 apples and lost 4 apples.",
        )
        == ()
    )
