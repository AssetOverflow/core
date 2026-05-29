//! VaultStore hot path: parallel top-k CGA inner product scan.
//!
//! Uses Rayon for data-parallel scoring across all stored versors.
//! Each worker computes the diagonal-metric CGA inner product
//! independently — no shared state, no locks.  Top-k is finalised
//! with a stable sort that mirrors Python's ascending-index
//! tie-break (ADR-0019 Stage 1 + ADR-0020 first-surface parity).
//!
//! The CGA inner product in Cl(4,1) is structurally diagonal with
//! ±1 metric values, so per-versor scoring collapses to
//!
//! ```text
//! sum_i metric[i] * v[i] * q[i]
//! ```
//!
//! which is 32 multiplies + 32 adds, not the 1024-op full
//! geometric_product the reference scalar path computes.  Bit-
//! identity with Python's vectorised path is preserved because
//! the serial fold order is identical (i = 0..32, left-to-right
//! accumulation) and float32 multiply/add are deterministic.

use rayon::prelude::*;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum VaultError {
    #[error("CGA error during recall: {0}")]
    Cga(String),
}

/// Diagonal Cl(4,1) CGA inner-product metric.  Derived once at
/// build time from cga_inner(e_i, e_i) over the 32-component
/// basis.  See `tests/test_vault_recall_vectorised.py` (Python
/// side) for the empirical derivation that pins this vector.
const CGA_INNER_METRIC: [f32; 32] = [
    1.0,  1.0,  1.0,  1.0,  1.0, -1.0, -1.0, -1.0,
   -1.0,  1.0, -1.0, -1.0,  1.0, -1.0,  1.0,  1.0,
   -1.0, -1.0,  1.0, -1.0,  1.0,  1.0, -1.0,  1.0,
    1.0,  1.0,  1.0, -1.0, -1.0, -1.0, -1.0, -1.0,
];

/// Per-versor diagonal-metric CGA inner product.  Same arithmetic
/// order as Python's `(metric[i] * v[i]) * q[i]` serial fold —
/// bit-identical scores by construction.
#[inline(always)]
fn diagonal_score(v: &[f32; 32], q: &[f32; 32]) -> f32 {
    let mut s: f32 = 0.0;
    for i in 0..32 {
        let t = CGA_INNER_METRIC[i] * v[i];
        s += t * q[i];
    }
    s
}

/// Zero-copy parallel top-k recall by CGA inner product, over a
/// flat (N*32,) f32 slice viewed directly from a numpy buffer.
///
/// `versors_flat` must hold N consecutive [f32; 32] blocks in C
/// (row-major) order.  No copies are made; Rayon scores straight
/// off the source slice with stride 32.
pub fn vault_recall_flat(
    versors_flat: &[f32],
    n: usize,
    query: &[f32; 32],
    top_k: usize,
) -> Result<Vec<(usize, f32)>, VaultError> {
    if n == 0 {
        return Ok(vec![]);
    }
    debug_assert_eq!(versors_flat.len(), n * 32);

    let mut scores: Vec<(usize, f32)> = (0..n)
        .into_par_iter()
        .map(|i| {
            let v = &versors_flat[i * 32..(i + 1) * 32];
            let mut s: f32 = 0.0;
            for j in 0..32 {
                let t = CGA_INNER_METRIC[j] * v[j];
                s += t * query[j];
            }
            (i, s)
        })
        .collect();

    let k = top_k.min(scores.len());
    if k < scores.len() {
        scores.select_nth_unstable_by(k.saturating_sub(1), |a, b| {
            b.1.partial_cmp(&a.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.0.cmp(&b.0))
        });
        scores.truncate(k);
    }
    scores.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.0.cmp(&b.0))
    });

    Ok(scores)
}

/// Parallel top-k recall by CGA inner product.
///
/// versors: slice of [f32; 32] stored versors
/// query:   [f32; 32] query versor
/// top_k:   number of results to return
///
/// Returns Vec<(index, score)> sorted descending by score, with
/// ascending-index tie-break.  Thread-safe: Rayon spawns workers
/// per chunk, no locks required.
pub fn vault_recall_raw(
    versors: &[[f32; 32]],
    query: &[f32; 32],
    top_k: usize,
) -> Result<Vec<(usize, f32)>, VaultError> {
    if versors.is_empty() {
        return Ok(vec![]);
    }

    // Score all versors in parallel via the diagonal kernel.
    let mut scores: Vec<(usize, f32)> = versors
        .par_iter()
        .enumerate()
        .map(|(i, v)| (i, diagonal_score(v, query)))
        .collect();

    // Stable top-k order: descending score, ascending index on
    // ties (mirrors Python list.sort with key=lambda x: -x[1] on
    // an enumerated list).
    let k = top_k.min(scores.len());
    if k < scores.len() {
        scores.select_nth_unstable_by(k.saturating_sub(1), |a, b| {
            b.1.partial_cmp(&a.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.0.cmp(&b.0))
        });
        scores.truncate(k);
    }
    scores.sort_by(|a, b| {
        b.1.partial_cmp(&a.1)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then(a.0.cmp(&b.0))
    });

    Ok(scores)
}

/// Batch reproject: null-project all versors in parallel.
/// Returns new Vec of reprojected versors.
pub fn vault_reproject_parallel(versors: &[[f32; 32]]) -> Vec<[f32; 32]> {
    use crate::cga::null_project_raw;
    versors.par_iter().map(|v| null_project_raw(v)).collect()
}

// ===========================================================================
// Delta-CRDT substrate (ADR-0180 §2.1 / §2.2)
// ===========================================================================
//
// `LocalArena` is the thread-local, share-nothing write cache each modality
// adapter accumulates into (ADR-0180 §2.1). It never touches global state, so
// it needs no locks: concurrency safety comes from each thread owning its own
// arena, not from synchronisation.
//
// `SemilatticeDelta` is the join-semilattice contract (ADR-0180 §2.2): the
// merge of deltas is commutative, associative, and idempotent. The Merge
// Kernel folds deltas into a single content-addressed, deduplicated, totally
// ordered set — the order-invariant state the Vault consumes. Ordering is by
// content (the versor's IEEE-754 bit pattern + provenance bytes), never
// arrival order, per the §2.2 content-addressed-tiebreak amendment
// (2026-05-29). That is precisely what makes
// `hash(Sequential_Ingest) == hash(Concurrent_CRDT_Ingest)` (§4.3) reachable:
// the merged state cannot depend on the order deltas arrived in.
//
// This is the pure-CPU Rust substrate (§1.5.5); no MLX/UMA handshake and no
// Python binding land here — those are downstream (ADR-0180 §4.1 item 2, and
// ADR-0181 PR-5 respectively).

use std::cmp::Ordering;

/// One write accumulated into an arena: a Cl(4,1) versor plus opaque
/// provenance bytes. Provenance is part of the content key, so two writes of
/// the same versor under different provenance are distinct semilattice
/// elements (both retained); two byte-identical writes collapse (the
/// idempotence leg of the join semilattice, ADR-0180 §2.2).
#[derive(Clone, Debug)]
pub struct ArenaEntry {
    pub versor: [f32; 32],
    pub provenance: Vec<u8>,
}

impl ArenaEntry {
    pub fn new(versor: [f32; 32], provenance: Vec<u8>) -> Self {
        Self { versor, provenance }
    }
}

/// Total, arrival-independent content order over arena entries.
///
/// f32 has no total `Ord` (NaN is unordered), so we compare the raw IEEE-754
/// bit patterns — which is exactly what "content-addressed" means here:
/// byte-identical versors sort together and deduplicate, and `-0.0`/`+0.0`
/// (distinct bytes) are treated as distinct content, as a byte-addressed merge
/// requires. Ties on the versor fall through to the provenance bytes, giving a
/// total order (ADR-0180 §2.2 amendment, mirroring ADR-0181 §2.2's merge key).
fn content_cmp(a: &ArenaEntry, b: &ArenaEntry) -> Ordering {
    for i in 0..32 {
        let o = a.versor[i].to_bits().cmp(&b.versor[i].to_bits());
        if o != Ordering::Equal {
            return o;
        }
    }
    a.provenance.cmp(&b.provenance)
}

#[inline]
fn content_eq(a: &ArenaEntry, b: &ArenaEntry) -> bool {
    content_cmp(a, b) == Ordering::Equal
}

/// A snapshot of newly-ingested entries (ADR-0180 §2.2). A `Delta` is always
/// held in content-addressed order with byte-identical duplicates removed, so
/// it is a canonical join-semilattice element regardless of the order its
/// entries were inserted in.
#[derive(Clone, Debug, Default)]
pub struct Delta {
    entries: Vec<ArenaEntry>,
}

impl Delta {
    /// Canonicalise an arbitrary entry list into a Delta: sort by content,
    /// drop byte-identical duplicates. `sort_by` is stable, but the dedup key
    /// is the *whole* content, so stability is immaterial to the result.
    pub fn from_entries(mut entries: Vec<ArenaEntry>) -> Self {
        entries.sort_by(content_cmp);
        entries.dedup_by(|a, b| content_eq(a, b));
        Self { entries }
    }

    pub fn entries(&self) -> &[ArenaEntry] {
        &self.entries
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

/// The join-semilattice contract for Delta-CRDT state (ADR-0180 §2.2).
///
/// Implementors must satisfy, with content-addressed equality (`content_cmp`):
///   * commutativity   `a.join(b) == b.join(a)`
///   * associativity   `a.join(b).join(c) == a.join(b.join(c))`
///   * idempotence     `a.join(a) == a`
///
/// These are exercised as failable tests in `tests/test_arena.rs`; if `join`
/// ever orders by arrival instead of content, or stops deduplicating, those
/// tests fail loudly (CLAUDE.md §Schema-Defined Proof Obligations).
pub trait SemilatticeDelta: Sized {
    fn join(&self, other: &Self) -> Self;
}

impl SemilatticeDelta for Delta {
    fn join(&self, other: &Self) -> Self {
        let mut merged =
            Vec::with_capacity(self.entries.len() + other.entries.len());
        merged.extend_from_slice(&self.entries);
        merged.extend_from_slice(&other.entries);
        Delta::from_entries(merged)
    }
}

/// Thread-local, share-nothing write cache for one modality adapter
/// (ADR-0180 §2.1). Adapters push entries here lock-free; nothing is ever
/// written to global state from an arena. `snapshot` emits the order-invariant
/// `Delta` the Merge Kernel folds.
#[derive(Clone, Debug, Default)]
pub struct LocalArena {
    entries: Vec<ArenaEntry>,
}

impl LocalArena {
    pub fn new() -> Self {
        Self {
            entries: Vec::new(),
        }
    }

    /// Lock-free local write. Push order is irrelevant: `snapshot`
    /// canonicalises into content-addressed order.
    pub fn push(&mut self, versor: [f32; 32], provenance: Vec<u8>) {
        self.entries.push(ArenaEntry::new(versor, provenance));
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Emit a canonical Delta of everything accumulated so far. Does not drain
    /// the arena — flush/GC policy is the Merge Kernel's concern, not the
    /// arena's.
    pub fn snapshot(&self) -> Delta {
        Delta::from_entries(self.entries.clone())
    }
}

/// The Merge Kernel (ADR-0180 §2.2): fold a batch of deltas into a single
/// content-addressed, deduplicated, totally ordered entry set. The result is
/// invariant under any permutation of `deltas` (commutativity + associativity)
/// and under duplicate deltas (idempotence) — the property §4.3's
/// `hash(Sequential) == hash(Concurrent)` proof rides on.
///
/// Implemented as a single canonicalisation of the union rather than a
/// `fold(join)` chain; `tests/test_arena.rs` pins that the two are
/// content-equal, so the cheap path can never silently diverge from the
/// semilattice fold it stands in for.
pub fn merge_kernel(deltas: &[Delta]) -> Delta {
    let mut all = Vec::new();
    for d in deltas {
        all.extend_from_slice(&d.entries);
    }
    Delta::from_entries(all)
}
