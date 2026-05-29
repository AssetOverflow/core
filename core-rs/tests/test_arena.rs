//! Delta-CRDT substrate proof obligations (ADR-0180 §2.1 / §2.2).
//!
//! Each test is written to FAIL LOUDLY under the specific violation it names
//! (CLAUDE.md §Schema-Defined Proof Obligations): a schema/trait is only a
//! proven property when a test would break if the property were silently
//! removed. The map:
//!
//!   * commutativity / associativity / idempotence — the three join-semilattice
//!     legs ADR-0180 §2.2 claims `Delta::join` satisfies.
//!   * permutation-invariant `merge_kernel` — the load-bearing property §4.3's
//!     `hash(Sequential) == hash(Concurrent)` rides on. Fails if `from_entries`
//!     stops sorting (i.e. orders by arrival).
//!   * distinct-provenance retention — guards the dedup from collapsing on the
//!     versor alone, which would silently drop epistemic state (a wrong=0-style
//!     data-loss hazard at the merge layer).

use core_rs::vault::{merge_kernel, ArenaEntry, Delta, LocalArena, SemilatticeDelta};

/// Deterministic distinct versor per seed.
fn versor(seed: u8) -> [f32; 32] {
    let mut v = [0f32; 32];
    for (i, slot) in v.iter_mut().enumerate() {
        *slot = (seed as f32) * 0.5 + (i as f32) * 0.125;
    }
    v
}

fn entry(seed: u8, prov: &str) -> ArenaEntry {
    ArenaEntry::new(versor(seed), prov.as_bytes().to_vec())
}

/// Canonical, comparable view of a Delta: (versor bits, provenance) per entry,
/// in the Delta's own order. Two Deltas are content-equal iff these match,
/// including order — so this also pins that ordering is content-addressed.
fn keys(d: &Delta) -> Vec<([u32; 32], Vec<u8>)> {
    d.entries()
        .iter()
        .map(|e| {
            let mut bits = [0u32; 32];
            for (i, b) in bits.iter_mut().enumerate() {
                *b = e.versor[i].to_bits();
            }
            (bits, e.provenance.clone())
        })
        .collect()
}

fn delta(entries: Vec<ArenaEntry>) -> Delta {
    Delta::from_entries(entries)
}

// --- the three join-semilattice legs (ADR-0180 §2.2) ----------------------

#[test]
fn join_is_commutative() {
    let a = delta(vec![entry(1, "p1"), entry(3, "p3")]);
    let b = delta(vec![entry(2, "p2"), entry(3, "p3")]);
    // Fails if join carries arrival order: a-first vs b-first would differ.
    assert_eq!(keys(&a.join(&b)), keys(&b.join(&a)));
}

#[test]
fn join_is_associative() {
    let a = delta(vec![entry(1, "p1")]);
    let b = delta(vec![entry(2, "p2")]);
    let c = delta(vec![entry(3, "p3")]);
    assert_eq!(keys(&a.join(&b).join(&c)), keys(&a.join(&b.join(&c))));
}

#[test]
fn join_is_idempotent() {
    let a = delta(vec![entry(1, "p1"), entry(2, "p2")]);
    // a ∘ a == a — fails if dedup is removed (length would double).
    let joined = a.join(&a);
    assert_eq!(keys(&joined), keys(&a));
    assert_eq!(joined.len(), 2);
}

// --- the load-bearing property for §4.3 -----------------------------------

#[test]
fn merge_kernel_is_permutation_invariant() {
    let d0 = delta(vec![entry(5, "a"), entry(1, "b")]);
    let d1 = delta(vec![entry(3, "c")]);
    let d2 = delta(vec![entry(9, "d"), entry(2, "e"), entry(7, "f")]);

    let forward = merge_kernel(&[d0.clone(), d1.clone(), d2.clone()]);
    let reversed = merge_kernel(&[d2.clone(), d1.clone(), d0.clone()]);
    let shuffled = merge_kernel(&[d1.clone(), d0.clone(), d2.clone()]);

    // hash(Sequential) == hash(Concurrent): merged state is independent of the
    // order deltas arrived in. Fails the instant `from_entries` orders by
    // arrival instead of content.
    assert_eq!(keys(&forward), keys(&reversed));
    assert_eq!(keys(&forward), keys(&shuffled));
}

#[test]
fn merge_kernel_dedups_duplicate_deltas() {
    let d = delta(vec![entry(4, "x"), entry(6, "y")]);
    // Re-ingesting the same delta is a no-op (idempotence at the kernel).
    let once = merge_kernel(&[d.clone()]);
    let twice = merge_kernel(&[d.clone(), d.clone()]);
    assert_eq!(keys(&once), keys(&twice));
    assert_eq!(twice.len(), 2);
}

#[test]
fn merge_kernel_equals_semilattice_fold() {
    let deltas = [
        delta(vec![entry(8, "a"), entry(2, "b")]),
        delta(vec![entry(5, "c")]),
        delta(vec![entry(2, "b"), entry(9, "d")]), // overlaps the first delta
    ];
    let folded = deltas
        .iter()
        .fold(Delta::default(), |acc, d| acc.join(d));
    // The cheap union-then-canonicalise path must equal the explicit
    // semilattice fold, or the kernel has silently diverged from the trait.
    assert_eq!(keys(&merge_kernel(&deltas)), keys(&folded));
}

// --- data-loss / over-dedup guard -----------------------------------------

#[test]
fn distinct_provenance_is_not_collapsed() {
    // Same versor, different provenance => two distinct semilattice elements.
    // Fails if dedup keys on the versor alone (which would drop state).
    let same_versor = vec![entry(7, "alpha"), entry(7, "beta")];
    let merged = delta(same_versor);
    assert_eq!(merged.len(), 2);

    // Byte-identical content (same versor + same provenance) => collapses.
    let identical = vec![entry(7, "alpha"), entry(7, "alpha")];
    assert_eq!(delta(identical).len(), 1);
}

#[test]
fn merge_result_is_content_sorted() {
    let d = merge_kernel(&[delta(vec![entry(9, "z"), entry(1, "a"), entry(5, "m")])]);
    let ks = keys(&d);
    let mut sorted = ks.clone();
    sorted.sort();
    assert_eq!(ks, sorted, "merge output must be in content-addressed order");
}

// --- LocalArena (ADR-0180 §2.1) -------------------------------------------

#[test]
fn arena_snapshot_independent_of_push_order() {
    let mut a = LocalArena::new();
    a.push(versor(3), b"p3".to_vec());
    a.push(versor(1), b"p1".to_vec());
    a.push(versor(2), b"p2".to_vec());

    let mut b = LocalArena::new();
    b.push(versor(2), b"p2".to_vec());
    b.push(versor(3), b"p3".to_vec());
    b.push(versor(1), b"p1".to_vec());

    // Two arenas fed the same writes in different orders snapshot to the same
    // canonical Delta (ADR-0180 §2.1: push order is irrelevant).
    assert_eq!(keys(&a.snapshot()), keys(&b.snapshot()));
}

#[test]
fn arena_snapshot_does_not_drain() {
    let mut a = LocalArena::new();
    a.push(versor(1), b"p1".to_vec());
    let _ = a.snapshot();
    // Flush/GC is the Merge Kernel's concern, not the arena's; snapshot must
    // be non-destructive so a delayed merge (the §3.2 window) cannot lose it.
    assert_eq!(a.len(), 1);
    assert_eq!(a.snapshot().len(), 1);
}
