from __future__ import annotations

import pytest

from language_packs import load_pack_entries
from morphology.registry import MorphologyRegistry, load_morphology


def test_hebrew_morphology_registry_loads_triliteral_roots():
    registry = load_morphology("he_logos_micro_v1")

    assert len(registry) == 8
    davar = registry.require("he-morph-001")
    assert davar.surface == "\u05d3\u05d1\u05e8"
    assert davar.root == "\u05d3-\u05d1-\u05e8"
    assert davar.inflection["gender"] == "masculine"
    devarim = registry.require("he-morph-008")
    assert devarim.surface == "\u05d3\u05d1\u05e8\u05d9\u05dd"
    assert devarim.root == davar.root
    assert devarim.suffix_chain == ("\u05d9\u05dd",)
    assert devarim.inflection["number"] == "plural"


def test_greek_morphology_registry_preserves_ordered_prefix_and_suffix():
    registry = load_morphology("grc_logos_micro_v1")

    aletheia = registry.for_surface("\u1f00\u03bb\u03ae\u03b8\u03b5\u03b9\u03b1")
    assert aletheia is not None
    assert aletheia.prefix_chain == ("\u1f00",)
    assert aletheia.stem == "\u03bb\u03b7\u03b8\u03b5\u03b9"
    assert aletheia.suffix_chain == ("\u03b1",)
    assert aletheia.inflection["case"] == "nominative"


def test_depth_pack_lexicon_entries_resolve_morphology_ids():
    registry = load_morphology("he_logos_micro_v1")
    entries = load_pack_entries("he_logos_micro_v1")

    assert all(entry.morphology_id for entry in entries)
    for entry in entries:
        morph = registry.require(entry.morphology_id or "")
        assert morph.surface == entry.surface
        assert morph.lemma == entry.lemma


def test_pack_without_morphology_returns_empty_registry():
    registry = load_morphology("en_minimal_v1")
    assert len(registry) == 0
    assert registry.get("missing") is None


def test_morphology_registry_rejects_duplicate_ids():
    entry = load_morphology("he_logos_micro_v1").require("he-morph-001")
    with pytest.raises(ValueError, match="Duplicate morphology_id"):
        MorphologyRegistry([entry, entry])
