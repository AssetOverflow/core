//! Versor operations: the three primitives.
//!
//! versor_apply       V*F*reverse(V)     — the only allowed field transition
//! normalize_to_versor F/sqrt(|F*rev(F)|) — called once at injection gate
//! versor_condition   ||F*rev(F)-1||_F   — used in tests and gate only

use crate::cl41::{geometric_product_f64, geometric_product_raw, reverse_f64, reverse_raw, Cl41Error};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum VersorError {
    #[error("Cl41 error: {0}")]
    Cl41(#[from] Cl41Error),
    #[error("Cannot normalize: norm^2 too small ({0})")]
    NullVersor(f32),
}

const NEAR_ZERO_TOL: f64 = 1e-12;
const NULL_SCALAR_TOL: f64 = 1e-9;
const CONSTRUCTION_RESIDUE_TOL: f64 = 1e-2;
const SEED_BIVECTORS: [usize; 6] = [6, 7, 8, 10, 11, 13];

fn is_null_vector(v: &[f32; 32]) -> bool {
    use crate::cga::cga_inner_raw;
    // Generous tolerance: the f32 sandwich product introduces ~1e-6 error
    // on null vectors; 1e-5 correctly classifies them without false positives
    // on actual versors (which have cga_inner >> 0.1).
    match cga_inner_raw(v, v) {
        Ok(inner) => (inner as f64).abs() < 1e-5,
        Err(_) => false,
    }
}

fn unitize_closed(v: &[f64; 32]) -> Result<[f64; 32], ()> {
    let input_norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
    if input_norm < NEAR_ZERO_TOL {
        return Err(());
    }

    let rev = reverse_f64(v);
    let vv = geometric_product_f64(v, &rev);

    let scalar_sq = vv[0];
    let residue_norm: f64 = vv[1..].iter().map(|x| x * x).sum::<f64>().sqrt();

    if residue_norm >= CONSTRUCTION_RESIDUE_TOL {
        return Err(());
    }
    if scalar_sq <= 0.0 {
        return Err(());
    }

    let inv = 1.0 / scalar_sq.sqrt();
    let mut result = *v;
    for x in result.iter_mut() { *x *= inv; }
    Ok(result)
}

fn seed_to_rotor(v: &[f64; 32]) -> Result<[f64; 32], ()> {
    let scale: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
    let scale = if scale == 0.0 { 1.0 } else { scale };

    let mut rotor = [0f64; 32];
    rotor[0] = 1.0;

    for (step, &blade) in SEED_BIVECTORS.iter().enumerate() {
        let source = v[(blade + step) % 32] / scale;
        let theta = 0.5 * source.tanh();
        let mut factor = [0f64; 32];
        factor[0] = theta.cos();
        factor[blade] = theta.sin();

        rotor = geometric_product_f64(&rotor, &factor);
    }

    unitize_closed(&rotor)
}

fn close_applied_versor(v: &[f32; 32]) -> [f32; 32] {
    if is_null_vector(v) {
        return crate::cga::null_project_raw(v);
    }

    let v_f64: [f64; 32] = {
        let mut arr = [0f64; 32];
        for i in 0..32 { arr[i] = v[i] as f64; }
        arr
    };

    if let Ok(closed) = unitize_closed(&v_f64) {
        let mut result = [0f32; 32];
        for i in 0..32 { result[i] = closed[i] as f32; }
        return result;
    }

    if let Ok(seeded) = seed_to_rotor(&v_f64) {
        let mut result = [0f32; 32];
        for i in 0..32 { result[i] = seeded[i] as f32; }
        return result;
    }

    *v
}

/// Sandwich product V * F * reverse(V) with closure semantics.
/// Preserves null vectors as null vectors. Applies unit-versor closure
/// with construction seed fallback for non-null results.
pub fn versor_apply_closed(v: &[f32; 32], f: &[f32; 32]) -> Result<[f32; 32], VersorError> {
    let rev_v = reverse_raw(v);
    let vf = geometric_product_raw(v, f)?;
    let vfrv = geometric_product_raw(&vf, &rev_v)?;
    Ok(close_applied_versor(&vfrv))
}

/// `versor_apply` f64 path — bit-identity port of Python
/// `algebra.versor.versor_apply` + `_close_applied_versor`.
///
/// Performs the full sandwich V·F·rev(V) and closure in f64.  The
/// closure mirrors Python exactly: no null-vector early branch
/// (Python doesn't have one), and after `unitize_closed` succeeds the
/// candidate is gated through `versor_condition < 1e-6` before being
/// accepted — otherwise the deterministic `seed_to_rotor`
/// construction map is used.  ADR-0020 parity gate
/// `tests/test_versor_apply_rust_parity.py`.
pub fn versor_apply_closed_f64(
    v: &[f64; 32],
    f: &[f64; 32],
) -> Result<[f64; 32], VersorError> {
    let rev_v = reverse_f64(v);
    let vf = geometric_product_f64(v, f);
    let vfrv = geometric_product_f64(&vf, &rev_v);
    Ok(close_applied_versor_f64(&vfrv))
}

const RUNTIME_CLOSURE_TOL: f64 = 1e-6;
const DENSE_SEED_MIN_COMPONENTS: usize = 8;

fn versor_condition_f64(v: &[f64; 32]) -> f64 {
    let rev = reverse_f64(v);
    let mut frv = geometric_product_f64(v, &rev);
    frv[0] -= 1.0;
    frv.iter().map(|x| x * x).sum::<f64>().sqrt()
}

/// Mirrors Python `unitize_versor`: try `unitize_closed`; on
/// bad_residue, if dense enough fall back to `seed_to_rotor`; else
/// propagate the error.
fn unitize_versor_f64(v: &[f64; 32]) -> Result<[f64; 32], ()> {
    match unitize_closed(v) {
        Ok(closed) => Ok(closed),
        Err(()) => {
            // Python distinguishes bad_residue (eligible for seed fallback)
            // from bad_scalar / near_zero (not eligible).  We can't
            // distinguish the error variants under the current
            // `unitize_closed` signature; mirror Python's policy by gating
            // the fallback on the dense-support heuristic, which is the
            // condition Python also requires before invoking the rotor seed.
            let support = v
                .iter()
                .filter(|x| x.abs() > NEAR_ZERO_TOL)
                .count();
            if support < DENSE_SEED_MIN_COMPONENTS {
                Err(())
            } else {
                seed_to_rotor(v)
            }
        }
    }
}

/// Mirrors Python `_close_applied_versor`:
///   try _runtime_closed(v) -> if condition < 1e-6 return; else seed_to_rotor
///   on any ValueError -> seed_to_rotor (with passthrough as last resort
///                                       if seed_to_rotor itself fails)
fn close_applied_versor_f64(v: &[f64; 32]) -> [f64; 32] {
    if let Ok(candidate) = unitize_versor_f64(v) {
        if versor_condition_f64(&candidate) < RUNTIME_CLOSURE_TOL {
            return candidate;
        }
    }
    if let Ok(seeded) = seed_to_rotor(v) {
        return seeded;
    }
    *v
}

/// Raw sandwich product V * F * reverse(V) without closure.
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
/// Returns scalar f32 truncation of an f64 fold.
///
/// The fold (geometric product, identity subtraction, Frobenius norm)
/// is performed in f64 to match the Python source-of-truth
/// `algebra.versor.versor_unit_residual`, which uses
/// `dtype=np.float64` + `np.linalg.norm`. ADR-0020 parity gate
/// `tests/test_versor_condition_rust_parity.py` asserts bit-identity
/// of the returned f32; an all-f32 fold here drifts by 1 ULP on
/// out-of-shell inputs.  Python is canonical per CLAUDE.md
/// sequencing rule 5.
pub fn versor_condition_raw(f: &[f32; 32]) -> Result<f32, VersorError> {
    let f64_in: [f64; 32] = core::array::from_fn(|i| f[i] as f64);
    let rev_f = reverse_f64(&f64_in);
    let mut frv = geometric_product_f64(&f64_in, &rev_f);
    frv[0] -= 1.0;
    let norm_sq: f64 = frv.iter().map(|x| x * x).sum();
    Ok(norm_sq.sqrt() as f32)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn identity_versor() -> [f32; 32] {
        let mut v = [0f32; 32];
        v[0] = 1.0;
        v
    }

    fn simple_reflector() -> [f32; 32] {
        let mut v = [0f32; 32];
        v[1] = 1.0;
        v
    }

    #[test]
    fn closed_identity_is_identity() {
        let id = identity_versor();
        let f = simple_reflector();
        let result = versor_apply_closed(&id, &f).unwrap();
        for i in 0..32 {
            assert!((result[i] - f[i]).abs() < 1e-5, "component {} diverged", i);
        }
    }

    #[test]
    fn closed_preserves_versor_condition() {
        let v = simple_reflector();
        let f = identity_versor();
        let result = versor_apply_closed(&v, &f).unwrap();
        let cond = versor_condition_raw(&result).unwrap();
        assert!(cond < 1e-4, "condition {} too large", cond);
    }

    #[test]
    fn closed_matches_raw_for_identity() {
        let id = identity_versor();
        let f = simple_reflector();
        let raw = versor_apply_raw(&id, &f).unwrap();
        let closed = versor_apply_closed(&id, &f).unwrap();
        for i in 0..32 {
            assert!((raw[i] - closed[i]).abs() < 1e-5);
        }
    }
}
