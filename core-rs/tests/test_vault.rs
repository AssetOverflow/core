#[cfg(test)]
mod tests {
    use crate::vault::vault_recall_raw;
    use crate::versor::normalize_to_versor_raw;

    fn random_versor(seed: u64) -> [f32; 32] {
        let mut state = seed ^ 0xdeadbeef_cafebabe;
        let mut raw = [0f32; 32];
        for x in raw.iter_mut() {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            *x = ((state >> 33) as f32) / (u32::MAX as f32) * 2.0 - 1.0;
        }
        normalize_to_versor_raw(&raw).expect("normalize failed")
    }

    #[test]
    fn test_recall_self() {
        let versors: Vec<[f32; 32]> = (0..20).map(|i| random_versor(i as u64)).collect();
        for (i, query) in versors.iter().enumerate() {
            let results = vault_recall_raw(&versors, query, 1).unwrap();
            assert_eq!(results[0].0, i,
                "Versor {} should recall itself as top-1, got {}", i, results[0].0);
        }
    }

    #[test]
    fn test_empty_vault() {
        let query = random_versor(0);
        let results = vault_recall_raw(&[], &query, 5).unwrap();
        assert!(results.is_empty());
    }

    #[test]
    fn test_top_k_count() {
        let versors: Vec<[f32; 32]> = (0..10).map(|i| random_versor(i as u64)).collect();
        let query = random_versor(99);
        let results = vault_recall_raw(&versors, &query, 3).unwrap();
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn test_scores_descending() {
        let versors: Vec<[f32; 32]> = (0..10).map(|i| random_versor(i as u64)).collect();
        let query = random_versor(99);
        let results = vault_recall_raw(&versors, &query, 5).unwrap();
        for w in results.windows(2) {
            assert!(w[0].1 >= w[1].1, "Scores not descending");
        }
    }
}
