//! VaultStore hot path: parallel top-k CGA inner product scan.
//!
//! Uses Rayon for data-parallel scoring across all stored versors.
//! Each worker computes cga_inner(query, v) independently — no shared state,
//! no locks. Results are merged with a partial sort for top-k.
//!
//! This is the primary reason the vault scan is in Rust:
//! Python cannot release the GIL across a list comprehension.
//! Rayon gives us true multithreaded scoring with zero-copy slice access.

use rayon::prelude::*;
use crate::cga::cga_inner_raw;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum VaultError {
    #[error("CGA error during recall: {0}")]
    Cga(String),
}

/// Parallel top-k recall by CGA inner product.
///
/// versors: slice of [f32; 32] stored versors
/// query:   [f32; 32] query versor
/// top_k:   number of results to return
///
/// Returns Vec<(index, score)> sorted descending by score.
/// Thread-safe: Rayon spawns workers per chunk, no locks required.
pub fn vault_recall_raw(
    versors: &[[f32; 32]],
    query: &[f32; 32],
    top_k: usize,
) -> Result<Vec<(usize, f32)>, VaultError> {
    if versors.is_empty() {
        return Ok(vec![]);
    }

    // Score all versors in parallel
    let mut scores: Vec<(usize, f32)> = versors
        .par_iter()
        .enumerate()
        .map(|(i, v)| {
            let score = cga_inner_raw(v, query).unwrap_or(f32::NEG_INFINITY);
            (i, score)
        })
        .collect();

    // Partial sort: bring top_k to the front
    let k = top_k.min(scores.len());
    scores.select_nth_unstable_by(k.saturating_sub(1), |a, b| {
        b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal)
    });
    scores.truncate(k);
    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

    Ok(scores)
}

/// Batch reproject: null-project all versors in parallel.
/// Returns new Vec of reprojected versors.
pub fn vault_reproject_parallel(versors: &[[f32; 32]]) -> Vec<[f32; 32]> {
    use crate::cga::null_project_raw;
    versors.par_iter().map(|v| null_project_raw(v)).collect()
}
