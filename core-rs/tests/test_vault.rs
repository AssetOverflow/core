use core_rs::vault::vault_recall_raw;
use core_rs::cga::embed_point_raw;

fn sample_point(seed: u64) -> [f32; 32] {
    let x = ((seed * 17 + 3) % 101) as f32 / 10.0;
    let y = ((seed * 23 + 7) % 101) as f32 / 10.0;
    let z = ((seed * 31 + 11) % 101) as f32 / 10.0;
    embed_point_raw(&[x, y, z])
}

#[test]
fn test_recall_self() {
    let versors: Vec<[f32; 32]> = (0..20).map(|i| sample_point(i as u64)).collect();
    for (i, query) in versors.iter().enumerate() {
        let results = vault_recall_raw(&versors, query, 1).unwrap();
        assert_eq!(results[0].0, i);
    }
}

#[test]
fn test_empty_vault() {
    let query = sample_point(0);
    let results = vault_recall_raw(&[], &query, 5).unwrap();
    assert!(results.is_empty());
}

#[test]
fn test_top_k_count() {
    let versors: Vec<[f32; 32]> = (0..10).map(|i| sample_point(i as u64)).collect();
    let query = sample_point(99);
    let results = vault_recall_raw(&versors, &query, 3).unwrap();
    assert_eq!(results.len(), 3);
}

#[test]
fn test_scores_descending() {
    let versors: Vec<[f32; 32]> = (0..10).map(|i| sample_point(i as u64)).collect();
    let query = sample_point(99);
    let results = vault_recall_raw(&versors, &query, 5).unwrap();
    for w in results.windows(2) {
        assert!(w[0].1 >= w[1].1);
    }
}
