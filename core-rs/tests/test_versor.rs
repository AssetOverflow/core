use core_rs::versor::{normalize_to_versor_raw, versor_apply_raw, versor_condition_raw};

fn random_versor(seed: u64) -> [f32; 32] {
    let theta = ((seed * 17 + 3) % 101) as f32 / 100.0;
    let mut v = [0f32; 32];
    v[0] = theta.cos();
    
    // Choose a bivector with negative square, e.g. e12
    // e1^2 = 1, e2^2 = 1 => (e1 e2)^2 = -e1^2 e2^2 = -1
    // MASK_TO_IDX for e1e2: e1 is bit 0, e2 is bit 1 => mask 3
    // MASK_TO_IDX[3] = 6 (grade 2 starts at 6)
    v[6] = theta.sin();
    
    v
}

#[test]
fn test_normalize_produces_versor() {
    for seed in 0..20u64 {
        let v = random_versor(seed);
        let cond = versor_condition_raw(&v).unwrap();
        assert!(cond < 1e-5, "versor_condition after normalize = {}", cond);
    }
}

#[test]
fn test_versor_apply_preserves_manifold() {
    for seed in 0..20u64 {
        let v = random_versor(seed);
        let f = random_versor(seed + 1000);
        let result = versor_apply_raw(&v, &f).unwrap();
        let cond = versor_condition_raw(&result).unwrap();
        assert!(cond < 1e-4, "versor_apply broke manifold: condition={:.2e} at seed={}", cond, seed);
    }
}

#[test]
fn test_identity_versor() {
    let mut identity = [0f32; 32];
    identity[0] = 1.0;
    let f = random_versor(42);
    let result = versor_apply_raw(&identity, &f).unwrap();
    for i in 0..32 {
        assert!((result[i] - f[i]).abs() < 1e-5, "Identity apply changed component {}: {} vs {}", i, result[i], f[i]);
    }
}

#[test]
fn test_composition_closed() {
    let v1 = random_versor(0);
    let v2 = random_versor(1);
    let f = random_versor(2);
    let f2 = versor_apply_raw(&v1, &f).unwrap();
    let f3 = versor_apply_raw(&v2, &f2).unwrap();
    let cond = versor_condition_raw(&f3).unwrap();
    assert!(cond < 1e-4, "Composition broke manifold: condition={:.2e}", cond);
}
