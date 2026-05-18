"""Phase 2.4 — ``en_core_relations_v2`` (pronouns + role-fillers) tests.

The v2 pack carries 8 specialization lemmas — mother/father, son/daughter,
brother/sister, grandparent/grandchild — each a typed specialization of
a v1 primitive (mother is-a parent, daughter is-a child, etc.).

The contract these tests pin:

  - Checksum-verified load.
  - All 8 lemmas present with the expected primary domain.
  - No accidental cross-pack collision with v1 OR cognition.
  - Pack IS in default ``RuntimeConfig.input_packs`` (mounted on
    the live runtime by default — paired with v2-internal reviewed
    chains so DEFINITION + CAUSE + VERIFICATION all ground).
  - The companion corpus ``relations_chains_v2.jsonl`` is registered.
"""

from __future__ import annotations

from language_packs.compiler import load_pack, load_pack_entries


PACK_ID = "en_core_relations_v2"

EXPECTED_LEMMAS: tuple[str, ...] = (
    "mother",
    "father",
    "daughter",
    "son",
    "brother",
    "sister",
    "grandparent",
    "grandchild",
)


EXPECTED_PRIMARY_DOMAINS: dict[str, str] = {
    "mother":       "kinship.parent.female",
    "father":       "kinship.parent.male",
    "daughter":     "kinship.child.female",
    "son":          "kinship.child.male",
    "brother":      "kinship.sibling.male",
    "sister":       "kinship.sibling.female",
    "grandparent":  "kinship.ascendant.transitive_1step",
    "grandchild":   "kinship.descendant.transitive_1step",
}


def test_pack_loads_with_matching_checksum() -> None:
    manifest, manifold = load_pack(PACK_ID)
    assert manifest.pack_id == PACK_ID
    assert len(manifest.checksum) == 64
    assert all(c in "0123456789abcdef" for c in manifest.checksum)
    assert len(manifold) == len(EXPECTED_LEMMAS)


def test_all_expected_lemmas_present() -> None:
    _, manifold = load_pack(PACK_ID)
    surfaces = {manifold.get_word_at(i) for i in range(len(manifold))}
    assert surfaces == set(EXPECTED_LEMMAS)


def test_each_lemma_carries_expected_primary_domain() -> None:
    entries = load_pack_entries(PACK_ID)
    by_lemma = {e.lemma: e for e in entries}
    for lemma, expected_primary in EXPECTED_PRIMARY_DOMAINS.items():
        assert lemma in by_lemma, f"missing lemma: {lemma}"
        actual = by_lemma[lemma].semantic_domains
        assert actual, f"{lemma!r} has empty semantic_domains"
        assert actual[0] == expected_primary, (
            f"{lemma!r}: primary domain drifted from {expected_primary!r} "
            f"to {actual[0]!r}"
        )


def test_every_lemma_has_multiple_semantic_domains() -> None:
    entries = load_pack_entries(PACK_ID)
    for entry in entries:
        assert len(entry.semantic_domains) >= 2, (
            f"{entry.lemma!r} has only {len(entry.semantic_domains)} domains"
        )


def test_no_lemma_collision_with_v1_or_cognition() -> None:
    _, v2_manifold = load_pack(PACK_ID)
    _, v1_manifold = load_pack("en_core_relations_v1")
    _, cog_manifold = load_pack("en_core_cognition_v1")
    v2 = {v2_manifold.get_word_at(i) for i in range(len(v2_manifold))}
    v1 = {v1_manifold.get_word_at(i) for i in range(len(v1_manifold))}
    cog = {cog_manifold.get_word_at(i) for i in range(len(cog_manifold))}
    assert not (v2 & v1), f"v2 collides with v1: {v2 & v1}"
    assert not (v2 & cog), f"v2 collides with cognition: {v2 & cog}"


def test_pack_is_in_default_input_packs() -> None:
    """The v2 pack is mounted by default — paired with reviewed
    v2-internal chains so DEFINITION/CAUSE/VERIFICATION on v2 lemmas
    all ground without falling through to OOV."""
    from core.config import RuntimeConfig
    assert PACK_ID in RuntimeConfig().input_packs


def test_pack_is_in_resolver_defaults() -> None:
    from chat.pack_resolver import DEFAULT_RESOLVABLE_PACK_IDS
    assert PACK_ID in DEFAULT_RESOLVABLE_PACK_IDS


def test_v2_corpus_is_registered() -> None:
    from chat.teaching_grounding import TEACHING_CORPORA
    corpus_ids = {s.corpus_id for s in TEACHING_CORPORA}
    assert "relations_chains_v2" in corpus_ids


def test_v2_pack_lemmas_ground_through_resolver() -> None:
    """Every v2 lemma resolves to v2 pack via the cross-pack resolver."""
    from chat.pack_resolver import resolve_lemma
    for lemma in EXPECTED_LEMMAS:
        resolved = resolve_lemma(lemma)
        assert resolved is not None, f"{lemma!r} did not resolve"
        assert resolved[0] == PACK_ID, (
            f"{lemma!r} resolved to {resolved[0]} instead of {PACK_ID}"
        )


def test_v2_chains_emit_teaching_grounded_surfaces() -> None:
    """Reviewed v2-internal chains produce teaching-grounded surfaces."""
    from chat.teaching_grounding import (
        clear_teaching_caches,
        teaching_grounded_surface,
    )
    from generate.intent import IntentTag
    clear_teaching_caches()
    s = teaching_grounded_surface("mother", IntentTag.CAUSE)
    assert s is not None
    assert "mother precedes daughter" in s
    assert "relations_chains_v2" in s

    s2 = teaching_grounded_surface("daughter", IntentTag.VERIFICATION)
    assert s2 is not None
    assert "daughter requires mother" in s2
