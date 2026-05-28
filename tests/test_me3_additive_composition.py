"""ME-3 — additive composition matcher tests.

Covers the ``additive_quantity_composition`` extension to
``_match_multiplicative_aggregation``: extracts two same-unit
quantities connected by ``and`` and emits a pre-composed
``CandidateInitial`` whose value is the sum.

Subject binding: same-sentence Option A (refuse on missing /
pronoun / determiner). Cross-sentence subject for additive composition
is deferred (would mirror ME-2 but not needed for the v1 ME-3
canary).
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
)
from generate.recognizer_registry import RatifiedRecognizer
from language_packs.compile_compositions import compile_compositions


_SPEC: Mapping[str, Any] = {
    "anchor_kind": "additive_quantity_composition",
    "observed_units": ["pounds", "pound", "dollars", "apples", "books"],
}

_SHAPE = "bound(qty_a) + bound(qty_b)"


def setup_function(_):
    clear_composition_cache()


def test_same_unit_admits_with_sum():
    result = _match_multiplicative_aggregation(
        "Maria saved 30 dollars in May and 20 dollars in June.", _SPEC
    )
    assert result is not None
    a = result[0][0]
    assert a["composition_shape"] == _SHAPE
    assert a["subject"] == "Maria"
    composed = a["composed_initial"]
    assert isinstance(composed, CandidateInitial)
    assert composed.initial.entity == "Maria"
    assert composed.initial.quantity.value == 50
    assert composed.initial.quantity.unit == "dollars"


def test_pronoun_subject_refuses():
    """Pronoun head → refuse (Option A); cross-sentence is a future brief."""
    result = _match_multiplicative_aggregation(
        "He lost 3 pounds in March and 4 pounds in April.", _SPEC
    )
    assert result is None


def test_determiner_subject_refuses():
    result = _match_multiplicative_aggregation(
        "The dog ate 3 pounds in March and 4 pounds in April.", _SPEC
    )
    assert result is None


def test_cross_unit_refuses():
    """Cross-unit composition has no canonical conversion in v1."""
    result = _match_multiplicative_aggregation(
        "Maria earned 30 dollars and 20 books.", _SPEC
    )
    assert result is None


def test_unobserved_unit_refuses():
    spec = dict(_SPEC)
    spec["observed_units"] = ["dollars"]  # 'pounds' missing
    result = _match_multiplicative_aggregation(
        "Tom gained 5 pounds and 3 pounds.", spec
    )
    assert result is None


def test_zero_count_refuses():
    result = _match_multiplicative_aggregation(
        "Maria earned 0 dollars and 50 dollars.", _SPEC
    )
    assert result is None


def test_plural_normalization():
    """pound/pounds normalize to canonical singular for matching."""
    spec = dict(_SPEC)
    spec["observed_units"] = ["pound"]
    result = _match_multiplicative_aggregation(
        "Tom gained 5 pounds and 3 pounds.", spec
    )
    # observed_units has 'pound' singular; the matcher should still
    # accept (rstrip normalization).
    assert result is not None


def test_unknown_verb_refuses():
    result = _match_multiplicative_aggregation(
        "Maria adopted 3 pounds and 4 pounds.", _SPEC
    )
    assert result is None


def test_multiplicative_aggregate_path_unaffected():
    """The original detection-only aggregate path still works."""
    spec = {"anchor_kind": "multiplicative_aggregate"}
    result = _match_multiplicative_aggregation(
        "There are 3 bags with 5 items each.", spec
    )
    # Detection-only — empty parsed_anchors.
    assert result is not None
    anchors, intent = result
    assert intent == "aggregate"
    assert anchors == ()


def test_wrong_anchor_kind_refuses():
    spec = {"anchor_kind": "currency_per_unit_rate"}
    result = _match_multiplicative_aggregation(
        "Maria earned 30 dollars and 20 dollars.", spec
    )
    assert result is None


def test_anchor_audit_fields():
    result = _match_multiplicative_aggregation(
        "Tom gained 5 pounds and 3 pounds.", _SPEC
    )
    assert result is not None
    a = result[0][0]
    assert {
        "composition_shape",
        "composed_initial",
        "count_a",
        "count_b",
        "unit",
        "subject",
        "verb",
        "kind",
    }.issubset(a.keys())


def test_source_span_substring():
    statement = "Sam earned 100 dollars and 50 dollars."
    result = _match_multiplicative_aggregation(statement, _SPEC)
    assert result is not None
    span = result[0][0]["composed_initial"].source_span
    assert span in statement


def test_no_match_returns_none():
    result = _match_multiplicative_aggregation(
        "There is nothing here.", _SPEC
    )
    assert result is None


# ---------------------------------------------------------------------------
# End-to-end: ratified composition entry + matcher + inject_from_match
# ---------------------------------------------------------------------------


def _stage_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "additive_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": _SHAPE,
                "composition_category": "additive_composition",
                "polarity": "affirms",
                "provenance": "test_me3",
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
    return pack


def _patch_pack_root(monkeypatch, pack_path: Path) -> None:
    from generate.comprehension import composition_registry as cr

    monkeypatch.setattr(cr, "_DEFAULT_PACK_RELPATH", pack_path)
    monkeypatch.setattr(cr, "_repo_root", lambda: Path("/"))


def _make_match(anchors: tuple[Mapping[str, Any], ...]) -> RecognizerMatch:
    class _FakeRec:
        spec_id = "test_me3"

    return RecognizerMatch(
        recognizer=_FakeRec(),  # type: ignore[arg-type]
        category=ShapeCategory.MULTIPLICATIVE_AGGREGATION,
        outcome="admissible",
        graph_intent="aggregate",
        parsed_anchors=anchors,
    )


def test_end_to_end_additive_admits(monkeypatch, tmp_path):
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    statement = "Maria saved 30 dollars in May and 20 dollars in June."
    result = _match_multiplicative_aggregation(statement, _SPEC)
    assert result is not None
    match = _make_match(result[0])
    emissions = inject_from_match(match, statement)
    assert len(emissions) == 1
    composed = emissions[0]
    assert composed.initial.entity == "Maria"
    assert composed.initial.quantity.value == 50
    assert composed.initial.quantity.unit == "dollars"


def test_end_to_end_falsifies_suppresses(monkeypatch, tmp_path):
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "additive_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": _SHAPE,
                "composition_category": "additive_composition",
                "polarity": "falsifies",
                "provenance": "test_falsifies",
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

    statement = "Maria saved 30 dollars in May and 20 dollars in June."
    result = _match_multiplicative_aggregation(statement, _SPEC)
    assert result is not None
    match = _make_match(result[0])
    emissions = inject_from_match(match, statement)
    assert emissions == ()
