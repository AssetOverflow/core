//! Cl(4,1) geometric product via precomputed table.
//!
//! Signature: (+,+,+,-,+). 32-component f32 multivectors.
//! The multiplication table is computed once at program start using
//! const evaluation and stored as two [u8;1024] and [i8;1024] arrays
//! (index and sign for each of the 32x32 blade pairs).
//!
//! geometric_product_raw is the inner loop called by every higher-level op.
//! It is deliberately kept allocation-free: inputs and output are [f32;32].

use thiserror::Error;

#[derive(Debug, Error)]
pub enum Cl41Error {
    #[error("Multivector length must be 32, got {0}")]
    BadLength(usize),
}

// Blade ordering: grade-0 (1), grade-1 (5), grade-2 (10), grade-3 (10), grade-4 (5), grade-5 (1)
// We encode each blade as a bitmask over 5 bits (bit k = basis vector k+1 present)
// The mapping from bitmask to component index follows grade-ascending, lex order.

// Signature: e1^2=+1, e2^2=+1, e3^2=+1, e4^2=-1, e5^2=+1
const SIG: [i8; 5] = [1, 1, 1, -1, 1];

// Precomputed at compile time via const fn
const BLADE_MASKS: [u8; 32] = build_blade_masks();
const MASK_TO_IDX: [u8; 32] = build_mask_to_idx();

const fn build_blade_masks() -> [u8; 32] {
    // Grade-ascending, lex order over 5 bits
    let mut masks = [0u8; 32];
    let mut pos = 0usize;
    let mut k = 0u8;
    while k <= 5 {
        // Iterate over all 5-bit masks with popcount == k
        let mut mask = 0u8;
        while mask < 32 {
            if popcount5(mask) == k {
                masks[pos] = mask;
                pos += 1;
            }
            mask += 1;
        }
        k += 1;
    }
    masks
}

const fn build_mask_to_idx() -> [u8; 32] {
    let blades = build_blade_masks();
    let mut lut = [0u8; 32];
    let mut i = 0usize;
    while i < 32 {
        lut[blades[i] as usize] = i as u8;
        i += 1;
    }
    lut
}

const fn popcount5(x: u8) -> u8 {
    let mut n = x & 0x1F;
    let mut c = 0u8;
    while n != 0 { c += n & 1; n >>= 1; }
    c
}

// Multiply two basis blades given as bitmasks. Returns (result_mask, sign).
// The sign is the parity of swaps needed to canonicalize A followed by B,
// multiplied by the metric contractions for repeated basis vectors.
const fn blade_product(a: u8, b: u8) -> (u8, i8) {
    let mut sign: i8 = 1;

    // Anticommutation sign: every pair (a_i, b_j) with a_i > b_j swaps once.
    let mut swaps = 0u8;
    let mut ai = 0u8;
    while ai < 5 {
        if (a >> ai) & 1 == 1 {
            let mut bj = 0u8;
            while bj < 5 {
                if (b >> bj) & 1 == 1 && ai > bj {
                    swaps += 1;
                }
                bj += 1;
            }
        }
        ai += 1;
    }
    if swaps % 2 == 1 {
        sign *= -1;
    }

    // Metric contractions for duplicate basis vectors.
    let common = a & b;
    let mut bit = 0u8;
    while bit < 5 {
        if (common >> bit) & 1 == 1 {
            sign *= SIG[bit as usize];
        }
        bit += 1;
    }

    (a ^ b, sign)
}

struct Table {
    idx:  [[u8; 32]; 32],
    sign: [[i8; 32]; 32],
}

fn build_table() -> Table {
    let mut idx  = [[0u8; 32]; 32];
    let mut sign = [[0i8; 32]; 32];
    for i in 0..32usize {
        for j in 0..32usize {
            let (result_mask, s) = blade_product(BLADE_MASKS[i], BLADE_MASKS[j]);
            idx[i][j]  = MASK_TO_IDX[result_mask as usize];
            sign[i][j] = s;
        }
    }
    Table { idx, sign }
}

use std::sync::OnceLock;
static TABLE: OnceLock<Table> = OnceLock::new();

fn table() -> &'static Table {
    TABLE.get_or_init(build_table)
}

/// Full geometric product in Cl(4,1).
/// Both inputs are [f32; 32]. Returns [f32; 32]. Allocation-free.
pub fn geometric_product_raw(a: &[f32; 32], b: &[f32; 32]) -> Result<[f32; 32], Cl41Error> {
    let t = table();
    let mut result = [0f32; 32];
    for i in 0..32 {
        let ai = a[i];
        if ai == 0.0 { continue; }
        for j in 0..32 {
            let bj = b[j];
            if bj == 0.0 { continue; }
            let k = t.idx[i][j] as usize;
            let s = t.sign[i][j] as f32;
            result[k] += s * ai * bj;
        }
    }
    Ok(result)
}

/// Reverse anti-automorphism.
/// Grade-k blade sign: (-1)^(k*(k-1)/2)
/// Grade 0,1: +1.  Grade 2,3: -1.  Grade 4,5: +1.
pub fn reverse_raw(a: &[f32; 32]) -> [f32; 32] {
    let mut r = *a;
    // Grade 2: indices 6..=15
    for i in 6..=15 { r[i] = -r[i]; }
    // Grade 3: indices 16..=25
    for i in 16..=25 { r[i] = -r[i]; }
    r
}
