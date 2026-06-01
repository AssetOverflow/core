"""ADR-0180 / ADR-0196 gate G1 (slice ZC-0) — Delta-CRDT semilattice contract.

These are *failable* proof obligations (CLAUDE.md §Schema-Defined Proof
Obligations) for the canonical reference in ``vault/crdt.py``:

  C-1 commutativity      join(a, b) == join(b, a)
  C-2 associativity      (a∘b)∘c == a∘(b∘c)
  C-3 idempotence        join(a, a) == a
  C-4 permutation        merge_kernel(perm(deltas)) is order-invariant
  C-5 duplicate no-op    merge(existing, already_seen) == existing
      kernel == fold     merge_kernel == reduce(join, …)  (the cheap path can
                         never silently diverge from the semilattice fold)

plus a golden fixture corpus that regression-locks the canonical byte layout
and merge hash. Each test fails loudly if ``join``/``merge_kernel`` ever orders
by arrival, stops deduplicating, or the canonical serialization drifts.
"""

from __future__ import annotations

import functools
import itertools
import json
from pathlib import Path

import pytest

from vault.crdt import (
    VERSOR_COMPONENTS,
    ArenaEntry,
    Delta,
    canonical_bytes,
    delta_hash,
    merge_kernel,
)

_FIXTURES = Path(__file__).parent / "fixtures" / "crdt" / "merge_fixtures.json"


def _v(idx: int, val: float) -> list[float]:
    v = [0.0] * VERSOR_COMPONENTS
    v[idx] = val
    return v


def _e(idx: int, val: float, prov: bytes) -> ArenaEntry:
    return ArenaEntry.of(_v(idx, val), prov)


def _decode_entry(d: dict) -> ArenaEntry:
    return ArenaEntry.of(d["versor"], bytes.fromhex(d["provenance_hex"]))


def _decode_delta(entry_dicts: list[dict]) -> Delta:
    return Delta.from_entries(_decode_entry(e) for e in entry_dicts)


# --- the three join-semilattice legs (ADR-0180 §2.2) -----------------------


def test_c1_join_is_commutative():
    a = Delta.from_entries([_e(0, 1.0, b"a")])
    b = Delta.from_entries([_e(1, 2.0, b"b")])
    # Fails if join carried arrival order: a-first vs b-first would differ.
    assert a.join(b).entries == b.join(a).entries
    assert len(a.join(b)) == 2  # distinct content — not collapsed


def test_c2_join_is_associative():
    a = Delta.from_entries([_e(0, 1.0, b"a")])
    b = Delta.from_entries([_e(1, 2.0, b"b")])
    c = Delta.from_entries([_e(2, 3.0, b"c")])
    assert a.join(b).join(c).entries == a.join(b.join(c)).entries


def test_c3_join_is_idempotent():
    a = Delta.from_entries([_e(0, 1.0, b"a"), _e(1, 2.0, b"b")])
    # a ∘ a == a — fails if dedup is removed (length would double).
    assert a.join(a).entries == a.entries
    assert len(a.join(a)) == 2


# --- merge kernel (the load-bearing hash(Sequential) == hash(Concurrent)) ---


def test_c4_merge_kernel_is_permutation_invariant():
    d0 = Delta.from_entries([_e(0, 1.0, b"a"), _e(1, 9.0, b"z")])
    d1 = Delta.from_entries([_e(2, 2.0, b"b")])
    d2 = Delta.from_entries([_e(3, 3.0, b"c")])
    reference = merge_kernel([d0, d1, d2])
    ref_hash = delta_hash(reference)
    for perm in itertools.permutations([d0, d1, d2]):
        merged = merge_kernel(list(perm))
        assert merged.entries == reference.entries
        assert delta_hash(merged) == ref_hash


def test_c5_duplicate_delta_is_noop():
    d = Delta.from_entries([_e(0, 1.0, b"a"), _e(1, 2.0, b"b")])
    assert merge_kernel([d]).entries == merge_kernel([d, d]).entries
    assert delta_hash(merge_kernel([d])) == delta_hash(merge_kernel([d, d, d]))


def test_merge_kernel_equals_semilattice_fold():
    deltas = [
        Delta.from_entries([_e(0, 1.0, b"a")]),
        Delta.from_entries([_e(1, 2.0, b"b"), _e(0, 1.0, b"a")]),
        Delta.from_entries([_e(2, 3.0, b"c")]),
    ]
    folded = functools.reduce(lambda acc, d: acc.join(d), deltas, Delta())
    assert merge_kernel(deltas).entries == folded.entries


# --- golden corpus: regression-lock the canonical form + merge hash ---------


def _load_cases() -> list[dict]:
    corpus = json.loads(_FIXTURES.read_text())
    assert corpus["versor_components"] == VERSOR_COMPONENTS
    return corpus["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_golden_fixture_canonical_form_and_hash(case: dict):
    deltas = [_decode_delta(ed) for ed in case["input_deltas"]]
    merged = merge_kernel(deltas)

    expected_entries = [_decode_entry(e) for e in case["expected_merged_entries"]]
    assert list(merged.entries) == expected_entries
    assert canonical_bytes(merged).hex() == case["expected_canonical_bytes_hex"]
    assert delta_hash(merged) == case["expected_delta_hash"]

    # Permutation invariance on the real corpus: any arrival order folds to the
    # same pinned hash.
    for perm in itertools.permutations(deltas):
        assert delta_hash(merge_kernel(list(perm))) == case["expected_delta_hash"]
