"""ME-1 — end-to-end admission via the composition_registry consumption path.

Truth-test for the PR: the Maria-with-3-appointments canary, given a
ratified ``bound(count) × bound(unit_cost)`` entry under
``multiplicative_composition``, produces a ``CandidateInitial``
admission when fed through ``inject_from_match`` (the consumption wire
from PR #398).

This proves the full ratify → compile → load → match → consume → admit
chain on a synthetic sentence with same-sentence subject. The case-0019
real canary requires cross-sentence subject lookup (ME-2 brief).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

import pytest

from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
)
from generate.math_candidate_parser import CandidateInitial
from generate.recognizer_anchor_inject import inject_from_match
from generate.recognizer_match import RecognizerMatch, _match_rate_with_currency
from language_packs.compile_compositions import compile_compositions


_SPEC: Mapping[str, Any] = {
    "anchor_kind": "currency_per_unit_composition",
    "observed_currency_symbols": ["$"],
    "observed_per_units": ["each", "apiece"],
}

_SHAPE = "bound(count) × bound(unit_cost)"


def _stage_pack(tmp_path: Path) -> Path:
    """Stage a minimal en_core_math_v1-style pack with a ratified entry."""
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "multiplicative_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": _SHAPE,
                "composition_category": "multiplicative_composition",
                "polarity": "affirms",
                "provenance": "test_me1_end_to_end",
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
                "checksum": "deadbeef",
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


def setup_function(_):
    clear_composition_cache()


class _FakeRec:
    spec_id = "test_me1"


def _build_match(anchors: tuple[Mapping[str, Any], ...]) -> RecognizerMatch:
    from evals.refusal_taxonomy.shape_categories import ShapeCategory

    return RecognizerMatch(
        recognizer=_FakeRec(),  # type: ignore[arg-type]
        category=ShapeCategory.RATE_WITH_CURRENCY,
        outcome="admissible",
        graph_intent="rate",
        parsed_anchors=anchors,
    )


def test_synthetic_maria_admits_via_composition_registry(monkeypatch, tmp_path):
    """The truth test: Maria sentence + ratified entry + consult = admission."""
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    # Step 1: matcher produces composition_shape + composed_initial
    statement = "Maria bought 3 vet appointments at $400 each."
    match_result = _match_rate_with_currency(statement, _SPEC)
    assert match_result is not None
    anchors, _intent = match_result

    # Step 2: feed the populated anchors into inject_from_match (the
    # consumption wire). The per-category injector for RATE_WITH_CURRENCY
    # is not registered, so the consult fallback fires.
    match = _build_match(anchors)
    emissions = inject_from_match(match, statement)

    # Step 3: assert the admission emerged with the composed value
    assert len(emissions) == 1
    composed = emissions[0]
    assert isinstance(composed, CandidateInitial)
    assert composed.initial.entity == "Maria"
    assert composed.initial.quantity.value == 1200
    assert composed.initial.quantity.unit == "dollars"


def test_case_0019_partial_under_option_a(monkeypatch, tmp_path):
    """Case 0019 real text — Option A refuses; admission requires ME-2."""
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    case_0019_sentence = (
        "The dog ends up having health problems and this requires "
        "3 vet appointments, which cost $400 each."
    )
    match_result = _match_rate_with_currency(case_0019_sentence, _SPEC)
    # Option A: refuses because no same-sentence proper-noun subject.
    # This is the honest scope boundary for ME-1; case 0019 admission
    # requires cross-sentence subject lookup (ME-2 brief).
    assert match_result is None


def test_falsifies_entry_suppresses(monkeypatch, tmp_path):
    """Polarity 'falsifies' for the same shape suppresses admission."""
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "multiplicative_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": _SHAPE,
                "composition_category": "multiplicative_composition",
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

    statement = "Maria bought 3 vet appointments at $400 each."
    match_result = _match_rate_with_currency(statement, _SPEC)
    assert match_result is not None
    match = _build_match(match_result[0])
    emissions = inject_from_match(match, statement)
    assert emissions == ()


def test_no_registry_entry_refuses(monkeypatch, tmp_path):
    """Empty registry → refusal-preferring even with populated anchor."""
    pack = tmp_path / "en_core_math_v1"
    pack.mkdir()
    (pack / "manifest.json").write_text(
        json.dumps({"pack_id": "en_core_math_v1", "checksum": "x"}),
        encoding="utf-8",
    )
    _patch_pack_root(monkeypatch, pack)

    statement = "Maria bought 3 vet appointments at $400 each."
    match_result = _match_rate_with_currency(statement, _SPEC)
    assert match_result is not None
    match = _build_match(match_result[0])
    emissions = inject_from_match(match, statement)
    assert emissions == ()
