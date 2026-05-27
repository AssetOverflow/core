"""Contract tests for the ``en_core_math_v1`` math seed lexicon pack.

Pins:
  - Pack loads via ``load_pack("en_core_math_v1")`` with passing checksum.
  - Lemma counts per category match the ported source whitelists (regression).
  - Zero overlap between mutually-exclusive categories.
  - Every lemma entry carries the expected provenance tag.
  - Per-category JSONL files in lexicon/ are structurally valid.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from language_packs.compiler import load_pack, load_pack_entries

PACK_ID = "en_core_math_v1"

_PACK_DIR = (
    Path(__file__).parent.parent / "language_packs" / "data" / PACK_ID
)
_LEXICON_DIR = _PACK_DIR / "lexicon"

PROVENANCE_TAG = "ported_from_math_candidate_parser_2026-05-26"

# Expected lemma counts sourced directly from the ported whitelist constants.
# Change only when the source constant changes AND an ADR ratifies the delta.
EXPECTED_CATEGORY_COUNTS: dict[str, int] = {
    "accumulation_verb":         17,
    "depletion_verb":            15,
    "transfer_verb":             7,
    "currency_unit_noun":        8,
    "entity_pronoun":            4,
    "proper_noun_entity_female": 62,
    "proper_noun_entity_male":   76,
    "possession_verb":           1,
    "capacity_verb":             13,
    "question_open":             2,
    "residual_modifier":         3,
}

EXPECTED_TOTAL = sum(EXPECTED_CATEGORY_COUNTS.values())  # 208


def _read_category(cat: str) -> list[dict]:
    path = _LEXICON_DIR / f"{cat}.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ---------------------------------------------------------------------------
# Pack-load + checksum
# ---------------------------------------------------------------------------

def test_pack_loads_with_matching_checksum() -> None:
    """``load_pack`` raises ``ValueError`` on checksum mismatch.

    A clean load proves manifest.checksum equals SHA-256 of bytes on disk —
    per CLAUDE.md §Semantic Pack Discipline.
    """
    manifest, _ = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert all(c in "0123456789abcdef" for c in manifest.checksum)


def test_total_lemma_count() -> None:
    """Total entries in lexicon.jsonl must equal sum of per-category counts."""
    entries = load_pack_entries(PACK_ID)
    assert len(entries) == EXPECTED_TOTAL, (
        f"Expected {EXPECTED_TOTAL} entries, got {len(entries)}. "
        "A source whitelist changed without an ADR update."
    )


# ---------------------------------------------------------------------------
# Per-category file structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cat", sorted(EXPECTED_CATEGORY_COUNTS))
def test_category_file_exists(cat: str) -> None:
    path = _LEXICON_DIR / f"{cat}.jsonl"
    assert path.exists(), f"lexicon/{cat}.jsonl missing"


@pytest.mark.parametrize("cat,expected", sorted(EXPECTED_CATEGORY_COUNTS.items()))
def test_category_lemma_count(cat: str, expected: int) -> None:
    rows = _read_category(cat)
    assert len(rows) == expected, (
        f"{cat}: expected {expected} lemmas, got {len(rows)}. "
        "Source whitelist changed — update EXPECTED_CATEGORY_COUNTS and the ADR."
    )


@pytest.mark.parametrize("cat", sorted(EXPECTED_CATEGORY_COUNTS))
def test_category_provenance(cat: str) -> None:
    """Every lemma in every per-category file must carry the provenance tag."""
    for row in _read_category(cat):
        assert row.get("provenance") == PROVENANCE_TAG, (
            f"{cat}: lemma {row.get('lemma')!r} has wrong provenance "
            f"{row.get('provenance')!r}; expected {PROVENANCE_TAG!r}"
        )


@pytest.mark.parametrize("cat", sorted(EXPECTED_CATEGORY_COUNTS))
def test_category_field_is_set(cat: str) -> None:
    for row in _read_category(cat):
        assert row.get("category") == cat, (
            f"lemma {row.get('lemma')!r} in {cat}.jsonl has "
            f"category={row.get('category')!r}"
        )


# ---------------------------------------------------------------------------
# Mutual exclusivity
# ---------------------------------------------------------------------------

def test_accumulation_depletion_disjoint() -> None:
    """accumulation_verb ∩ depletion_verb must be empty."""
    acc = {r["lemma"] for r in _read_category("accumulation_verb")}
    dep = {r["lemma"] for r in _read_category("depletion_verb")}
    overlap = acc & dep
    assert not overlap, (
        f"Verbs in both accumulation_verb and depletion_verb: {sorted(overlap)}. "
        "Each verb must have a unique polarity assignment."
    )


def test_accumulation_transfer_disjoint() -> None:
    """accumulation_verb ∩ transfer_verb must be empty."""
    acc = {r["lemma"] for r in _read_category("accumulation_verb")}
    trn = {r["lemma"] for r in _read_category("transfer_verb")}
    overlap = acc & trn
    assert not overlap, (
        f"Verbs in both accumulation_verb and transfer_verb: {sorted(overlap)}"
    )


def test_depletion_transfer_disjoint() -> None:
    """depletion_verb ∩ transfer_verb must be empty.

    Transfer verbs (give, send, …) were explicitly removed from
    depletion_verb to resolve the dual-entry in SUBTRACT_VERBS/TRANSFER_VERBS.
    """
    dep = {r["lemma"] for r in _read_category("depletion_verb")}
    trn = {r["lemma"] for r in _read_category("transfer_verb")}
    overlap = dep & trn
    assert not overlap, (
        f"Verbs in both depletion_verb and transfer_verb: {sorted(overlap)}"
    )


def test_capacity_verb_disjoint_from_accumulation() -> None:
    """capacity_verb ∩ accumulation_verb must be empty (make/pick/pack placed in capacity)."""
    cap = {r["lemma"] for r in _read_category("capacity_verb")}
    acc = {r["lemma"] for r in _read_category("accumulation_verb")}
    overlap = cap & acc
    assert not overlap, (
        f"Verbs in both capacity_verb and accumulation_verb: {sorted(overlap)}. "
        "make/pick/pack belong exclusively to capacity_verb."
    )


def test_female_male_names_disjoint() -> None:
    """Female and male name lists must not share any lemma."""
    female = {r["lemma"] for r in _read_category("proper_noun_entity_female")}
    male = {r["lemma"] for r in _read_category("proper_noun_entity_male")}
    overlap = female & male
    assert not overlap, (
        f"Names in both female and male lists: {sorted(overlap)}"
    )


# ---------------------------------------------------------------------------
# Compiled entry provenance
# ---------------------------------------------------------------------------

def test_every_compiled_entry_has_provenance() -> None:
    """Every entry in lexicon.jsonl carries the provenance tag in provenance_ids."""
    entries = load_pack_entries(PACK_ID)
    missing = [e.lemma for e in entries if PROVENANCE_TAG not in (e.provenance_ids or ())]
    assert not missing, (
        f"Entries missing provenance tag: {missing[:10]}"
    )


def test_every_compiled_entry_has_two_semantic_domains() -> None:
    """Each entry must carry ≥2 semantic domains for surface composition headroom."""
    entries = load_pack_entries(PACK_ID)
    thin = [e.lemma for e in entries if len(e.semantic_domains) < 2]
    assert not thin, f"Entries with <2 semantic domains: {thin[:10]}"
