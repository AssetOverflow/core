# symbolic-logic eval lane

## What it measures

CORE's foundation for proposition-based inference: when premises are
taught via the correction loop, the resulting field state and vault
content carry the chain in a *deterministic*, *premise-sensitive*,
*recallable* form.

v1 measures three structural foundations on which a future inference
engine would be built; it does **not** test that CORE applies named
inference rules (modus ponens, modus tollens, syllogism) directly.
See `gaps.md` for the architectural finding and roadmap toward v2.

## Why it matters (structural win)

Frontier LLMs produce inference-like text but provide no first-class
evidence that the chain was actually stored, replayed deterministically,
or that the produced trace depends on the specific premises given.
Their inference is a single forward pass over a stochastic policy.

CORE returns:

- `CognitiveTurnResult.vault_hits` — how many premises the probe
  recalled.
- `CognitiveTurnResult.trace_hash` — a SHA-256 over deterministic
  pipeline state.
- `CognitiveTurnResult.pack_mutation_proposal` — datestamped record
  for each correction-intent turn.

These let a downstream caller verify three properties of any
premise-chain inference:

1. **Recall**: the probe can see the chain (vault_hits > 0).
2. **Replay**: replaying the same chain produces the same trace.
3. **Storage**: each correction-intent premise becomes one stored
   proposal.

## Patterns covered (v1)

| Pattern | Shape |
|---------|-------|
| `modus_ponens_chain` | A→B, B→C, probe A |
| `modus_tollens_chain` | A→B, ¬B, probe |
| `syllogism` | A is B, B is C, probe A |
| `chain_recall` | Longer chains of 3-5 hops |
| `negation` | A, then ¬A, probe |

All patterns use the same scoring; the pattern label is metadata for
later analysis.

## Sub-metrics

### M1. premise_recall

For each case, probe `vault_hits >= min_vault_hits` (case threshold).
Demonstrates that the premise chain was stored and is recallable from
the probe.

**Pass threshold:** ≥ 0.80 of cases meet their `min_vault_hits`.

### M2. replay_determinism

Each case runs twice on fresh pipelines.  Both runs must produce the
same `trace_hash`.

**Pass threshold:** ≥ 0.95 of cases replay identically.

### M3. proposal_storage

Each correction-intent premise should produce a `PackMutationProposal`.
For each case, the count of fired proposals must equal
`expected_proposals`.

**Pass threshold:** ≥ 0.80 of cases match their `expected_proposals`.

### M4. overall

All three sub-metrics pass.

## Pass thresholds (v1)

| Metric | Threshold |
|--------|-----------|
| premise_recall | ≥ 0.80 |
| replay_determinism | ≥ 0.95 |
| proposal_storage | ≥ 0.80 |
| Overall | all three pass |

## Case format

```json
{"id":"SYM-001",
 "pattern":"modus_ponens_chain",
 "premises":["What is truth?","Actually truth is wisdom.",
             "What is wisdom?","Actually wisdom is light."],
 "probe":"What is truth?",
 "expected_proposals":2,
 "min_vault_hits":1}
```

Fields:
- `id`: stable case identifier
- `pattern`: inference shape label (metadata only)
- `premises`: ordered list of prompts to run before probe
- `probe`: the scored prompt
- `expected_proposals`: count of correction-intent premises
- `min_vault_hits`: minimum vault_hits the probe must achieve

## Data layout

```
evals/symbolic_logic/
  contract.md
  gaps.md
  runner.py
  dev/cases.jsonl
  public/v1/cases.jsonl
  holdouts/v1/cases.jsonl
  results/
```
