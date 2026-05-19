# Compound Intent Decomposition

**Lane:** `compound_intent_decomposition`

Scores whether a compound conversational prompt is decomposed into the
intended semantic atoms before generation. This lane is structural: it
does not grade paragraph fluency or final surface length.

## Case Schema

```json
{
  "id": "compound_truth_001",
  "prompt": "What is truth, and why does it matter?",
  "expected_atoms": [
    {"intent": "definition", "subject": "truth"},
    {"intent": "cause", "subject": "truth"}
  ]
}
```

## Metrics

- `decomposition_accuracy`: exact ordered atom match.
- `atom_precision`: expected atoms found in the same position.
- `subject_accuracy`: expected subjects recovered in the same position.

