"""vault/crdt.py — canonical Delta-CRDT reference contract (ADR-0180, gate G1).

This module is the **locked reference contract** for CORE's Delta-CRDT write
substrate.  It is the Python-canonical mirror of the Rust incumbent in
``core-rs/src/vault.rs`` (§2.1/§2.2) and the contract any future native backend
(Rust binding, or a Zig prototype under ADR-0196 gate G2) must reproduce
bit-for-bit.  See ``docs/zig/crdt-substrate/`` (slice ZC-0) and
``docs/zig/adoption-gates.md`` (G1, G3).

What this is
------------
A *thread-local, share-nothing* write cache (``LocalArena``) accumulates
content-addressed writes; a canonical ``Delta`` is the sorted, deduplicated
snapshot; the ``merge_kernel`` folds many deltas into one order-invariant
``Delta``.  The join is a semilattice (commutative, associative, idempotent),
so the merged state — and its ``delta_hash`` — cannot depend on the order
deltas arrived in.  That is exactly the property ADR-0180 §4.3's
``hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)`` rides on.

Content law, not cognition
--------------------------
Ordering is by **content** — the IEEE-754 bit pattern of the 32 versor
components, then the provenance bytes — never by arrival order.  This module
performs **no** normalization, no versor closure/repair, no field mutation, and
no global Vault writes (CLAUDE.md §Normalization Rules / §Core Primitives).  A
``-0.0`` and a ``+0.0`` have distinct bits and are therefore distinct content,
as a byte-addressed merge requires.

Canonical serialization (the cross-language contract)
-----------------------------------------------------
``canonical_bytes(delta)`` is the load-bearing artifact; ``delta_hash`` is just
its SHA-256.  Layout (all little-endian)::

    u64   entry_count
    for each entry in canonical order:
        32 x f32   versor components   (IEEE-754, little-endian, 4 bytes each)
        u64        provenance_length
        bytes      provenance

Each entry is self-delimiting (fixed 128-byte versor + length-prefixed
provenance), so the byte stream is unambiguous.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

__all__ = [
    "VERSOR_COMPONENTS",
    "ArenaEntry",
    "Delta",
    "LocalArena",
    "merge_kernel",
    "canonical_bytes",
    "delta_hash",
]

# A Cl(4,1) multivector has 2**5 = 32 components (ADR-0180 §2.1; matches the
# ``[f32; 32]`` arena entry in core-rs/src/vault.rs).
VERSOR_COMPONENTS = 32


def _to_f32(x: float) -> float:
    """Round a Python float (f64) to the f32 value the Rust ``[f32; 32]`` would
    hold.  Storing the f32-coerced value makes content identity purely
    f32-based, so two inputs that map to the same f32 bits are the same
    content — exactly as the Rust substrate sees them."""
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def _component_bits(x: float) -> int:
    """The unsigned 32-bit IEEE-754 bit pattern of an (already f32-coerced)
    component.  Mirrors Rust ``f32::to_bits`` used by ``content_cmp``."""
    return struct.unpack("<I", struct.pack("<f", x))[0]


@dataclass(frozen=True)
class ArenaEntry:
    """One content-addressed write: a Cl(4,1) versor plus opaque provenance.

    Two writes of the same versor under *different* provenance are distinct
    semilattice elements (both retained); two byte-identical writes collapse
    (the idempotence leg of the join, ADR-0180 §2.2).
    """

    versor: tuple[float, ...]
    provenance: bytes

    @classmethod
    def of(cls, versor: Sequence[float], provenance: bytes = b"") -> "ArenaEntry":
        components = tuple(versor)
        if len(components) != VERSOR_COMPONENTS:
            raise ValueError(
                f"ArenaEntry versor must have {VERSOR_COMPONENTS} components; "
                f"got {len(components)}"
            )
        return cls(
            versor=tuple(_to_f32(c) for c in components),
            provenance=bytes(provenance),
        )

    def _content_key(self) -> tuple[tuple[int, ...], bytes]:
        """Total, arrival-independent content order key.

        Compares the 32 components by their IEEE-754 bit patterns (per-component
        unsigned-int comparison, matching Rust ``content_cmp``), with the
        provenance bytes as the final tiebreak.  Python compares the bits tuple
        element-wise then the bytes lexicographically — byte-for-byte the Rust
        ordering.
        """
        return (tuple(_component_bits(c) for c in self.versor), self.provenance)


@dataclass(frozen=True)
class Delta:
    """A canonical snapshot of newly-ingested entries (ADR-0180 §2.2): always
    held in content-addressed order with byte-identical duplicates removed, so
    it is a canonical join-semilattice element regardless of insertion order."""

    entries: tuple[ArenaEntry, ...] = ()

    @classmethod
    def from_entries(cls, entries: Iterable[ArenaEntry]) -> "Delta":
        """Canonicalise an arbitrary entry list: sort by content, drop
        byte-identical duplicates.  Does not mutate the input."""
        ordered = sorted(entries, key=ArenaEntry._content_key)
        deduped: list[ArenaEntry] = []
        last_key: tuple[tuple[int, ...], bytes] | None = None
        for entry in ordered:
            key = entry._content_key()
            if key != last_key:
                deduped.append(entry)
                last_key = key
        return cls(entries=tuple(deduped))

    def join(self, other: "Delta") -> "Delta":
        """Semilattice join: the canonical union of two deltas.  Commutative,
        associative, idempotent (ADR-0180 §2.2)."""
        return Delta.from_entries((*self.entries, *other.entries))

    def __len__(self) -> int:
        return len(self.entries)

    def is_empty(self) -> bool:
        return not self.entries


class LocalArena:
    """Thread-local, share-nothing write cache for one modality adapter
    (ADR-0180 §2.1).  Adapters push entries here lock-free; **nothing is ever
    written to global state from an arena**.  ``snapshot`` emits the
    order-invariant ``Delta`` the Merge Kernel folds; it does not drain the
    arena (flush/GC is the kernel's concern)."""

    def __init__(self) -> None:
        self._entries: list[ArenaEntry] = []

    def push(self, versor: Sequence[float], provenance: bytes = b"") -> None:
        """Lock-free local write.  Push order is irrelevant: ``snapshot``
        canonicalises into content-addressed order."""
        self._entries.append(ArenaEntry.of(versor, provenance))

    def __len__(self) -> int:
        return len(self._entries)

    def is_empty(self) -> bool:
        return not self._entries

    def snapshot(self) -> Delta:
        return Delta.from_entries(tuple(self._entries))


def merge_kernel(deltas: Sequence[Delta]) -> Delta:
    """Fold a batch of deltas into one content-addressed, deduplicated, totally
    ordered ``Delta`` (ADR-0180 §2.2).  Invariant under any permutation of
    ``deltas`` and under duplicate deltas — the property §4.3's
    ``hash(Sequential) == hash(Concurrent)`` rides on."""
    union: list[ArenaEntry] = []
    for delta in deltas:
        union.extend(delta.entries)
    return Delta.from_entries(union)


def canonical_bytes(delta: Delta) -> bytes:
    """The canonical little-endian serialization of a ``Delta`` — the
    cross-language contract a Rust/Zig backend must reproduce byte-for-byte.
    See the module docstring for the layout."""
    out = bytearray()
    out += struct.pack("<Q", len(delta.entries))
    for entry in delta.entries:
        for component in entry.versor:
            out += struct.pack("<f", component)
        out += struct.pack("<Q", len(entry.provenance))
        out += entry.provenance
    return bytes(out)


def delta_hash(delta: Delta) -> str:
    """SHA-256 (hex) of ``canonical_bytes(delta)`` — the replay-stable merge
    key.  Equal for any permutation of the deltas that produced ``delta``."""
    return hashlib.sha256(canonical_bytes(delta)).hexdigest()
