"""Contract tests for the ``en_core_relations_v1`` kinship starter pack.

Following the teaching-order doctrine
([`docs/teaching_order.md`](../docs/teaching_order.md) §5),
domain expansion starts with kinship — a tight, well-bounded
domain whose triples exercise every formation gate end-to-end.

As of ADR-0063 (cross-pack surface resolver), this pack IS in the
default ``RuntimeConfig.input_packs``.  Pack-grounded surface
composers in :mod:`chat.pack_grounding` consult
:mod:`chat.pack_resolver` so kinship lemmas ground on the live path
without a separate composer module.

These tests pin:

  - The pack loads via ``load_pack("en_core_relations_v1")`` without
    a checksum mismatch (manifest.checksum matches the bytes on
    disk per CLAUDE.md's pack-discipline).
  - The 8 kinship lemmas are all present.
  - Each lemma carries the expected canonical semantic_domains
    (deterministic taxonomy under ``kinship.*``, ``lineage.*``,
    ``biology.*``, ``social.*``).
  - No accidental cross-pack lemma collision with
    ``en_core_cognition_v1`` (orthogonal domains; deliberate
    separation per teaching_order.md).
"""

from __future__ import annotations

from language_packs.compiler import load_pack, load_pack_entries


PACK_ID = "en_core_relations_v1"

EXPECTED_LEMMAS: tuple[str, ...] = (
    "parent",
    "child",
    "sibling",
    "family",
    "ancestor",
    "descendant",
    "spouse",
    "offspring",
)

# Note: `person` is intentionally NOT in this pack — it lives in
# `en_core_cognition_v1` and the orthogonality test below pins
# that boundary.

EXPECTED_PRIMARY_DOMAINS: dict[str, str] = {
    "parent":     "kinship.ascendant.direct",
    "child":      "kinship.descendant.direct",
    "sibling":    "kinship.lateral.direct",
    "family":     "kinship.unit",
    "ancestor":   "kinship.ascendant.transitive",
    "descendant": "kinship.descendant.transitive",
    "spouse":     "kinship.partner",
    "offspring":  "kinship.descendant.direct",
}


def test_pack_loads_with_matching_checksum() -> None:
    """``load_pack`` raises ``ValueError`` on checksum mismatch.  A
    clean load implies manifest.checksum equals SHA-256 of the
    bytes actually on disk — CLAUDE.md's pack-discipline."""
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
    """The first ``semantic_domains`` entry is the load-bearing
    primary domain — drives mounted-pack resonance grouping."""
    entries = load_pack_entries(PACK_ID)
    by_lemma = {e.lemma: e for e in entries}
    for lemma, expected_primary in EXPECTED_PRIMARY_DOMAINS.items():
        assert lemma in by_lemma, f"missing lemma: {lemma}"
        actual = by_lemma[lemma].semantic_domains
        assert actual, f"{lemma!r} has empty semantic_domains"
        assert actual[0] == expected_primary, (
            f"{lemma!r}: primary domain drifted from {expected_primary!r} "
            f"to {actual[0]!r} — kinship taxonomy is load-bearing for the "
            f"first relations curriculum unit; updating requires an ADR."
        )


def test_every_lemma_has_multiple_semantic_domains() -> None:
    """Pack-grounded discipline: every lemma must surface a list of
    domains so the surface composer can pick top-k.  A 1-domain
    entry would collapse the composer's information surface."""
    entries = load_pack_entries(PACK_ID)
    for entry in entries:
        assert len(entry.semantic_domains) >= 2, (
            f"{entry.lemma!r} has only {len(entry.semantic_domains)} "
            f"semantic_domains; need ≥2 for surface composition headroom."
        )


def test_no_lemma_collision_with_cognition_pack() -> None:
    """The relations pack and the cognition pack are deliberately
    orthogonal (teaching_order.md §5 — domain DAGs ratify in
    isolation before cross-domain triples).  Any lemma in both
    packs would create silent mounting ambiguity at the
    ``_load_mounted_packs_cached`` layer."""
    _, relations_manifold = load_pack(PACK_ID)
    _, cognition_manifold = load_pack("en_core_cognition_v1")
    relations_surfaces = {
        relations_manifold.get_word_at(i)
        for i in range(len(relations_manifold))
    }
    cognition_surfaces = {
        cognition_manifold.get_word_at(i)
        for i in range(len(cognition_manifold))
    }
    overlap = relations_surfaces & cognition_surfaces
    assert not overlap, (
        f"unexpected lemma collision between en_core_relations_v1 and "
        f"en_core_cognition_v1: {overlap}.  Either the relations pack "
        f"absorbed a cognition lemma (reject) or the cognition pack "
        f"grew a kinship lemma (reject) — domain DAGs must stay "
        f"orthogonal per teaching_order.md §5."
    )


def test_pack_is_in_default_input_packs() -> None:
    """ADR-0063 — once the cross-pack surface resolver landed, the
    relations pack joined the default mount.  Pack composers in
    :mod:`chat.pack_grounding` consult :mod:`chat.pack_resolver` for
    cross-pack lemma residency, so mounting the pack no longer
    silently widens recall without a corresponding surface composer
    — the composer is now cross-pack by default.

    Inverted from the original ADR-0063-pre guard
    ``test_pack_is_not_in_default_input_packs``."""
    from core.config import RuntimeConfig
    assert PACK_ID in RuntimeConfig().input_packs
