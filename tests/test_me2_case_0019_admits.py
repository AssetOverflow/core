"""ME-2 — the load-bearing truth test: case 0019 admits via cross-sentence subject.

End-to-end: ratify ``bound(count) × bound(unit_cost)`` under
``multiplicative_composition``, then run the match dispatcher with
``prior_subject="John"`` on case 0019's composition sentence, then
feed the recognizer match into ``inject_from_match``. The composition
registry consult must produce a ``CandidateInitial`` with
``entity="John"`` and ``value=1200``.

This is the real-world canary that was deferred by ME-1's Option A.
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
from generate.recognizer_match import RecognizerMatch, match
from generate.recognizer_registry import RatifiedRecognizer
from language_packs.compile_compositions import compile_compositions


_SHAPE = "bound(count) × bound(unit_cost)"

_CASE_0019_COMPOSITION_SENTENCE = (
    "The dog ends up having health problems and this requires "
    "3 vet appointments, which cost $400 each."
)


def _stage_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "en_core_math_v1"
    comp_dir = pack / "compositions"
    comp_dir.mkdir(parents=True)
    (comp_dir / "multiplicative_composition.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": _SHAPE,
                "composition_category": "multiplicative_composition",
                "polarity": "affirms",
                "provenance": "test_me2_case_0019",
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


def _synthetic_registry() -> tuple[RatifiedRecognizer, ...]:
    """Build a one-entry registry with a currency_per_unit_composition spec."""
    canonical_pattern: Mapping[str, Any] = {
        "anchor_kind": "currency_per_unit_composition",
        "observed_currency_symbols": ["$"],
        "observed_per_units": ["each", "apiece"],
    }
    rec = RatifiedRecognizer(
        proposal_id="test_me2_proposal_id",
        shape_category=ShapeCategory.RATE_WITH_CURRENCY,
        canonical_pattern=canonical_pattern,
        spec_digest="0" * 64,
        review_date="2026-05-27",
        ratified_at_revision="test",
    )
    return (rec,)


def setup_function(_):
    clear_composition_cache()


def test_case_0019_admits_with_prior_subject_john(monkeypatch, tmp_path):
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    registry = _synthetic_registry()
    # ME-2: dispatcher with prior_subject "John" (resolved from sentence 0).
    m = match(_CASE_0019_COMPOSITION_SENTENCE, registry, prior_subject="John")
    assert m is not None
    assert isinstance(m, RecognizerMatch)
    anchor = m.parsed_anchors[0]
    assert anchor["composition_shape"] == _SHAPE
    assert anchor["subject"] == "John"

    emissions = inject_from_match(m, _CASE_0019_COMPOSITION_SENTENCE)
    assert len(emissions) == 1
    composed = emissions[0]
    assert isinstance(composed, CandidateInitial)
    assert composed.initial.entity == "John"
    assert composed.initial.quantity.value == 1200
    assert composed.initial.quantity.unit == "dollars"


def test_case_0019_refuses_without_prior_subject(monkeypatch, tmp_path):
    """Same sentence, no prior_subject → ME-1 Option A still refuses."""
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    registry = _synthetic_registry()
    m = match(_CASE_0019_COMPOSITION_SENTENCE, registry, prior_subject=None)
    assert m is None


def test_case_0019_refuses_with_pronoun_prior(monkeypatch, tmp_path):
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    registry = _synthetic_registry()
    m = match(_CASE_0019_COMPOSITION_SENTENCE, registry, prior_subject="He")
    # Pronouns are rejected in cross-sentence binding (refusal-preferring)
    assert m is None


def test_maria_same_sentence_unaffected_by_prior_subject(monkeypatch, tmp_path):
    """ME-1's same-sentence path still works; prior_subject is irrelevant."""
    pack = _stage_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    registry = _synthetic_registry()
    # Same-sentence subject "Maria" wins; prior_subject argument is ignored
    # because the regular matcher hits first.
    statement = "Maria bought 3 vet appointments at $400 each."
    m = match(statement, registry, prior_subject="John")
    assert m is not None
    composed = inject_from_match(m, statement)[0]
    assert isinstance(composed, CandidateInitial)
    # Same-sentence subject wins; the head Maria is the entity.
    assert composed.initial.entity == "Maria"
