use core_rs::vault::vault_recall_raw;
use core_rs::versor::normalize_to_versor_raw;

fn sample_versor(seed: u64) -> [f32; 32] {
    let mut raw = [0f32; 32];
    for (idx, x) in raw.iter_mut().enumerate() {
        let value = ((seed as usize + idx * 17 + 3) % 101) as f32;
        *x = (value / 50.0) - 1.0;
    }
    normalize_to_versor_raw(&raw).expect("normalize failed")
}

#[test]
fn test_recall_self() {
    let versors: Vec<[f32; 32]> = (0..20).map(|i| sample_versor(i as u64)).collect();
    for (i, query) in versors.iter().enumerate() {
        let results = vault_recall_raw(&versors, query, 1).unwrap();
        assert_eq!(results[0].0, i);
    }
}

#[test]
fn test_empty_vault() {
    let query = sample_versor(0);
    let results = vault_recall_raw(&[], &query, 5).unwrap();
    assert!(results.is_empty());
}

#[test]
fn test_top_k_count() {
    let versors: Vec<[f32; 32]> = (0..10).map(|i| sample_versor(i as u64)).collect();
    let query = sample_versor(99);
    let results = vault_recall_raw(&versors, &query, 3).unwrap();
    assert_eq!(results.len(), 3);
}

#[test]
fn test_scores_descending() {
    let versors: Vec<[f32; 32]> = (0..10).map(|i| sample_versor(i as u64)).collect();
    let query = sample_versor(99);
    let results = vault_recall_raw(&versors, &query, 5).unwrap();
    for w in results.windows(2) {
        assert!(w[0].1 >= w[1].1);
    }
}
