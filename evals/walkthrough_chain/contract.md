# Walkthrough Chain

**Lane:** `walkthrough_chain`

Scores bounded relation walks over the reviewed teaching-chain substrate.
This lane tests path structure: an anchor subject plus deterministic
relation hops. It is separate from paragraph or multi-sentence fluency.

## Case Schema

```json
{
  "id": "walk_truth_001",
  "prompt": "Walk me through truth.",
  "subject": "truth",
  "max_hops": 2,
  "expected_path": ["truth", "knowledge", "evidence"]
}
```

## Metrics

- `path_exact_rate`: actual path equals expected path.
- `anchor_rate`: first path element equals expected subject.
- `min_hop_rate`: actual path contains at least one relation hop.
- `bounded_rate`: path length never exceeds `max_hops + 1`.

