# provenance eval lane

## What it measures

Whether every articulated claim back-points to a concrete source (vault entry,
teaching event, or pack axiom / intent rule), and whether replaying the same
input on the same field state reproduces the trace bit-for-bit.

This tests the architectural claim that CORE's outputs are *grounded*: every
surface assertion is traceable to memory, teaching, or pack vocabulary, and the
pipeline is deterministic so traces are reproducible.

## Why it matters (structural win)

Frontier LLMs cannot produce per-claim provenance — their outputs are
synthesized from opaque weight activations with no back-pointer to source data.
CORE, by construction, produces:

- **Vault provenance** — `vault_hits > 0` indicates exact-recall sources
  consulted during the turn. Each hit can be resolved to a stored versor and
  its metadata.
- **Teaching provenance** — `reviewed_teaching_example` and
  `pack_mutation_proposal` carry stable IDs that survive replay.
- **Pack provenance** — `intent.tag` is grounded in pack-defined intent rules
  (a non-`UNKNOWN` tag means the input mapped onto an axiom in the active
  language pack).
- **Trace hash** — SHA-256 over a stable subset of the turn output is
  deterministic across hardware (floats rounded to 9 decimals).

A model that articulates without sources fails this lane. A model that
articulates correctly but cannot replay fails this lane. A model that passes is
demonstrating something frontier models cannot.

## Sub-metrics

### M1. Replay determinism

For every case, run the pipeline twice with two freshly-constructed runtimes
on the same prompt sequence. The trace hashes of corresponding turns must be
identical.

**Pass threshold:** 100% (any mismatch is a structural failure).

### M2. Input sensitivity

Pairs of cases with different prompts must produce different trace hashes. A
collision would mean the hash is not actually sensitive to its inputs.

**Pass threshold:** > 0.95.

### M3. Source attribution

For each case, the expected source kinds (`pack`, `vault`, `teaching`) must
appear in the computed `Provenance` for the final turn.

**Pass threshold:** > 0.95.

### M4. Source validity

Every source referenced in the `Provenance` must be valid:

- `pack` source: `intent.tag` is a known `IntentTag` enum value (not the empty
  string).
- `vault` source: every vault hit index is in `[0, len(vault))`.
- `teaching` source: every teaching proposal id is present in the
  `TeachingStore`.

**Pass threshold:** 100%.

## Case format

Each case is a JSONL row with the following fields:

```json
{
  "id": "PROV-V1-NNN",
  "category": "pack_axiom" | "vault_recall" | "teaching" | "mixed",
  "prime": ["optional", "list", "of", "prompts", "to", "run", "before"],
  "prompt": "the final prompt whose provenance is scored",
  "expected_sources": ["pack", "vault", "teaching"]
}
```

- `prime` (optional): zero or more prompts run before the scored prompt to
  seed the vault, the teaching store, or both.
- `expected_sources`: a non-empty subset of `{"pack", "vault", "teaching"}` —
  the kinds of source the final turn must back-point to.

## Pass thresholds (v1)

| Metric | Threshold |
|--------|-----------|
| replay_determinism | 1.00 |
| input_sensitivity  | > 0.95 |
| source_attribution | > 0.95 |
| source_validity    | 1.00 |
| Overall            | all four pass |

## Data layout

```
evals/provenance/
  contract.md
  runner.py
  dev/cases.jsonl
  public/v1/cases.jsonl
  holdouts/v1/cases.jsonl
  baselines/
  results/
```
