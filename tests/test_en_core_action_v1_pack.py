"""``en_core_action_v1`` — action verb pack tests.

The action pack adds common-action verb coverage absent from prior
packs.  Cognition verbs are reasoning/relation operators; meta verbs
are speech/mental/perceptual; this pack covers what an agent *does*:
performing, creating, changing, moving, possessing.  26 entries:

  - action.doing.*       — do make perform conduct execute carry achieve accomplish (8)
  - action.creating.*    — create build form produce generate develop (6)
  - action.changing.*    — change transform                            (2)
  - action.moving.*      — move go come send receive                   (5)
  - action.possessing.*  — get take give keep use                      (5)

Contracts pinned: checksum-verified load, all entries POS=VERB,
attitude.*-style primary-domain invariant, no collision with any of
the 6 prior English packs, mounted by default, registered after
temporal in DEFAULT_RESOLVABLE_PACK_IDS, prior-pack resolution
unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS, resolve_lemma
from core.config import RuntimeConfig
from language_packs.compiler import load_pack


PACK_ID = "en_core_action_v1"
_PACK_ROOT = Path(__file__).resolve().parent.parent / "language_packs" / "data" / PACK_ID

EXPECTED_TOTAL = 27

# Canonical base lemmas (resolver-addressable). Does not include surface
# inflections like 'makes' which are stored in the manifold as separate
# entries but are not independently resolvable via the lemma resolver.
EXPECTED_LEMMAS: tuple[str, ...] = (
    "do", "make", "perform", "conduct", "execute", "carry", "achieve",
    "accomplish", "create", "build", "form", "produce", "generate",
    "develop", "change", "transform", "move", "go", "come", "send",
    "receive", "get", "take", "give", "keep", "use",
)


def _read_lexicon() -> list[dict]:
    path = _PACK_ROOT / "lexicon.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_pack_loads_with_matching_checksum() -> None:
    manifest, manifold = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert all(c in "0123456789abcdef" for c in manifest.checksum)
    assert len(manifold) == EXPECTED_TOTAL


def test_all_entries_are_verbs() -> None:
    for entry in _read_lexicon():
        assert entry["pos"] == "VERB", entry["entry_id"]
        assert "verb" in entry["morphology_tags"], entry["entry_id"]


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    surfaces = {manifold.get_word_at(i) for i in range(len(manifold))}
    assert set(EXPECTED_LEMMAS).issubset(surfaces), (
        f"missing lemmas: {set(EXPECTED_LEMMAS) - surfaces}"
    )


def test_every_entry_has_action_namespace_primary_domain() -> None:
    for entry in _read_lexicon():
        domains = entry["semantic_domains"]
        assert isinstance(domains, list) and domains, entry
        assert domains[0].startswith("action."), (
            f"entry {entry['entry_id']} primary domain {domains[0]!r} "
            f"is not in the action.* namespace"
        )


def test_no_collision_with_prior_packs() -> None:
    prior_lemmas: set[str] = set()
    pack_root = _PACK_ROOT.parent
    for pack in (
        "en_core_cognition_v1",
        "en_core_meta_v1",
        "en_core_attitude_v1",
        "en_core_temporal_v1",
        "en_core_relations_v1",
        "en_core_relations_v2",
    ):
        for line in (pack_root / pack / "lexicon.jsonl").read_text("utf-8").splitlines():
            if line.strip():
                prior_lemmas.add(json.loads(line)["lemma"].lower())
    for entry in _read_lexicon():
        lemma = entry["lemma"].lower()
        assert lemma not in prior_lemmas, (
            f"lemma {lemma!r} collides with a prior-mounted pack"
        )


def test_provenance_is_seed_core_action_v1() -> None:
    for entry in _read_lexicon():
        assert "seed:core_action_v1" in entry["provenance_ids"], entry


def test_entry_ids_contiguous_and_zero_padded() -> None:
    entries = sorted(_read_lexicon(), key=lambda d: d["entry_id"])
    for i, entry in enumerate(entries, start=1):
        assert entry["entry_id"] == f"en-core-action-{i:03d}", entry["entry_id"]


def test_pack_mounted_in_default_runtime_config() -> None:
    cfg = RuntimeConfig()
    assert PACK_ID in cfg.input_packs


def test_pack_registered_after_prior_content_packs() -> None:
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS
    for earlier in (
        "en_core_cognition_v1",
        "en_core_meta_v1",
        "en_core_attitude_v1",
        "en_core_temporal_v1",
    ):
        assert DEFAULT_RESOLVABLE_PACK_IDS.index(earlier) < DEFAULT_RESOLVABLE_PACK_IDS.index(PACK_ID)


def test_resolver_routes_action_lemmas_to_this_pack() -> None:
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None, f"lemma {lemma!r} did not resolve"
        pack_id, domains = resolved
        assert pack_id == PACK_ID, (
            f"lemma {lemma!r} resolved to {pack_id} instead of {PACK_ID}"
        )
        assert domains[0].startswith("action.")


def test_prior_pack_lemma_resolution_unchanged() -> None:
    for lemma, expected in (
        ("truth", "en_core_cognition_v1"),
        ("doubt", "en_core_meta_v1"),
        ("true", "en_core_attitude_v1"),
        ("now", "en_core_temporal_v1"),
    ):
        resolved = resolve_lemma(lemma)
        assert resolved is not None and resolved[0] == expected
