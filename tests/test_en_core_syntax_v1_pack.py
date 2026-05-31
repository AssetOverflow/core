"""``en_core_syntax_v1`` — foundational syntax vocabulary pack tests.

This pack is the first foundation-curriculum substrate pack.  It does not
implement a parser.  It seeds the lower-level vocabulary needed for later
claim parsing, relation binding, clause attachment, conditional structure,
reference handling, polarity, and evidence-span discipline.

Contracts pinned here:

- checksum-verified load through ``language_packs.compiler.load_pack``;
- every entry's primary semantic namespace is syntax/claim/provenance;
- contiguous zero-padded entry ids;
- one gloss per lexicon lemma, with manifest checksum discipline;
- resolver registration after polarity and before kinship/domain relation packs;
- prior high-frequency pack lemma routing remains unchanged.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from chat.pack_resolver import (
    DEFAULT_RESOLVABLE_PACK_IDS,
    clear_resolver_cache,
    resolve_gloss,
    resolve_lemma,
)
from language_packs.compiler import load_pack


PACK_ID = "en_core_syntax_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 24
EXPECTED_POS_COUNTS = {"NOUN": 24}
EXPECTED_LEMMAS: tuple[str, ...] = (
    "subject",
    "predicate",
    "agent",
    "patient",
    "object",
    "modifier",
    "clause",
    "sentence",
    "phrase",
    "antecedent",
    "consequent",
    "referent",
    "anaphor",
    "qualifier",
    "scope",
    "polarity",
    "coordination",
    "conjunction",
    "disjunction",
    "negation",
    "exception",
    "comparison",
    "attachment",
    "evidence_span",
)

_ALLOWED_PRIMARY_PREFIXES = ("syntax.", "claim.", "provenance.")
_EXPECTED_PROVENANCE = ["foundation_syntax_v1:reviewed:2026-05-30"]


def _read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text("utf-8").splitlines()
        if line.strip()
    ]


def _read_lexicon() -> list[dict]:
    return _read_jsonl(_PACK_ROOT / "lexicon.jsonl")


def _read_glosses() -> list[dict]:
    return _read_jsonl(_PACK_ROOT / "glosses.jsonl")


def test_pack_loads_with_matching_checksum() -> None:
    manifest, manifold = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert len(manifold) == EXPECTED_TOTAL


def test_manifest_checksums_match_pack_bytes() -> None:
    manifest = json.loads((_PACK_ROOT / "manifest.json").read_text("utf-8"))
    assert manifest["checksum"] == hashlib.sha256(
        (_PACK_ROOT / "lexicon.jsonl").read_bytes()
    ).hexdigest()
    assert manifest["glosses_checksum"] == hashlib.sha256(
        (_PACK_ROOT / "glosses.jsonl").read_bytes()
    ).hexdigest()


def test_pos_distribution_matches_design() -> None:
    assert dict(Counter(e["pos"] for e in _read_lexicon())) == EXPECTED_POS_COUNTS


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    assert {manifold.get_word_at(i) for i in range(len(manifold))} == set(EXPECTED_LEMMAS)


def test_every_entry_has_foundational_primary_namespace() -> None:
    for entry in _read_lexicon():
        primary = entry["semantic_domains"][0]
        assert primary.startswith(_ALLOWED_PRIMARY_PREFIXES), entry


def test_every_entry_has_reviewed_foundation_provenance() -> None:
    for entry in _read_lexicon():
        assert entry["provenance_ids"] == _EXPECTED_PROVENANCE, entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-syntax-{i:03d}", entry["entry_id"]


def test_glosses_are_one_to_one_with_lexicon() -> None:
    lexicon_lemmas = {entry["lemma"] for entry in _read_lexicon()}
    gloss_lemmas = {entry["lemma"] for entry in _read_glosses()}
    assert gloss_lemmas == lexicon_lemmas


def test_gloss_entries_use_strict_definitional_overlay_shape() -> None:
    for entry in _read_glosses():
        assert set(entry) == {
            "lemma",
            "gloss",
            "pos",
            "provenance_ids",
            "definitional_atoms",
            "predicates_invited",
            "definition_version",
        }
        assert entry["provenance_ids"] == _EXPECTED_PROVENANCE
        assert entry["definition_version"] == 1
        assert isinstance(entry["definitional_atoms"], list)
        assert isinstance(entry["predicates_invited"], list)


def test_pack_registered_after_polarity_before_relation_content() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    assert DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_polarity_v1") < DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)
    assert DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID) < DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_relations_v1")
    assert DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID) < DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_relations_v2")


def test_resolver_routes_syntax_lemmas_to_this_pack() -> None:
    clear_resolver_cache()
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == PACK_ID, (
            f"{lemma!r} resolved to {resolved}"
        )
        assert resolved[1][0].startswith(_ALLOWED_PRIMARY_PREFIXES)


def test_gloss_resolver_routes_syntax_lemmas_to_this_pack() -> None:
    clear_resolver_cache()
    for lemma in ("subject", "predicate", "antecedent", "negation", "evidence_span"):
        resolved = resolve_gloss(lemma)
        assert resolved is not None, lemma
        pack_id, pos, gloss = resolved
        assert pack_id == PACK_ID
        assert pos == "NOUN"
        assert isinstance(gloss, str) and len(gloss.split()) >= 4


def test_prior_pack_lemma_resolution_unchanged() -> None:
    for lemma, expected in (
        ("truth", "en_core_cognition_v1"),
        ("doubt", "en_core_meta_v1"),
        ("true", "en_core_attitude_v1"),
        ("now", "en_core_temporal_v1"),
        ("do", "en_core_action_v1"),
        ("all", "en_core_quantitative_v1"),
        ("place", "en_core_spatial_v1"),
        ("cause", "en_core_causation_v1"),
        ("never", "en_core_polarity_v1"),
        ("parent", "en_core_relations_v1"),
        ("mother", "en_core_relations_v2"),
    ):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == expected
