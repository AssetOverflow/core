//! ADR-0180 / ADR-0196 gate G1 (slice ZC-0) — Rust↔Python byte-parity.
//!
//! Proves the Rust Delta-CRDT substrate (`core_rs::vault`) produces
//! `canonical_bytes` identical to the Python reference `vault/crdt.py` over the
//! shared golden corpus. Expected hex is generated *from* the Python reference
//! (single source of truth) into `tests/fixtures/crdt_parity_expected.rs`, so
//! the two languages cannot silently disagree. Fails loudly if the Rust
//! serialization, content ordering, or dedup ever diverges from the locked
//! Python contract (CLAUDE.md §Schema-Defined Proof Obligations).

use core_rs::vault::{merge_kernel, ArenaEntry, Delta};

include!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/tests/fixtures/crdt_parity_expected.rs"
));

fn v(idx: usize, val: f32) -> [f32; 32] {
    let mut a = [0.0f32; 32];
    a[idx] = val;
    a
}

fn e(idx: usize, val: f32, prov: &str) -> ArenaEntry {
    ArenaEntry::new(v(idx, val), prov.as_bytes().to_vec())
}

fn delta(entries: Vec<ArenaEntry>) -> Delta {
    Delta::from_entries(entries)
}

fn hex(bytes: &[u8]) -> String {
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push_str(&format!("{:02x}", b));
    }
    s
}

fn expected(name: &str) -> &'static str {
    EXPECTED_CANONICAL_BYTES_HEX
        .iter()
        .find(|entry| entry.0 == name)
        .map(|entry| entry.1)
        .unwrap_or_else(|| panic!("no expected fixture for case {name}"))
}

fn assert_parity(name: &str, deltas: Vec<Delta>) {
    let merged = merge_kernel(&deltas);
    assert_eq!(hex(&merged.canonical_bytes()), expected(name), "case {name}");
}

#[test]
fn parity_single_entry() {
    assert_parity("single_entry", vec![delta(vec![e(0, 1.0, "a")])]);
}

#[test]
fn parity_dedup_within_delta() {
    assert_parity(
        "dedup_within_delta",
        vec![delta(vec![e(0, 1.0, "a"), e(0, 1.0, "a")])],
    );
}

#[test]
fn parity_distinct_provenance_retained() {
    assert_parity(
        "distinct_provenance_retained",
        vec![delta(vec![e(5, 2.0, "left"), e(5, 2.0, "right")])],
    );
}

#[test]
fn parity_three_delta_merge() {
    assert_parity(
        "three_delta_merge",
        vec![
            delta(vec![e(1, 3.0, "z"), e(0, 1.0, "a")]),
            delta(vec![e(2, 2.0, "m"), e(0, 1.0, "a")]),
            delta(vec![e(10, 5.0, "q")]),
        ],
    );
}

#[test]
fn parity_signed_zero_distinct() {
    assert_parity(
        "signed_zero_distinct",
        vec![delta(vec![e(0, 0.0, "p"), e(0, -0.0, "p")])],
    );
}

#[test]
fn parity_permutation_invariant_matches_python() {
    // Reordering input deltas must not change the merged bytes (and thus the
    // Python-pinned hash). Mirrors the Python permutation-invariance test.
    let d0 = delta(vec![e(1, 3.0, "z"), e(0, 1.0, "a")]);
    let d1 = delta(vec![e(2, 2.0, "m"), e(0, 1.0, "a")]);
    let d2 = delta(vec![e(10, 5.0, "q")]);
    let forward = hex(&merge_kernel(&[d0.clone(), d1.clone(), d2.clone()]).canonical_bytes());
    let reversed = hex(&merge_kernel(&[d2, d1, d0]).canonical_bytes());
    assert_eq!(forward, reversed);
    assert_eq!(forward, expected("three_delta_merge"));
}
