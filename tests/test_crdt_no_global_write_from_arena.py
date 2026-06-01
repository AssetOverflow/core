"""ADR-0180 / ADR-0196 gate G1 (slice ZC-0) — C-7: arena writes are local.

A ``LocalArena`` is a thread-local, share-nothing write cache. Pushing to it
must never mutate the global Vault; only an explicit merge *publication* (out of
scope for the reference contract — ADR-0180 §1.5.5) may alter Vault-visible
state. These tests fail loudly if the CRDT reference ever grows a global-write
side effect, and pin the purity/immutability of snapshot and merge.
"""

from __future__ import annotations

import inspect

import vault.crdt as crdt
from vault.crdt import ArenaEntry, Delta, LocalArena, merge_kernel
from vault.store import VaultStore

_DIM = crdt.VERSOR_COMPONENTS


def _v(idx: int, val: float) -> list[float]:
    v = [0.0] * _DIM
    v[idx] = val
    return v


def test_arena_push_does_not_write_global_vault():
    store = VaultStore()
    assert store.store_count == 0

    arena = LocalArena()
    for i in range(5):
        arena.push(_v(i, float(i + 1)), f"p{i}".encode())
    snapshot = arena.snapshot()
    merge_kernel([snapshot, arena.snapshot()])

    # Nothing was published: the Vault is untouched by arena accumulation.
    assert store.store_count == 0
    assert len(snapshot) == 5


def test_crdt_module_has_no_global_vault_coupling():
    src = inspect.getsource(crdt)
    for forbidden in ("VaultStore", "vault.store", ".store(", "vault_recall", ".recall("):
        assert forbidden not in src, (
            f"vault.crdt must not couple to the global Vault; found {forbidden!r}"
        )


def test_snapshot_does_not_drain_arena():
    arena = LocalArena()
    arena.push(_v(0, 1.0), b"a")
    arena.push(_v(1, 2.0), b"b")
    before = len(arena)
    first = arena.snapshot()
    second = arena.snapshot()
    assert len(arena) == before == 2
    assert first.entries == second.entries


def test_merge_and_from_entries_do_not_mutate_inputs():
    entries = [ArenaEntry.of(_v(0, 1.0), b"a"), ArenaEntry.of(_v(1, 2.0), b"b")]
    entries_snapshot = list(entries)
    Delta.from_entries(entries)
    assert entries == entries_snapshot  # from_entries left the input list intact

    delta = Delta.from_entries(entries)
    deltas = [delta, delta]
    deltas_snapshot = list(deltas)
    merge_kernel(deltas)
    assert deltas == deltas_snapshot  # merge_kernel left the input list intact
