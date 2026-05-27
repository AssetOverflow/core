"""Tests for generate.comprehension.lexicon (ADR-0164 §Decision §1)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from generate.comprehension.lexicon import (
    Lexicon,
    LexiconEntry,
    LexiconLoadError,
    load_lexicon,
    lookup,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Categories declared in ADR-0164 §Decision §1 that must be present in the
# en_core_math_v1 pack shipped with PR #322.
REQUIRED_CATEGORIES = {
    "accumulation_verb",
    "capacity_verb",
    "currency_unit_noun",
    "depletion_verb",
    "entity_pronoun",
    "possession_verb",
    "proper_noun_gender_female",
    "proper_noun_gender_male",
    "question_open",
    "residual_modifier",
    "transfer_verb",
}


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_succeeds(self) -> None:
        lex = load_lexicon()
        assert isinstance(lex, Lexicon)

    def test_all_required_categories_present(self) -> None:
        lex = load_lexicon()
        present = set(lex.by_category.keys())
        missing = REQUIRED_CATEGORIES - present
        assert not missing, f"Missing categories: {sorted(missing)}"

    def test_by_category_values_are_sorted_tuples(self) -> None:
        lex = load_lexicon()
        for cat, entries in lex.by_category.items():
            assert isinstance(entries, tuple), f"{cat}: not a tuple"
            lemmas = [e.lemma for e in entries]
            assert lemmas == sorted(lemmas), f"{cat}: entries not sorted by lemma"

    def test_by_surface_is_mapping_proxy(self) -> None:
        import types as _types
        lex = load_lexicon()
        assert isinstance(lex.by_surface, _types.MappingProxyType)

    def test_by_category_is_mapping_proxy(self) -> None:
        import types as _types
        lex = load_lexicon()
        assert isinstance(lex.by_category, _types.MappingProxyType)

    def test_pack_id_is_math_v1(self) -> None:
        lex = load_lexicon()
        assert lex.source_pack_id == "en_core_math_v1"

    def test_sha256_field_is_populated(self) -> None:
        lex = load_lexicon()
        assert len(lex.pack_manifest_sha256) == 64


# ---------------------------------------------------------------------------
# Checksum
# ---------------------------------------------------------------------------


class TestChecksum:
    def test_checksum_mismatch_raises(self, tmp_path: Path) -> None:
        """Tampering the manifest checksum must raise LexiconLoadError."""
        import shutil

        # Copy the real pack into a temp location.
        real_pack = (
            Path(__file__).resolve().parent.parent
            / "language_packs" / "data" / "en_core_math_v1"
        )
        fake_pack = tmp_path / "en_core_math_v1"
        shutil.copytree(real_pack, fake_pack)

        # Corrupt the manifest checksum.
        manifest_path = fake_pack / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["checksum"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest))

        with pytest.raises(LexiconLoadError, match="checksum"):
            load_lexicon(fake_pack)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


class TestLookups:
    @pytest.mark.parametrize("lemma", ["buy", "earn", "get", "collect", "save"])
    def test_accumulation_verb_lemmas(self, lemma: str) -> None:
        lex = load_lexicon()
        entry = lookup(lex, lemma)
        assert entry is not None, f"{lemma!r} not found"
        assert entry.category == "accumulation_verb", (
            f"{lemma!r}: expected accumulation_verb, got {entry.category!r}"
        )

    def test_depletion_verb_lemma(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "spend")
        assert entry is not None
        assert entry.category == "depletion_verb"

    def test_transfer_verb_lemma(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "give")
        assert entry is not None
        assert entry.category == "transfer_verb"

    def test_currency_unit_noun(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "money")
        assert entry is not None
        assert entry.category == "currency_unit_noun"

    def test_entity_pronoun(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "she")
        assert entry is not None
        assert entry.category == "entity_pronoun"

    def test_proper_noun_female(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "tina")
        assert entry is not None
        assert entry.category == "proper_noun_gender_female"

    def test_alias_resolves_to_lemma_entry(self) -> None:
        lex = load_lexicon()
        # "earned" is an alias of "earn" (accumulation_verb)
        entry = lookup(lex, "earned")
        assert entry is not None, "'earned' alias not found"
        assert entry.lemma == "earn"
        assert entry.category == "accumulation_verb"

    def test_alias_earns_resolves_to_earn(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "earns")
        assert entry is not None
        assert entry.lemma == "earn"

    def test_alias_spent_resolves_to_spend(self) -> None:
        lex = load_lexicon()
        entry = lookup(lex, "spent")
        assert entry is not None
        assert entry.lemma == "spend"

    def test_unknown_surface_returns_none(self) -> None:
        lex = load_lexicon()
        assert lookup(lex, "xyzzy") is None

    def test_unknown_proper_noun_returns_none(self) -> None:
        lex = load_lexicon()
        assert lookup(lex, "Zaphod") is None

    def test_case_insensitive_lookup(self) -> None:
        lex = load_lexicon()
        lower = lookup(lex, "earn")
        upper = lookup(lex, "EARN")
        assert lower is not None
        assert upper is not None
        assert lower.lemma == upper.lemma


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_loads_have_equal_hash(self) -> None:
        lex1 = load_lexicon()
        lex2 = load_lexicon()
        assert hash(lex1) == hash(lex2)

    def test_two_loads_are_equal(self) -> None:
        lex1 = load_lexicon()
        lex2 = load_lexicon()
        assert lex1 == lex2


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_same_object_returned(self) -> None:
        lex1 = load_lexicon()
        lex2 = load_lexicon()
        assert lex1 is lex2, "Second call must return the cached object"

    def test_explicit_path_cache_hit(self, tmp_path: Path) -> None:
        import shutil
        real_pack = (
            Path(__file__).resolve().parent.parent
            / "language_packs" / "data" / "en_core_math_v1"
        )
        fake_pack = tmp_path / "en_core_math_v1"
        shutil.copytree(real_pack, fake_pack)

        a = load_lexicon(fake_pack)
        b = load_lexicon(fake_pack)
        assert a is b


# ---------------------------------------------------------------------------
# Mutual exclusion
# ---------------------------------------------------------------------------


class TestMutualExclusion:
    def test_surface_in_two_categories_raises(self, tmp_path: Path) -> None:
        """A surface appearing in two different categories raises LexiconLoadError."""
        import shutil

        real_pack = (
            Path(__file__).resolve().parent.parent
            / "language_packs" / "data" / "en_core_math_v1"
        )
        conflict_pack = tmp_path / "en_core_math_v1"
        shutil.copytree(real_pack, conflict_pack)

        # Inject a conflicting entry: "earn" already exists as accumulation_verb;
        # add it again as depletion_verb in the depletion_verb source file.
        conflict_entry = json.dumps({
            "lemma": "earn",
            "category": "depletion_verb",
            "aliases": [],
            "provenance": "test-conflict",
        })
        depletion_file = conflict_pack / "lexicon" / "depletion_verb.jsonl"
        with open(depletion_file, "a", encoding="utf-8") as f:
            f.write("\n" + conflict_entry + "\n")

        # Recompute and patch the manifest checksum to match the (unmodified)
        # compiled lexicon.jsonl — the conflict is in the source files only.
        compiled_path = conflict_pack / "lexicon.jsonl"
        actual_sha256 = hashlib.sha256(compiled_path.read_bytes()).hexdigest()
        manifest_path = conflict_pack / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["checksum"] = actual_sha256
        manifest_path.write_text(json.dumps(manifest))

        with pytest.raises(LexiconLoadError, match="[Mm]utual"):
            load_lexicon(conflict_pack)
