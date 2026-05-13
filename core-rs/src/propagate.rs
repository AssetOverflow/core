//! Propagation loop in Rust — tight versor_apply chain.
//!
//! propagate_n steps runs N versor_apply calls in a single Rust stack frame,
//! eliminating Python dispatch overhead for each step.
//! Used by generate/stream.py when stepping more than one token at a time
//! (e.g. prefill, speculative steps, or batch generation).

use crate::versor::versor_apply_raw;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum PropagateError {
    #[error("Versor error during propagation: {0}")]
    Versor(String),
}

/// Run n versor_apply steps in sequence.
/// rotors: slice of n [f32;32] versors to apply in order
/// f0:     initial field state
/// Returns final field state after n steps.
pub fn propagate_n_raw(
    rotors: &[[f32; 32]],
    f0: &[f32; 32],
) -> Result<[f32; 32], PropagateError> {
    let mut f = *f0;
    for v in rotors {
        f = versor_apply_raw(v, &f)
            .map_err(|e| PropagateError::Versor(e.to_string()))?;
    }
    Ok(f)
}

/// Parallel batch propagation: apply the same rotor V to a batch of field states.
/// Used for beam search or multi-hypothesis generation.
/// Returns new batch of field states.
pub fn propagate_batch_raw(
    v: &[f32; 32],
    fields: &[[f32; 32]],
) -> Result<Vec<[f32; 32]>, PropagateError> {
    use rayon::prelude::*;
    fields
        .par_iter()
        .map(|f| {
            versor_apply_raw(v, f)
                .map_err(|e| PropagateError::Versor(e.to_string()))
        })
        .collect()
}
