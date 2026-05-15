//! CGA inner product and null-cone operations.
//!
//! Signature: (+,+,+,+,-), with Euclidean coordinates on e1,e2,e3.
//! e4^2 = +1, e5^2 = -1.
//!
//! A Euclidean point x embeds as:
//!
//!   X = x + n_o + 0.5 * |x|^2 * n_inf
//!
//! with e4 coeff = 0.5*(|x|^2 - 1), e5 coeff = 0.5*(|x|^2 + 1).
//!
//! Then X·X = 0 and X·Y = -0.5 * ||x-y||^2.
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
    Ok(0.5 * (xy[0] + yx[0]))
}

/// Check if X is on the null cone: |X·X| < tol.
pub fn is_null_raw(x: &[f32; 32], tol: f32) -> Result<bool, CgaError> {
    Ok(cga_inner_raw(x, x)?.abs() < tol)
}

/// Re-project X onto the null cone by extracting Euclidean components
/// and re-embedding with the canonical CGA point map.
pub fn null_project_raw(x: &[f32; 32]) -> [f32; 32] {
    embed_point_raw(&[x[1], x[2], x[3]])
}

/// Embed a Euclidean point [x, y, z] into the CGA null cone.
/// X = x + n_o + 0.5|x|^2 n_inf
/// where n_o = 0.5(e4 - e5), n_inf = e4 + e5.
pub fn embed_point_raw(p: &[f32; 3]) -> [f32; 32] {
    let mut result = [0f32; 32];
    result[1] = p[0];
    result[2] = p[1];
    result[3] = p[2];
    let r2 = p[0] * p[0] + p[1] * p[1] + p[2] * p[2];
    result[4] = 0.5 * (r2 - 1.0);
    result[5] = 0.5 * (r2 + 1.0);
    result
}
