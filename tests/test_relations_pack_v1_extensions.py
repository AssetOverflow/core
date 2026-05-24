"""Regression tests for additive ``en_core_relations_v1`` content extension.

This file deliberately tests only existing schemas and live resolver
behavior.  It does not introduce new pack types, new validators, or new
manifest fields.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from chat.pack_resolver import resolve_lemma
from chat.teaching_grounding import TeachingCorpusSpec, _load_corpus


PACK_ID = "en_core_relations_v1"
PACK_DIR = Path("language_packs/data") / PACK_ID
LEXICON_PATH = PACK_DIR / "lexicon.jsonl"
MANIFEST_PATH = PACK_DIR / "manifest.json"
CHAINS_PATH = Path("teaching/relations_chains/relations_chains_v1.jsonl")

BASELINE_LEMMA_COUNT = 8
EXPECTED_ADDED_LEMMAS = frozenset({
    "advisor",
    "apprentice",
    "caregiver",
    "colleague",
    "cousin",
    "elder",
    "friend",
    "guardian",
    "manager",
    "mentor",
    "neighbor",
    "relative",
    "supervisor",
    "teammate",
})
EXPECTED_TOTAL_LEMMA_COUNT = BASELINE_LEMMA_COUNT + len(EXPECTED_ADDED_LEMMAS)

BASELINE_CHAIN_COUNT = 7
EXPECTED_ADDED_CHAIN_COUNT = 14
EXPECTED_TOTAL_CHAIN_COUNT = BASELINE_CHAIN_COUNT + EXPECTED_ADDED_CHAIN_COUNT


def _lexicon_entries() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in LEXICON_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _chain_entries() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in CHAINS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_relations_v1_entry_count_delta() -> None:
    entries = _lexicon_entries()
    assert len(entries) == EXPECTED_TOTAL_LEMMA_COUNT
    added = {
        str(e["lemma"])
        for e in entries
        if "relations_extension_v1:reviewed:2026-05-23" in e.get("provenance_ids", [])
    }
    assert added == EXPECTED_ADDED_LEMMAS


def test_relations_v1_has_no_duplicate_lemma_or_surface_keys() -> None:
    entries = _lexicon_entries()
    lemmas = [str(e["lemma"]) for e in entries]
    surfaces = [str(e["surface"]) for e in entries]
    assert len(lemmas) == len(set(lemmas))
    assert len(surfaces) == len(set(surfaces))


def test_manifest_checksum_matches_lexicon_bytes() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actual = hashlib.sha256(LEXICON_PATH.read_bytes()).hexdigest()
    assert manifest["checksum"] == actual


def test_all_added_lemmas_resolve_via_cross_pack_resolver() -> None:
    for lemma in sorted(EXPECTED_ADDED_LEMMAS):
        resolved = resolve_lemma(lemma)
        assert resolved is not None, lemma
        pack_id, domains = resolved
        assert pack_id == PACK_ID
        assert domains


def test_relations_v1_chain_count_delta_and_loadability() -> None:
    chains = _chain_entries()
    assert len(chains) == EXPECTED_TOTAL_CHAIN_COUNT
    added = [
        c for c in chains
        if c.get("provenance") == "relations_extension_v1:reviewed:2026-05-23"
    ]
    assert len(added) == EXPECTED_ADDED_CHAIN_COUNT

    loaded = _load_corpus(TeachingCorpusSpec(
        corpus_id="relations_chains_v1",
        path=CHAINS_PATH,
        pack_id=PACK_ID,
    ))
    assert len(loaded) == EXPECTED_TOTAL_CHAIN_COUNT
