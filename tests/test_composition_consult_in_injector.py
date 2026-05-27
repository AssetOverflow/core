"""CW-2 — inject_from_match composition-registry consultation tests.

Verifies the contract of ``_consult_composition_registry``:

- empty registry → fallback is a no-op (no admission)
- matcher publishes ``composition_shape`` + ``composed_initial``,
  registry affirms → inject_from_match emits the composed payload
- matcher publishes the shape, registry falsifies → suppressed
- matcher publishes the shape, registry absent → refusal-preferring
- matcher publishes the shape AND registry affirms BUT no
  ``composed_initial`` payload → under-admit (registry never invents
  arithmetic; ADR-0169 §"Mutation boundary")

These tests are wiring-level — they verify the consumer is reachable
from the production code path. They do not exercise the full
candidate-graph pipeline (covered by the eval-delta truth test once a
matcher extension publishes ``composition_shape``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.refusal_taxonomy.shape_categories import ShapeCategory
from generate.comprehension.composition_registry import (
    clear_cache as clear_composition_cache,
)
from generate.math_candidate_parser import CandidateInitial
from generate.math_problem_graph import InitialPossession, Quantity
from generate.recognizer_anchor_inject import inject_from_match
from generate.recognizer_match import RecognizerMatch
from language_packs.compile_compositions import compile_compositions


_SHAPE = "bound(count) × bound(unit_cost)"


def _build_candidate_initial() -> CandidateInitial:
    return CandidateInitial(
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


class _FakeRecognizer:
    """Test double — RecognizerMatch only stores the recognizer reference."""

    spec_id = "test_spec"


def _build_match(anchor: dict[str, Any]) -> RecognizerMatch:
    return RecognizerMatch(
        recognizer=_FakeRecognizer(),  # type: ignore[arg-type]
        category=ShapeCategory.CURRENCY_AMOUNT,
        outcome="admissible",
        graph_intent="amount",
        parsed_anchors=(anchor,),
    )


def _write_registry(
    pack_path: Path,
    surface_pattern: str,
    polarity: str,
    category: str = "multiplicative_composition",
) -> None:
    comp_dir = pack_path / "compositions"
    comp_dir.mkdir(parents=True, exist_ok=True)
    (comp_dir / f"{category}.jsonl").write_text(
        json.dumps(
            {
                "surface_pattern": surface_pattern,
                "composition_category": category,
                "polarity": polarity,
                "provenance": "test_provenance",
                "evidence_hashes": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _, sha = compile_compositions(pack_path)
    (pack_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "en_core_math_v1",  # use canonical pack id
                "checksum": "deadbeef",
                "composition_checksum": sha,
            }
        ),
        encoding="utf-8",
    )


def setup_function(_):
    clear_composition_cache()


def _patch_pack_root(monkeypatch: pytest.MonkeyPatch, pack_path: Path) -> None:
    """Redirect the composition registry's default pack-root to our fixture."""
    from generate.comprehension import composition_registry as cr

    monkeypatch.setattr(cr, "_DEFAULT_PACK_RELPATH", pack_path)
    monkeypatch.setattr(cr, "_repo_root", lambda: Path("/"))


def test_no_composition_shape_returns_empty(monkeypatch, tmp_path):
    _patch_pack_root(monkeypatch, tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "en_core_math_v1", "checksum": "x"}),
        encoding="utf-8",
    )
    match = _build_match({"kind": "currency_amount"})  # no composition_shape
    result = inject_from_match(match, "sentence")
    assert result == ()


def test_affirms_admits_pre_composed_initial(monkeypatch, tmp_path):
    _write_registry(tmp_path, _SHAPE, "affirms")
    _patch_pack_root(monkeypatch, tmp_path)
    composed = _build_candidate_initial()
    match = _build_match(
        {
            "composition_shape": _SHAPE,
            "composed_initial": composed,
        }
    )
    result = inject_from_match(match, "sentence")
    assert result == (composed,)


def test_falsifies_suppresses(monkeypatch, tmp_path):
    _write_registry(tmp_path, _SHAPE, "falsifies")
    _patch_pack_root(monkeypatch, tmp_path)
    composed = _build_candidate_initial()
    match = _build_match(
        {
            "composition_shape": _SHAPE,
            "composed_initial": composed,
        }
    )
    result = inject_from_match(match, "sentence")
    assert result == ()


def test_absent_in_registry_refuses(monkeypatch, tmp_path):
    _write_registry(tmp_path, "different_shape", "affirms")
    _patch_pack_root(monkeypatch, tmp_path)
    composed = _build_candidate_initial()
    match = _build_match(
        {
            "composition_shape": _SHAPE,  # not in registry
            "composed_initial": composed,
        }
    )
    result = inject_from_match(match, "sentence")
    assert result == ()


def test_affirms_without_composed_payload_under_admits(monkeypatch, tmp_path):
    """Registry never invents arithmetic — affirms + no payload = ()."""
    _write_registry(tmp_path, _SHAPE, "affirms")
    _patch_pack_root(monkeypatch, tmp_path)
    match = _build_match({"composition_shape": _SHAPE})  # no composed_initial
    result = inject_from_match(match, "sentence")
    assert result == ()


def test_empty_registry_is_noop(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "en_core_math_v1", "checksum": "x"}),
        encoding="utf-8",
    )
    _patch_pack_root(monkeypatch, tmp_path)
    composed = _build_candidate_initial()
    match = _build_match(
        {
            "composition_shape": _SHAPE,
            "composed_initial": composed,
        }
    )
    # Empty registry — even with a fully-populated anchor, no admission.
    result = inject_from_match(match, "sentence")
    assert result == ()
