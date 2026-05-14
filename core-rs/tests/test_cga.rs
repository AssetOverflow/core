use core_rs::cga::{cga_inner_raw, embed_point_raw, is_null_raw, null_project_raw};

#[test]
fn test_embedded_point_is_null() {
    let p = [1.0f32, 2.0, 3.0];
    let x = embed_point_raw(&p);
    assert!(is_null_raw(&x, 1e-5).unwrap(), "Embedded point should be null");
}

#[test]
fn test_origin_is_null() {
    let x = embed_point_raw(&[0.0, 0.0, 0.0]);
    assert!(is_null_raw(&x, 1e-5).unwrap());
}

#[test]
fn test_cga_inner_symmetry() {
    let x = embed_point_raw(&[1.0, 0.0, 0.0]);
    let y = embed_point_raw(&[0.0, 1.0, 0.0]);
    let xy = cga_inner_raw(&x, &y).unwrap();
    let yx = cga_inner_raw(&y, &x).unwrap();
    assert!((xy - yx).abs() < 1e-6, "cga_inner not symmetric");
}

#[test]
fn test_cga_distance_identity() {
    let x = embed_point_raw(&[0.0, 0.0, 0.0]);
    let y = embed_point_raw(&[1.0, 0.0, 0.0]);
    let inner = cga_inner_raw(&x, &y).unwrap();
    assert!((inner - (-0.5)).abs() < 1e-5, "Expected -0.5 for unit-distance points, got {}", inner);
}

#[test]
fn test_null_project_restores_null() {
    let p = [1.0f32, 2.0, 3.0];
    let mut x = embed_point_raw(&p);
    x[0] += 0.05;
    x[7] -= 0.03;
    let fixed = null_project_raw(&x);
    assert!(is_null_raw(&fixed, 1e-5).unwrap(), "null_project failed to restore null cone");
}
