"""Language-pack cache isolation tests."""

from __future__ import annotations

from language_packs.compiler import load_mounted_packs, load_pack, load_pack_entries


def test_load_pack_returns_defensive_manifold_copies() -> None:
    _manifest_a, manifold_a = load_pack("en_core_cognition_v1")
    _manifest_b, manifold_b = load_pack("en_core_cognition_v1")

    original_len = len(manifold_b)
    manifold_a.insert_transient("cache_probe_token", manifold_a.get_versor("truth"))

    assert len(manifold_a) == original_len + 1
    assert len(manifold_b) == original_len
    assert not manifold_b.is_transient("cache_probe_token")


def test_load_mounted_packs_returns_defensive_manifold_copies() -> None:
    packs = ("en_minimal_v1", "en_core_cognition_v1")
    mounted_a = load_mounted_packs(packs)
    mounted_b = load_mounted_packs(packs)

    original_len = len(mounted_b)
    mounted_a.insert_transient("mounted_cache_probe_token", mounted_a.get_versor("truth"))

    assert len(mounted_a) == original_len + 1
    assert len(mounted_b) == original_len
    assert not mounted_b.is_transient("mounted_cache_probe_token")


def test_load_pack_entries_returns_new_list_from_cached_tuple() -> None:
    entries_a = load_pack_entries("en_core_cognition_v1")
    entries_b = load_pack_entries("en_core_cognition_v1")

    entries_a.pop()

    assert len(entries_a) == len(entries_b) - 1
    assert entries_b[-1].entry_id == "en-core-cog-070"
