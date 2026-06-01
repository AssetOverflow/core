"""ADR-0180 / ADR-0196 gate G1 (slice ZC-0) — content-addressed ordering.

The Delta-CRDT canonical order is by *content* — the IEEE-754 bit pattern of
the 32 versor components, then the provenance bytes — never by arrival order
(ADR-0180 §2.2 content-addressed-tiebreak amendment). These tests pin that the
``vault/crdt.py`` reference is byte/bit-addressed, matching the Rust
``content_cmp`` in ``core-rs/src/vault.rs`` (per-component ``f32::to_bits``,
then ``Vec<u8>`` provenance compare).
"""

from __future__ import annotations

import struct

from vault.crdt import VERSOR_COMPONENTS, ArenaEntry, Delta


def _v(idx: int, val: float) -> list[float]:
    v = [0.0] * VERSOR_COMPONENTS
    v[idx] = val
    return v


def _e(idx: int, val: float, prov: bytes) -> ArenaEntry:
    return ArenaEntry.of(_v(idx, val), prov)


def _f32_from_bits(bits: int) -> float:
    return struct.unpack("<f", struct.pack("<I", bits))[0]


def test_canonical_order_independent_of_insertion_order():
    e_a = _e(0, 1.0, b"a")
    e_b = _e(5, 2.0, b"b")
    e_c = _e(2, 3.0, b"c")
    d1 = Delta.from_entries([e_a, e_b, e_c])
    d2 = Delta.from_entries([e_c, e_a, e_b])
    d3 = Delta.from_entries([e_b, e_c, e_a])
    assert d1.entries == d2.entries == d3.entries
    # The canonical order is exactly the content-key sort order.
    assert list(d1.entries) == sorted([e_a, e_b, e_c], key=ArenaEntry._content_key)


def test_distinct_provenance_is_retained():
    versor = _v(5, 2.0)
    d = Delta.from_entries(
        [ArenaEntry.of(versor, b"left"), ArenaEntry.of(versor, b"right")]
    )
    # Fails if dedup keys on the versor alone (which would drop state).
    assert len(d) == 2


def test_byte_identical_entries_collapse():
    d = Delta.from_entries([_e(0, 1.0, b"x"), _e(0, 1.0, b"x")])
    assert len(d) == 1


def test_signed_zero_is_distinct_content():
    pos = ArenaEntry.of(_v(0, 0.0), b"p")
    neg = ArenaEntry.of(_v(0, -0.0), b"p")
    # +0.0 bits (0x00000000) != -0.0 bits (0x80000000) -> distinct content.
    assert pos._content_key() != neg._content_key()
    assert len(Delta.from_entries([pos, neg])) == 2


def test_nan_is_retained_and_bit_addressed():
    # Two NaNs that differ only in payload bits are distinct content. The
    # reference is bit-addressed (struct '<f' round-trips the f32 payload,
    # matching numpy's f32 cast and Rust's to_bits on all supported
    # little-endian targets).
    nan1 = _f32_from_bits(0x7FC00000)
    nan2 = _f32_from_bits(0x7FC00001)
    e1 = ArenaEntry.of(_v(0, nan1), b"n")
    e2 = ArenaEntry.of(_v(0, nan2), b"n")
    assert e1._content_key() != e2._content_key()
    assert len(Delta.from_entries([e1, e2])) == 2
    # A NaN is retained as content — never dropped or normalized to a number.
    assert len(Delta.from_entries([ArenaEntry.of(_v(3, nan1), b"")])) == 1


def test_content_order_follows_component_bit_order():
    # Component 0 sorts by its u32 bit pattern: 1.0 (0x3f800000) < 2.0
    # (0x40000000); a negative value's sign bit makes it sort *after* positives
    # under unsigned bit comparison (matching Rust to_bits ordering).
    lo = _e(0, 1.0, b"")
    hi = _e(0, 2.0, b"")
    neg = _e(0, -1.0, b"")  # 0xbf800000 — high bit set, sorts last
    ordered = Delta.from_entries([hi, neg, lo]).entries
    assert ordered == (lo, hi, neg)
