//! Graph diffusion operator and exponential-map unitizer.
//!
//! These are the hot-path operations for the pulse loop.
//! `unitize_f32` builds a proper rotor from bivector content via the
//! exponential map, distinguishing boost planes (cosh/sinh) from
//! rotation planes (cos/sin) in Cl(4,1).
//!
//! `graph_diffusion_step` runs one forward pass of damped blending
//! across all graph edges, re-unitizing each touched node.

use crate::cl41::geometric_product_f64;
use std::collections::HashMap;

/// Blade indices 9, 12, 14, 15 square to +1 (boost/hyperbolic planes involving e5).
/// Remaining bivector indices (6-8, 10-11, 13) square to -1 (rotation planes).
const BOOST_INDICES: [usize; 4] = [9, 12, 14, 15];

fn is_boost(blade_idx: usize) -> bool {
    matches!(blade_idx, 9 | 12 | 14 | 15)
}

/// Unitize a multivector to versor condition via the exponential map.
///
/// Works in f64 throughout, returns f32. Matches the Python `_unitize_f32`
/// in `field/operators.py` exactly.
pub fn unitize_f32(v: &[f32; 32]) -> [f32; 32] {
    let v64: [f64; 32] = {
        let mut arr = [0f64; 32];
        for i in 0..32 { arr[i] = v[i] as f64; }
        arr
    };

    let norm: f64 = v64.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm < 1e-12 {
        let mut out = [0f32; 32];
        out[0] = 1.0;
        return out;
    }

    // Extract bivector content (indices 6..16)
    let bv: [f64; 10] = {
        let mut arr = [0f64; 10];
        for i in 0..10 { arr[i] = v64[6 + i]; }
        arr
    };
    let bv_norm: f64 = bv.iter().map(|x| x * x).sum::<f64>().sqrt();
    if bv_norm < 1e-14 {
        let mut out = [0f32; 32];
        out[0] = if v64[0] >= 0.0 { 1.0 } else { -1.0 };
        return out;
    }

    let angle = bv_norm.atan2(v64[0].abs());

    let mut rotor = [0f64; 32];
    rotor[0] = 1.0;

    for i in 0..10usize {
        let w = bv[i] / bv_norm;
        if w.abs() < 1e-14 { continue; }
        let theta = angle * w;
        let mut factor = [0f64; 32];
        let blade_idx = 6 + i;
        if is_boost(blade_idx) {
            factor[0] = theta.cosh();
            factor[blade_idx] = theta.sinh();
        } else {
            factor[0] = theta.cos();
            factor[blade_idx] = theta.sin();
        }
        rotor = geometric_product_f64(&rotor, &factor);
    }

    if v64[0] < 0.0 {
        for x in rotor.iter_mut() { *x = -*x; }
    }

    let mut result = [0f32; 32];
    for i in 0..32 { result[i] = rotor[i] as f32; }
    result
}

/// One forward step of graph diffusion.
///
/// For each node that has incoming edges, blend it with the average
/// of its neighbors, then re-unitize via the exponential map.
///
/// Returns (new_fields, delta) where delta is L2 norm of change.
pub fn graph_diffusion_step(
    fields: &[[f32; 32]],
    edges: &[[i32; 2]],
    damping: f64,
) -> (Vec<[f32; 32]>, f64) {
    let n = fields.len();
    let mut new_fields: Vec<[f32; 32]> = fields.to_vec();

    // Build neighbor map: dst -> [src, ...]
    let mut neighbors: HashMap<usize, Vec<usize>> = HashMap::new();
    for edge in edges {
        let dst = edge[1] as usize;
        let src = edge[0] as usize;
        neighbors.entry(dst).or_default().push(src);
    }

    for (&node, srcs) in &neighbors {
        if node >= n || srcs.is_empty() { continue; }

        // Current node in f64
        let mut f = [0f64; 32];
        for i in 0..32 { f[i] = fields[node][i] as f64; }

        // Neighbor average in f64
        let mut avg = [0f64; 32];
        for &src in srcs {
            for i in 0..32 { avg[i] += fields[src][i] as f64; }
        }
        let inv = 1.0 / srcs.len() as f64;
        for x in avg.iter_mut() { *x *= inv; }

        // Blend
        let mut blended = [0f32; 32];
        for i in 0..32 {
            blended[i] = ((1.0 - damping) * f[i] + damping * avg[i]) as f32;
        }
        new_fields[node] = unitize_f32(&blended);
    }

    // Compute delta
    let mut delta_sq = 0f64;
    for i in 0..n {
        for j in 0..32 {
            let d = (new_fields[i][j] - fields[i][j]) as f64;
            delta_sq += d * d;
        }
    }

    (new_fields, delta_sq.sqrt())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn identity() -> [f32; 32] {
        let mut v = [0f32; 32];
        v[0] = 1.0;
        v
    }

    #[test]
    fn unitize_identity_is_identity() {
        let id = identity();
        let result = unitize_f32(&id);
        assert!((result[0] - 1.0).abs() < 1e-5);
        for i in 1..32 {
            assert!(result[i].abs() < 1e-5, "component {} = {}", i, result[i]);
        }
    }

    #[test]
    fn unitize_zero_returns_identity() {
        let zero = [0f32; 32];
        let result = unitize_f32(&zero);
        assert!((result[0] - 1.0).abs() < 1e-5);
    }

    #[test]
    fn unitize_preserves_versor_condition() {
        use crate::versor::versor_condition_raw;
        let mut v = [0f32; 32];
        v[0] = 0.8;
        v[6] = 0.3;
        v[9] = 0.2;  // boost blade
        let result = unitize_f32(&v);
        let cond = versor_condition_raw(&result).unwrap();
        assert!(cond < 1e-4, "versor condition {} too large", cond);
    }

    #[test]
    fn diffusion_step_reduces_delta_over_iterations() {
        let mut fields = vec![identity(); 3];
        // Perturb node 1
        fields[1][0] = 0.9;
        fields[1][6] = 0.1;
        fields[1] = unitize_f32(&fields[1]);

        let edges = vec![[0i32, 2], [1, 2]];
        let (f1, d1) = graph_diffusion_step(&fields, &edges, 0.5);
        let (_, d2) = graph_diffusion_step(&f1, &edges, 0.5);
        assert!(d2 < d1, "delta should decrease: d1={}, d2={}", d1, d2);
    }
}
