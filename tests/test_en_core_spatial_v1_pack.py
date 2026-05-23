"""``en_core_spatial_v1`` — spatial vocabulary pack tests.

Spatial vocabulary had zero coverage in any prior pack — *here*,
*there*, *near*, *above*, *place*, *location* all fell through to
OOV.  24 entries across:

  - spatial.deictic.*    — here, there
  - spatial.direction.*  — forward, backward, left, up, down  (5 ADV)
  - spatial.relation.*   — near, far, above, below, inside, outside,
                           between, beyond  (8 ADP)
  - spatial.noun.*       — place, location, area, region, space, end,
                           top, bottom, side  (9 NOUN)

POS mix (7 ADV / 8 ADP / 9 NOUN).  The composer is POS-agnostic.

Contracts pinned: checksum-verified load, primary-domain namespace
``spatial.*``, no collision with the 8 prior packs (notably ``right``
is in en_core_attitude_v1 as evaluative.positive, so spatial-direction
``right`` was deliberately omitted), mounted by default, registered
after en_core_quantitative_v1, prior-pack resolution unchanged.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_spatial_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 25
EXPECTED_POS_COUNTS = {"ADV": 7, "ADP": 8, "NOUN": 10}

# Manifold surfaces include an inflected plural ("places") under a distinct
# entry id (en-core-spatial-025) added during the adr-0085-style-v2 review.
EXPECTED_LEMMAS: tuple[str, ...] = (
    "here", "there", "forward", "backward", "left", "up", "down",
    "near", "far", "above", "below", "inside", "outside", "between", "beyond",
    "place", "places", "location", "area", "region", "space", "end", "top",
    "bottom", "side",
)

_ALLOWED_PROVENANCE_SHAPES: frozenset[tuple[str, ...]] = frozenset({
    ("seed:core_spatial_v1",),
    ("seed:core_spatial", "adr-0085-style-v2:reviewed:2026-05-22"),
})


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


def test_every_entry_has_spatial_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        assert entry["semantic_domains"][0].startswith("spatial."), entry


def test_no_collision_with_prior_packs() -> None:
    prior: set[str] = set()
    for pack in (
        "en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1",
        "en_core_temporal_v1", "en_core_action_v1", "en_core_quantitative_v1",
        "en_core_relations_v1", "en_core_relations_v2",
    ):
        for line in (_PACK_ROOT.parent / pack / "lexicon.jsonl").read_text("utf-8").splitlines():
            if line.strip():
                prior.add(json.loads(line)["lemma"].lower())
    for entry in _read_lexicon():
        assert entry["lemma"].lower() not in prior, entry


def test_provenance_is_seed_core_spatial_v1() -> None:
    for entry in _read_lexicon():
        shape = tuple(entry["provenance_ids"])
        assert shape in _ALLOWED_PROVENANCE_SHAPES, entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-spatial-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    assert PACK_ID in RuntimeConfig().input_packs


def test_pack_registered_after_prior_content_packs() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    for earlier in (
        "en_core_cognition_v1", "en_core_meta_v1", "en_core_attitude_v1",
        "en_core_temporal_v1", "en_core_action_v1", "en_core_quantitative_v1",
    ):
        assert DEFAULT_RESOLVABLE_PACK_IDS.index(earlier) < DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)


def test_resolver_routes_spatial_lemmas_to_this_pack() -> None:
    # "places" is a plural surface (entry en-core-spatial-025), not a lemma —
    # the resolver only resolves on lemma form, so exclude inflected surfaces.
    for lemma in EXPECTED_LEMMAS:
        if lemma == "places":
            continue
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == PACK_ID, (
            f"{lemma!r} resolved to {resolved}"
        )
        assert resolved[1][0].startswith("spatial.")


def test_right_remains_in_attitude_pack_not_spatial() -> None:
    """``right`` was deliberately excluded from spatial-direction
    because en_core_attitude_v1 already owns it as evaluative.positive.
    Verify the first-match-wins resolver preserves attitude's claim."""
    resolved = resolve_lemma("right")
    assert resolved is not None and resolved[0] == "en_core_attitude_v1"
    assert resolved[1][0].startswith("attitude.evaluative.")


def test_prior_pack_lemma_resolution_unchanged() -> None:
    for lemma, expected in (
        ("truth", "en_core_cognition_v1"),
        ("doubt", "en_core_meta_v1"),
        ("true", "en_core_attitude_v1"),
        ("now", "en_core_temporal_v1"),
        ("do", "en_core_action_v1"),
        ("all", "en_core_quantitative_v1"),
    ):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == expected
