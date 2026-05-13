//! Holonomy encoder in Rust — the forward+reverse versor walk.
//!
//! This is in Rust because:
//!   - Long prompts (100+ tokens) do 200+ geometric products in sequence
//!   - Each geometric product is O(32^2) = 1024 multiply-adds
//!   - Python overhead per call makes this 10-50x slower than necessary
//!   - Rust collapses the entire walk into a single allocation-free loop

use crate::cl41::{geometric_product_raw, reverse_raw};
use crate::versor::normalize_to_versor_raw;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum HolonomyError {
    #[error("Empty word list")]
    Empty,
    #[error("Versor error: {0}")]
    Versor(String),
}

/// Compute holonomy of a word versor sequence.
///
/// Forward walk:  F = w0 * w1 * ... * wn
/// Reverse walk:  R = (1-alpha) * rev(wn) * ... * rev(w0)
/// Holonomy:      H = normalize(F * R)
///
/// weights: per-word scalars (inverse frequency). If empty, uniform 1.0.
/// alpha:   blend factor [0,1]. 0.5 recommended.
pub fn holonomy_encode_raw(
    words: &[[f32; 32]],
    weights: &[f32],
    alpha: f32,
) -> Result<[f32; 32], HolonomyError> {
    if words.is_empty() {
        return Err(HolonomyError::Empty);
    }

    let n = words.len();
    let use_weights = !weights.is_empty() && weights.len() == n;

    // Forward accumulation
    let mut scaled = words[0];
    if use_weights {
        let w = weights[0];
        for x in scaled.iter_mut() { *x *= w; }
    }
    let mut f = normalize_to_versor_raw(&scaled)
        .map_err(|e| HolonomyError::Versor(e.to_string()))?;

    for k in 1..n {
        let mut wk = words[k];
        if use_weights {
            let w = weights[k];
            for x in wk.iter_mut() { *x *= w; }
        }
        let wk_norm = normalize_to_versor_raw(&wk)
            .map_err(|e| HolonomyError::Versor(e.to_string()))?;
        f = geometric_product_raw(&f, &wk_norm)
            .map_err(|e| HolonomyError::Versor(e.to_string()))?;
    }

    // Reverse accumulation with (1-alpha) damping
    let damp = 1.0 - alpha;
    let mut last_rev = reverse_raw(&words[n - 1]);
    for x in last_rev.iter_mut() { *x *= damp; }
    let mut r = normalize_to_versor_raw(&last_rev)
        .map_err(|e| HolonomyError::Versor(e.to_string()))?;

    for k in (0..n - 1).rev() {
        let rev_wk = reverse_raw(&words[k]);
        let rev_norm = normalize_to_versor_raw(&rev_wk)
            .map_err(|e| HolonomyError::Versor(e.to_string()))?;
        r = geometric_product_raw(&rev_norm, &r)
            .map_err(|e| HolonomyError::Versor(e.to_string()))?;
    }

    let h = geometric_product_raw(&f, &r)
        .map_err(|e| HolonomyError::Versor(e.to_string()))?;
    normalize_to_versor_raw(&h)
        .map_err(|e| HolonomyError::Versor(e.to_string()))
}
