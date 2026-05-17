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
//!     sum_i metric[i] * v[i] * q[i]
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
