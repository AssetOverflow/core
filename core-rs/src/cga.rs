//! CGA inner product and null-cone operations.
//!
//! cga_inner(X, Y) = 0.5 * scalar_part(X*Y + Y*X)
//!                 = -d^2 / 2  for null vectors X, Y
//!
//! This is the ONLY distance metric in CORE-AI.

use crate::cl41::{geometric_product_raw, Cl41Error};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum CgaError {
    #[error("Cl41 error: {0}")]
    Cl41(#[from] Cl41Error),
}

/// Symmetric CGA inner product.
/// 0.5 * scalar_part(X*Y + Y*X)
/// For null vectors: equals -d^2 / 2.
pub fn cga_inner_raw(x: &[f32; 32], y: &[f32; 32]) -> Result<f32, CgaError> {
    let xy = geometric_product_raw(x, y)?;
    let yx = geometric_product_raw(y, x)?;
    // scalar part is index 0
    Ok(0.5 * (xy[0] + yx[0]))
}

/// Check if X is on the null cone: |X*X| < tol.
pub fn is_null_raw(x: &[f32; 32], tol: f32) -> Result<bool, CgaError> {
    Ok(cga_inner_raw(x, x)?.abs() < tol)
}

/// Re-project X onto the null cone.
/// Extract Euclidean components (indices 1-3), recompute e+ = 0.5*|x|^2, e- = 1.
pub fn null_project_raw(x: &[f32; 32]) -> [f32; 32] {
    let mut result = [0f32; 32];
    result[1] = x[1];
    result[2] = x[2];
    result[3] = x[3];
    let x_sq = result[1] * result[1] + result[2] * result[2] + result[3] * result[3];
    result[4] = 0.5 * x_sq; // e+ coefficient
    result[5] = 1.0;         // e- coefficient
    result
}

/// Embed a Euclidean point [x, y, z] into the CGA null cone.
/// X = x*e1 + y*e2 + z*e3 + (1/2)|x|^2 * e+ + e-
pub fn embed_point_raw(p: &[f32; 3]) -> [f32; 32] {
    let mut result = [0f32; 32];
    result[1] = p[0];
    result[2] = p[1];
    result[3] = p[2];
    let r2 = p[0]*p[0] + p[1]*p[1] + p[2]*p[2];
    result[4] = 0.5 * r2;
    result[5] = 1.0;
    result
}
