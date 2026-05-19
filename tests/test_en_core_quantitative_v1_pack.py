"""``en_core_quantitative_v1`` — quantifier + numeric basics pack tests.

Quantifiers and basic numerics had zero coverage in any prior pack —
queries like "What does some mean?" or "What is a few?" all fell
through to OOV.  24 entries across:

  - quantitative.universal.*    (6 DET) all every each both none neither
  - quantitative.existential.*  (6 DET) some any several few many much
  - quantitative.comparative.*  (6 DET) more less fewer most least enough
  - quantitative.numeric.*      (3 NUM) one two three
  - quantitative.unit.*         (3 mix) single (ADJ) half (NOUN) whole (ADJ)

Mixed POS distribution (18 DET / 3 NUM / 2 ADJ / 1 NOUN) — the resolver
is POS-agnostic, surface composition uses semantic_domains.

Contracts pinned: checksum-verified load, primary-domain namespace
``quantitative.*``, no collision with the 7 prior packs, mounted by
default, registered after en_core_action_v1, prior-pack resolution
unchanged.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_quantitative_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 24
EXPECTED_POS_COUNTS = {"DET": 18, "NUM": 3, "ADJ": 2, "NOUN": 1}

EXPECTED_LEMMAS: tuple[str, ...] = (
    "all", "every", "each", "both", "none", "neither",
    "some", "any", "several", "few", "many", "much",
    "more", "less", "fewer", "most", "least", "enough",
    "one", "two", "three", "single", "half", "whole",
)


def _read_lexicon() -> list[dict]:
    return [
        json.loads(line)
        for line in (_PACK_ROOT / "lexicon.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]


def test_pack_loads_with_matching_checksum() -> None:
    manifest, manifold = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert len(manifold) == EXPECTED_TOTAL


def test_pos_distribution_matches_design() -> None:
    pos_counts = Counter(e["pos"] for e in _read_lexicon())
    assert dict(pos_counts) == EXPECTED_POS_COUNTS


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    assert {manifold.get_word_at(i) for i in range(len(manifold))} == set(EXPECTED_LEMMAS)


def test_every_entry_has_quantitative_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        assert entry["semantic_domains"][0].startswith("quantitative."), entry


def test_no_collision_with_prior_packs() -> None:
    prior: set[str] = set()
    for pack in (
        "en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1",
        "en_core_temporal_v1", "en_core_action_v1",
        "en_core_relations_v1", "en_core_relations_v2",
    ):
        for line in (_PACK_ROOT.parent / pack / "lexicon.jsonl").read_text("utf-8").splitlines():
            if line.strip():
                prior.add(json.loads(line)["lemma"].lower())
    for entry in _read_lexicon():
        assert entry["lemma"].lower() not in prior, entry


def test_provenance_is_seed_core_quant_v1() -> None:
    for entry in _read_lexicon():
        assert entry["provenance_ids"] == ["seed:core_quant_v1"], entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-quant-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    assert PACK_ID in RuntimeConfig().input_packs


def test_pack_registered_after_prior_content_packs() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    for earlier in (
        "en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1",
        "en_core_temporal_v1", "en_core_action_v1",
    ):
        assert DEFAULT_RESOLVABLE_PACK_IDS.index(earlier) < DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)


def test_resolver_routes_quantitative_lemmas_to_this_pack() -> None:
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == PACK_ID, (
            f"{lemma!r} resolved to {resolved}"
        )
        assert resolved[1][0].startswith("quantitative.")


def test_prior_pack_lemma_resolution_unchanged() -> None:
    for lemma, expected in (
        ("truth", "en_core_cognition_v1"),
        ("doubt", "en_core_meta_v1"),
        ("true", "en_core_attitude_v1"),
        ("now", "en_core_temporal_v1"),
        ("do", "en_core_action_v1"),
    ):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == expected
