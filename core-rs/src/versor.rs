//! Versor operations: the three primitives.
//!
//! versor_apply       V*F*reverse(V)     — the only allowed field transition
//! normalize_to_versor F/sqrt(|F*rev(F)|) — called once at injection gate
//! versor_condition   ||F*rev(F)-1||_F   — used in tests and gate only

use crate::cl41::{geometric_product_raw, reverse_raw, Cl41Error};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum VersorError {
    #[error("Cl41 error: {0}")]
    Cl41(#[from] Cl41Error),
    #[error("Cannot normalize: norm^2 too small ({0})")]
    NullVersor(f32),
}

/// Sandwich product V * F * reverse(V).
/// Allocation-free. This is the hot path — called every generation step.
pub fn versor_apply_raw(v: &[f32; 32], f: &[f32; 32]) -> Result<[f32; 32], VersorError> {
    let rev_v = reverse_raw(v);
    let vf    = geometric_product_raw(v, f)?;
    let vfrv  = geometric_product_raw(&vf, &rev_v)?;
    Ok(vfrv)
}

/// Project F onto versor manifold: F / sqrt(|scalar_part(F*rev(F))|).
/// Called ONCE at ingest/gate. Never mid-propagation.
pub fn normalize_to_versor_raw(f: &[f32; 32]) -> Result<[f32; 32], VersorError> {
    let rev_f = reverse_raw(f);
    let frv   = geometric_product_raw(f, &rev_f)?;
    let n2    = frv[0]; // grade-0 = scalar part
    if n2.abs() < 1e-12 {
        return Err(VersorError::NullVersor(n2));
    }
    let inv_norm = 1.0 / n2.abs().sqrt();
    let mut result = *f;
    for x in result.iter_mut() { *x *= inv_norm; }
    Ok(result)
}

/// ||F * reverse(F) - 1||_F.
/// Returns scalar f32. Used in tests and injection gate only.
pub fn versor_condition_raw(f: &[f32; 32]) -> Result<f32, VersorError> {
    let rev_f = reverse_raw(f);
    let mut frv = geometric_product_raw(f, &rev_f)?;
    frv[0] -= 1.0; // subtract identity
    let norm_sq: f32 = frv.iter().map(|x| x * x).sum();
    Ok(norm_sq.sqrt())
}
