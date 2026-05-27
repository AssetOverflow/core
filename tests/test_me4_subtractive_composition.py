"""ME-4 — subtractive composition matcher tests.

Covers the ``subtractive_quantity_composition`` extension to
``_match_multiplicative_aggregation``. Pattern: ``<Subject> <init-verb>
<N> <unit>(,| then| ;| and then| and) <sub-verb> <M> <unit>`` with
same unit and ``M < N`` (non-negative remainder discipline).
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
from language_packs.compile_compositions import compile_compositions


_SPEC: Mapping[str, Any] = {
    "anchor_kind": "subtractive_quantity_composition",
    "observed_units": ["apples", "apple", "dollars", "pounds", "pound", "books"],
}

_SHAPE = "bound(initial) − bound(removed)"


def setup_function(_):
    clear_composition_cache()


def test_canonical_subtractive_admits():
    result = _match_multiplicative_aggregation(
        "Sam had 50 apples, gave 20 apples.", _SPEC
    )
    assert result is not None
    a = result[0][0]
    assert a["composition_shape"] == _SHAPE
    assert a["subject"] == "Sam"
    composed = a["composed_initial"]
    assert isinstance(composed, CandidateInitial)
    assert composed.initial.entity == "Sam"
    assert composed.initial.quantity.value == 30
    assert composed.initial.quantity.unit == "apples"


def test_then_connective_admits():
    result = _match_multiplicative_aggregation(
        "Mark had 100 dollars then spent 30 dollars.", _SPEC
    )
    assert result is not None
    assert result[0][0]["composed_initial"].initial.quantity.value == 70


def test_and_connective_admits():
    result = _match_multiplicative_aggregation(
        "Tom had 10 apples and lost 4 apples.", _SPEC
    )
    assert result is not None
    assert result[0][0]["composed_initial"].initial.quantity.value == 6


def test_negative_remainder_refuses():
    """Refusal-preferring: count_b >= count_a is the wrong>0 hazard."""
    result = _match_multiplicative_aggregation(
        "Lily had 5 apples and lost 10 apples.", _SPEC
    )
    assert result is None


def test_equal_remainder_refuses():
    result = _match_multiplicative_aggregation(
        "Lily had 5 apples and lost 5 apples.", _SPEC
    )
    assert result is None  # zero remainder still refuses (initial=0 boundary)


def test_pronoun_subject_refuses():
    result = _match_multiplicative_aggregation(
        "He had 10 apples, gave 3 apples.", _SPEC
    )
    assert result is None


def test_determiner_subject_refuses():
    result = _match_multiplicative_aggregation(
        "The cat had 10 apples, gave 3 apples.", _SPEC
    )
    assert result is None


def test_cross_unit_refuses():
    result = _match_multiplicative_aggregation(
        "Sam had 50 apples, gave 20 dollars.", _SPEC
    )
    assert result is None


def test_unobserved_unit_refuses():
    spec = dict(_SPEC)
    spec["observed_units"] = ["dollars"]
    result = _match_multiplicative_aggregation(
        "Sam had 50 apples, gave 20 apples.", spec
    )
    assert result is None


def test_unknown_initial_verb_refuses():
    result = _match_multiplicative_aggregation(
        "Sam adopted 50 apples, gave 20 apples.", _SPEC
    )
    assert result is None


def test_unknown_removal_verb_refuses():
    result = _match_multiplicative_aggregation(
        "Sam had 50 apples, dropped 20 apples.", _SPEC
    )
    assert result is None  # 'dropped' not in removal verb set


def test_gave_away_variant():
    result = _match_multiplicative_aggregation(
        "Sam had 50 apples, gave away 20 apples.", _SPEC
    )
    assert result is not None
    assert result[0][0]["composed_initial"].initial.quantity.value == 30


def test_additive_path_unaffected():
    """ME-3 additive dispatch still works."""
    additive_spec = {
        "anchor_kind": "additive_quantity_composition",
        "observed_units": ["dollars"],
    }
    result = _match_multiplicative_aggregation(
        "Maria saved 30 dollars in May and 20 dollars in June.", additive_spec
    )
    assert result is not None
    assert result[0][0]["composed_initial"].initial.quantity.value == 50


def test_multiplicative_aggregate_path_unaffected():
    spec = {"anchor_kind": "multiplicative_aggregate"}
    result = _match_multiplicative_aggregation(
        "There are 3 bags with 5 items each.", spec
    )
    assert result is not None
    anchors, intent = result
    assert intent == "aggregate"
    assert anchors == ()


def test_anchor_audit_fields():
    result = _match_multiplicative_aggregation(
        "Sam had 50 apples, gave 20 apples.", _SPEC
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
        "initial_verb",
        "removal_verb",
        "kind",
    }.issubset(a.keys())


# ---------------------------------------------------------------------------
# End-to-end via composition_registry.
# ---------------------------------------------------------------------------


def _stage_pack(tmp_path: Path, polarity: str = "affirms") -> Path:
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "subtractive_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": _SHAPE,
                "composition_category": "subtractive_composition",
                "polarity": polarity,
                "provenance": "test_me4",
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


def _make_match(anchors):
    class _R:
        spec_id = "test_me4"

    return RecognizerMatch(
        recognizer=_R(),  # type: ignore[arg-type]
        category=ShapeCategory.MULTIPLICATIVE_AGGREGATION,
        outcome="admissible",
        graph_intent="aggregate",
        parsed_anchors=anchors,
    )


def test_end_to_end_subtractive_admits(monkeypatch, tmp_path):
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    statement = "Sam had 50 apples, gave 20 apples."
    result = _match_multiplicative_aggregation(statement, _SPEC)
    assert result is not None
    emissions = inject_from_match(_make_match(result[0]), statement)
    assert len(emissions) == 1
    assert emissions[0].initial.quantity.value == 30


def test_end_to_end_falsifies_suppresses(monkeypatch, tmp_path):
    pack = _stage_pack(tmp_path, polarity="falsifies")
    _patch_pack_root(monkeypatch, pack)

    statement = "Sam had 50 apples, gave 20 apples."
    result = _match_multiplicative_aggregation(statement, _SPEC)
    assert result is not None
    emissions = inject_from_match(_make_match(result[0]), statement)
    assert emissions == ()
