"""``en_core_causation_v1`` — causation vocabulary pack tests.

Cognition pack already owns ``cause``/``because``; this pack extends
the causal apparatus with effect nouns, causative verbs not in
en_core_action_v1, and causal adjectives.  15 entries:

  - causation.effect.*      effect result consequence outcome impact influence  (6 NOUN)
  - causation.verb.*        trigger induce yield enable prevent drive            (6 VERB)
  - causation.adjective.*   causal resultant consequent                          (3 ADJ)
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_causation_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 15
EXPECTED_POS_COUNTS = {"NOUN": 6, "VERB": 6, "ADJ": 3}

EXPECTED_LEMMAS: tuple[str, ...] = (
    "effect", "result", "consequence", "outcome", "impact", "influence",
    "trigger", "induce", "yield", "enable", "prevent", "drive",
    "causal", "resultant", "consequent",
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
    assert dict(Counter(e["pos"] for e in _read_lexicon())) == EXPECTED_POS_COUNTS


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    assert {manifold.get_word_at(i) for i in range(len(manifold))} == set(EXPECTED_LEMMAS)


def test_every_entry_has_causation_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        assert entry["semantic_domains"][0].startswith("causation."), entry


def test_no_collision_with_prior_packs() -> None:
    prior: set[str] = set()
    for pack in (
        "en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1",
        "en_core_temporal_v1", "en_core_action_v1", "en_core_quantitative_v1",
        "en_core_spatial_v1", "en_core_relations_v1", "en_core_relations_v2",
    ):
        for line in (_PACK_ROOT.parent / pack / "lexicon.jsonl").read_text("utf-8").splitlines():
            if line.strip():
                prior.add(json.loads(line)["lemma"].lower())
    for entry in _read_lexicon():
        assert entry["lemma"].lower() not in prior, entry


def test_provenance_is_seed_core_causation_v1() -> None:
    for entry in _read_lexicon():
        assert entry["provenance_ids"] == ["seed:core_causation_v1"], entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-causation-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    assert PACK_ID in RuntimeConfig().input_packs


def test_pack_registered_after_prior_content_packs() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    for earlier in (
        "en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1",
        "en_core_temporal_v1", "en_core_action_v1", "en_core_quantitative_v1",
        "en_core_spatial_v1",
    ):
        assert DEFAULT_RESOLVABLE_PACK_IDS.index(earlier) < DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)


def test_resolver_routes_causation_lemmas_to_this_pack() -> None:
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == PACK_ID
        assert resolved[1][0].startswith("causation.")


def test_cause_remains_in_cognition_v1() -> None:
    """``cause`` was deliberately excluded — en_core_cognition_v1
    already owns it (both NOUN and VERB)."""
    resolved = resolve_lemma("cause")
    assert resolved is not None and resolved[0] == "en_core_cognition_v1"


def test_prior_pack_lemma_resolution_unchanged() -> None:
    for lemma, expected in (
        ("truth", "en_core_cognition_v1"),
        ("doubt", "en_core_meta_v1"),
        ("true", "en_core_attitude_v1"),
        ("now", "en_core_temporal_v1"),
        ("do", "en_core_action_v1"),
        ("all", "en_core_quantitative_v1"),
        ("here", "en_core_spatial_v1"),
    ):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == expected
