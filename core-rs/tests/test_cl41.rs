use core_rs::cl41::{geometric_product_raw, reverse_raw};

fn basis(i: usize) -> [f32; 32] {
    let mut v = [0f32; 32];
    v[1 + i] = 1.0;
    v
}

fn scalar(s: f32) -> [f32; 32] {
    let mut v = [0f32; 32];
    v[0] = s;
    v
}

#[test]
fn test_e1_squared_is_plus1() {
    let e1 = basis(0);
    let r = geometric_product_raw(&e1, &e1).unwrap();
    assert!((r[0] - 1.0).abs() < 1e-6, "e1^2 should be +1, got {}", r[0]);
}

#[test]
fn test_e5_squared_is_minus1() {
    let e5 = basis(4);
    let r = geometric_product_raw(&e5, &e5).unwrap();
    assert!((r[0] + 1.0).abs() < 1e-6, "e5^2 should be -1, got {}", r[0]);
}

#[test]
fn test_e1_e2_anticommute() {
    let e1 = basis(0);
    let e2 = basis(1);
    let e1e2 = geometric_product_raw(&e1, &e2).unwrap();
    let e2e1 = geometric_product_raw(&e2, &e1).unwrap();
    for i in 0..32 {
        assert!((e1e2[i] + e2e1[i]).abs() < 1e-6, "e1*e2 + e2*e1 != 0 at index {}", i);
    }
}

#[test]
fn test_scalar_identity() {
    let e1 = basis(0);
    let one = scalar(1.0);
    let r = geometric_product_raw(&one, &e1).unwrap();
    assert!((r[1] - 1.0).abs() < 1e-6, "1*e1 should be e1");
}

#[test]
fn test_reverse_grade2_sign() {
    let mut a = [0f32; 32];
    a[6] = 1.0;
    let r = reverse_raw(&a);
    assert!((r[6] + 1.0).abs() < 1e-6, "reverse of grade-2 blade should negate");
}

#[test]
fn test_reverse_grade1_unchanged() {
    let e1 = basis(0);
    let r = reverse_raw(&e1);
    assert!((r[1] - 1.0).abs() < 1e-6, "reverse of grade-1 blade should be unchanged");
}
