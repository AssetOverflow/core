"""Empty-registry no-op invariant for the consumption wiring.

Loads the ``frame_registry`` and ``composition_registry`` against an
**isolated empty pack** (not the canonical en_core_math_v1) and asserts
the empty-registry contract holds:

- both registries load without error
- both report ``is_empty() == True``
- the canonical lexicon ``load_lexicon`` continues to work unchanged
  (no manifest-schema regression from adding the new optional fields)
- the composition-consult fallback in ``inject_from_match`` is a no-op
  when registry is empty (a synthetic match with a populated
  composition_shape anchor still returns ``()``)

RAT-1 note: the canonical pack may now carry ratified composition
entries; these tests use a synthetic isolated pack to verify the
empty-registry contract independent of canonical-pack state.
"""

from __future__ import annotations

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
    load_composition_registry,
)
from generate.comprehension.frame_registry import (
    clear_cache as clear_frame_cache,
    load_frame_registry,
)
from generate.comprehension.lexicon import load_lexicon
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import InitialPossession, Quantity
from generate.recognizer_anchor_inject import inject_from_match
from generate.recognizer_match import RecognizerMatch


def setup_function(_):
    clear_frame_cache()
    clear_composition_cache()


import json
from pathlib import Path

import pytest


def _stage_empty_pack(tmp_path: Path) -> Path:
    pack = tmp_path / "en_core_math_v1"
    pack.mkdir()
    (pack / "manifest.json").write_text(
        json.dumps({"pack_id": "en_core_math_v1", "checksum": "deadbeef"}),
        encoding="utf-8",
    )
    return pack


def _patch_pack_root(monkeypatch, pack_path: Path) -> None:
    from generate.comprehension import composition_registry as cr
    from generate.comprehension import frame_registry as fr

    monkeypatch.setattr(cr, "_DEFAULT_PACK_RELPATH", pack_path)
    monkeypatch.setattr(cr, "_repo_root", lambda: Path("/"))
    monkeypatch.setattr(fr, "_DEFAULT_PACK_RELPATH", pack_path)
    monkeypatch.setattr(fr, "_repo_root", lambda: Path("/"))


def test_frame_registry_loads_and_is_empty_on_isolated_pack(monkeypatch, tmp_path):
    pack = _stage_empty_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)
    reg = load_frame_registry()
    assert reg.is_empty()
    assert reg.source_pack_id == "en_core_math_v1"


def test_composition_registry_loads_and_is_empty_on_isolated_pack(monkeypatch, tmp_path):
    pack = _stage_empty_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)
    reg = load_composition_registry()
    assert reg.is_empty()
    assert reg.source_pack_id == "en_core_math_v1"


def test_lexicon_load_unaffected_by_new_manifest_fields():
    # The manifest schema gained optional ``frame_checksum`` and
    # ``composition_checksum`` fields. The existing lexicon loader
    # MUST be unaffected when those fields are absent or present.
    lex = load_lexicon()
    assert lex.source_pack_id == "en_core_math_v1"
    assert len(lex.by_surface) > 0


def test_inject_from_match_composition_consult_is_noop_when_registry_empty(monkeypatch, tmp_path):
    """Even a fully-populated anchor produces no admission when registry empty."""
    pack = _stage_empty_pack(tmp_path)
    _patch_pack_root(monkeypatch, pack)

    class _FakeRec:
        spec_id = "test"

    composed = CandidateInitial(
        initial=InitialPossession(
            entity="John",
            quantity=Quantity(value=1200, unit="dollars"),
        ),
        source_span="3 vet appointments cost $400 each",
        matched_anchor="has",
        matched_value_token="1200",
        matched_unit_token="dollars",
        matched_entity_token="John",
    )
    match = RecognizerMatch(
        recognizer=_FakeRec(),  # type: ignore[arg-type]
        category=ShapeCategory.CURRENCY_AMOUNT,
        outcome="admissible",
        graph_intent="amount",
        parsed_anchors=(
            {
                "composition_shape": "bound(count) × bound(unit_cost)",
                "composed_initial": composed,
            },
        ),
    )
    # Empty registry — no entry to affirm the shape — refusal-preferring.
    assert inject_from_match(match, "synthetic sentence") == ()
