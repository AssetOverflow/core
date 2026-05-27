"""CW-2 — composition_registry loader tests.

Covers: empty no-op, round-trip, deterministic order, manifest mismatch,
declared-without-file, cache, byte-stability, allowlist enforcement
(defense-in-depth), polarity validation, conflict detection,
``is_affirmed`` / ``is_falsified`` semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generate.comprehension.composition_registry import (
    CompositionRegistry,
    CompositionRegistryLoadError,
    WrongCompositionCategory,
    clear_cache,
    is_affirmed,
    is_falsified,
    load_composition_registry,
    lookup,
)
from language_packs.compile_compositions import compile_compositions
from teaching.math_composition_ratification import SAFE_COMPOSITION_CATEGORIES


def _write_entry(
    path: Path,
    surface_pattern: str,
    composition_category: str,
    polarity: str = "affirms",
    provenance: str = "test_provenance",
) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "surface_pattern": surface_pattern,
                    "composition_category": composition_category,
                    "polarity": polarity,
                    "provenance": provenance,
                    "evidence_hashes": [],
                }
            )
            + "\n"
        )


@pytest.fixture
def empty_pack(tmp_path: Path) -> Path:
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "test_empty", "checksum": "deadbeef"}),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def populated_pack(tmp_path: Path) -> Path:
    comp_dir = tmp_path / "compositions"
    comp_dir.mkdir()
    _write_entry(
        comp_dir / "multiplicative.jsonl",
        "bound(count) × bound(unit_cost)",
        "multiplicative_composition",
        polarity="affirms",
    )
    _write_entry(
        comp_dir / "additive.jsonl",
        "bound(qty_a) + bound(qty_b)",
        "additive_composition",
        polarity="affirms",
    )
    _, sha = compile_compositions(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test_populated",
                "checksum": "deadbeef",
                "composition_checksum": sha,
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def setup_function(_):
    clear_cache()


def test_empty_pack_returns_empty_registry(empty_pack: Path):
    reg = load_composition_registry(empty_pack)
    assert isinstance(reg, CompositionRegistry)
    assert reg.is_empty()


def test_populated_round_trip(populated_pack: Path):
    reg = load_composition_registry(populated_pack)
    assert not reg.is_empty()
    entry = lookup(reg, "bound(count) × bound(unit_cost)")
    assert entry is not None
    assert entry.composition_category == "multiplicative_composition"
    assert entry.polarity == "affirms"


def test_safe_categories_pinned():
    # Defense-in-depth: the load-time allowlist matches what the handler
    # enforces at write time. If the handler's set ever drifts, this
    # test fails — operator must update both surfaces consciously.
    assert SAFE_COMPOSITION_CATEGORIES == frozenset(
        {
            "multiplicative_composition",
            "additive_composition",
            "subtractive_composition",
        }
    )


def test_unsafe_category_at_load_raises(tmp_path: Path):
    comp_dir = tmp_path / "compositions"
    comp_dir.mkdir()
    _write_entry(
        comp_dir / "bad.jsonl",
        "bound(a) ratio bound(b)",
        "ratio_composition",  # explicitly deferred per ADR-0169
    )
    _, sha = compile_compositions(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test",
                "checksum": "x",
                "composition_checksum": sha,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(WrongCompositionCategory, match="ratio_composition"):
        load_composition_registry(tmp_path)


def test_invalid_polarity_raises(tmp_path: Path):
    comp_dir = tmp_path / "compositions"
    comp_dir.mkdir()
    _write_entry(
        comp_dir / "bad.jsonl",
        "x",
        "multiplicative_composition",
        polarity="maybe",
    )
    _, sha = compile_compositions(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test",
                "checksum": "x",
                "composition_checksum": sha,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CompositionRegistryLoadError, match="invalid polarity"):
        load_composition_registry(tmp_path)


def test_is_affirmed_and_is_falsified(tmp_path: Path):
    comp_dir = tmp_path / "compositions"
    comp_dir.mkdir()
    _write_entry(
        comp_dir / "ok.jsonl",
        "shape_a",
        "multiplicative_composition",
        polarity="affirms",
    )
    _write_entry(
        comp_dir / "ok.jsonl",
        "shape_b",
        "multiplicative_composition",
        polarity="falsifies",
    )
    _, sha = compile_compositions(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "t", "checksum": "x", "composition_checksum": sha}),
        encoding="utf-8",
    )
    reg = load_composition_registry(tmp_path)
    assert is_affirmed(reg, "shape_a") is True
    assert is_falsified(reg, "shape_a") is False
    assert is_affirmed(reg, "shape_b") is False
    assert is_falsified(reg, "shape_b") is True
    # Absence
    assert is_affirmed(reg, "shape_unknown") is False
    assert is_falsified(reg, "shape_unknown") is False


def test_manifest_mismatch_raises(populated_pack: Path):
    manifest_path = populated_pack / "manifest.json"
    payload = json.loads(manifest_path.read_text())
    payload["composition_checksum"] = "f" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    clear_cache()
    with pytest.raises(CompositionRegistryLoadError, match="checksum mismatch"):
        load_composition_registry(populated_pack)


def test_declared_without_file_raises(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "pack_id": "test",
                "checksum": "x",
                "composition_checksum": "f" * 64,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CompositionRegistryLoadError, match="missing"):
        load_composition_registry(tmp_path)


def test_compile_byte_stable(tmp_path: Path):
    comp_dir = tmp_path / "compositions"
    comp_dir.mkdir()
    _write_entry(
        comp_dir / "a.jsonl",
        "bound(count) × bound(unit_cost)",
        "multiplicative_composition",
    )
    b1, s1 = compile_compositions(tmp_path)
    b2, s2 = compile_compositions(tmp_path)
    assert b1 == b2
    assert s1 == s2


def test_cache_returns_same_instance(populated_pack: Path):
    reg1 = load_composition_registry(populated_pack)
    reg2 = load_composition_registry(populated_pack)
    assert reg1 is reg2


def test_conflicting_pattern_polarities_raise(tmp_path: Path):
    comp_dir = tmp_path / "compositions"
    comp_dir.mkdir()
    _write_entry(
        comp_dir / "a.jsonl",
        "same_pattern",
        "multiplicative_composition",
        polarity="affirms",
    )
    _write_entry(
        comp_dir / "b.jsonl",
        "same_pattern",
        "multiplicative_composition",
        polarity="falsifies",
    )
    _, sha = compile_compositions(tmp_path)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"pack_id": "t", "checksum": "x", "composition_checksum": sha}),
        encoding="utf-8",
    )
    with pytest.raises(CompositionRegistryLoadError, match="conflicting entries"):
        load_composition_registry(tmp_path)
