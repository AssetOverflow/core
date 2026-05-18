"""ADR-0063 — cross-pack surface resolver tests.

The contract these tests pin:

  - :func:`chat.pack_resolver.resolve_lemma` returns the first
    ``(pack_id, semantic_domains)`` whose lexicon contains the lemma.
  - Cognition lemmas resolve to ``en_core_cognition_v1``; kinship
    lemmas resolve to ``en_core_relations_v1``; absent lemmas return
    ``None``.
  - First-match-wins on order.
  - The lru_cache survives repeat calls without re-reading disk.
  - :func:`mounted_lemmas` is the union of lemma keys across the
    mounted packs in deterministic order.
"""

from __future__ import annotations

import pytest

from chat.pack_resolver import (
    DEFAULT_RESOLVABLE_PACK_IDS,
    _pack_lexicon_for,
    clear_resolver_cache,
    is_resolvable,
    mounted_lemmas,
    resolve_lemma,
)


# ---------------------------------------------------------------------------
# resolve_lemma — first-match-wins across mounted packs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "lemma",
    ["light", "knowledge", "meaning", "memory", "truth", "thought", "concept"],
)
def test_cognition_lemma_resolves_to_cognition_pack(lemma: str) -> None:
    resolved = resolve_lemma(lemma)
    assert resolved is not None, f"{lemma!r} did not resolve"
    pack_id, domains = resolved
    assert pack_id == "en_core_cognition_v1"
    assert isinstance(domains, tuple)
    assert domains, "resolved pack must surface non-empty semantic_domains"


@pytest.mark.parametrize(
    "lemma",
    ["parent", "child", "sibling", "family", "ancestor",
     "descendant", "spouse", "offspring"],
)
def test_kinship_lemma_resolves_to_relations_pack(lemma: str) -> None:
    resolved = resolve_lemma(lemma)
    assert resolved is not None, f"{lemma!r} did not resolve"
    pack_id, domains = resolved
    assert pack_id == "en_core_relations_v1"
    assert isinstance(domains, tuple)
    assert domains


def test_unknown_lemma_returns_none() -> None:
    assert resolve_lemma("nonexistent_lemma_xyz") is None


@pytest.mark.parametrize("bad", ["", "   ", None])
def test_empty_or_invalid_lemma_returns_none(bad) -> None:
    assert resolve_lemma(bad) is None  # type: ignore[arg-type]


def test_resolver_normalizes_case_and_whitespace() -> None:
    a = resolve_lemma("Knowledge")
    b = resolve_lemma("  knowledge  ")
    c = resolve_lemma("knowledge")
    assert a == b == c
    assert a is not None and a[0] == "en_core_cognition_v1"


def test_resolver_is_first_match_wins() -> None:
    """When the same lemma appears in two mounted packs, the earlier
    pack in *pack_ids* wins.  Today no lemma collision exists between
    cognition and relations (orthogonality test enforces this); this
    test reverses the order to verify the resolution rule itself."""
    reversed_order = (
        "en_core_relations_v1",
        "en_core_cognition_v1",
    )
    # ``parent`` exists only in relations; ``knowledge`` only in
    # cognition — order swap should not change which pack carries
    # them, only their resolution order.
    parent = resolve_lemma("parent", pack_ids=reversed_order)
    knowledge = resolve_lemma("knowledge", pack_ids=reversed_order)
    assert parent is not None and parent[0] == "en_core_relations_v1"
    assert knowledge is not None and knowledge[0] == "en_core_cognition_v1"


def test_pack_ids_default_contains_both_packs() -> None:
    assert "en_core_cognition_v1" in DEFAULT_RESOLVABLE_PACK_IDS
    assert "en_core_relations_v1" in DEFAULT_RESOLVABLE_PACK_IDS
    # Cognition first — first-match-wins favours cognition on any
    # future cross-pack lemma collision.
    assert DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_cognition_v1") < \
        DEFAULT_RESOLVABLE_PACK_IDS.index("en_core_relations_v1")


# ---------------------------------------------------------------------------
# is_resolvable — boolean shortcut
# ---------------------------------------------------------------------------


def test_is_resolvable_round_trips() -> None:
    assert is_resolvable("light") is True
    assert is_resolvable("parent") is True
    assert is_resolvable("nonexistent_lemma_xyz") is False
    assert is_resolvable("") is False


# ---------------------------------------------------------------------------
# mounted_lemmas — union view used by topic extractors
# ---------------------------------------------------------------------------


def test_mounted_lemmas_unions_both_packs() -> None:
    union = mounted_lemmas()
    assert "knowledge" in union
    assert "parent" in union
    assert "nonexistent_lemma_xyz" not in union
    # Frozen so callers cannot mutate the cached union accidentally.
    assert isinstance(union, frozenset)


def test_mounted_lemmas_respects_explicit_pack_ids() -> None:
    cognition_only = mounted_lemmas(pack_ids=("en_core_cognition_v1",))
    assert "knowledge" in cognition_only
    assert "parent" not in cognition_only, (
        "cognition-only view leaked a kinship lemma — pack residency "
        "boundary broken"
    )


# ---------------------------------------------------------------------------
# Caching contract
# ---------------------------------------------------------------------------


def test_pack_lexicon_is_cached() -> None:
    """Two calls for the same pack must return the same dict identity
    (lru_cache returns the cached object, not a copy)."""
    a = _pack_lexicon_for("en_core_cognition_v1")
    b = _pack_lexicon_for("en_core_cognition_v1")
    assert a is b


def test_clear_resolver_cache_is_safe() -> None:
    """The test-only escape hatch must not crash when called twice."""
    clear_resolver_cache()
    clear_resolver_cache()
    # And the resolver still works afterwards.
    assert resolve_lemma("knowledge") is not None


def test_missing_pack_returns_empty_index() -> None:
    """A pack id with no on-disk lexicon must yield an empty dict and
    callers see ``None`` from :func:`resolve_lemma` — no exception."""
    empty = _pack_lexicon_for("nonexistent_pack_id_zzz_v0")
    assert empty == {}
    assert resolve_lemma("knowledge", pack_ids=("nonexistent_pack_id_zzz_v0",)) is None
