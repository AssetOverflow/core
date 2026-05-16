# sample-efficiency eval lane

## What it measures

How many reviewed corrections CORE needs before a probed concept
produces grounded, coherent answers.  This is the first
**quantitative-curve** lane in the framework (Phase 4 per
`docs/capability_roadmap.md`): the output is a curve per concept,
not a pass/fail score per case.

For each concept, the runner teaches one correction at a time and
probes the concept after each correction.  Plotting probe score as
a function of corrections-given yields the *corrections-to-
competence curve*.

## Why quantitative

Frontier models hide their per-correction learning behind the
training run; the practitioner sees the final checkpoint and not
the slope.  CORE's reviewed-teaching loop makes per-correction
learning observable by construction.  This lane publishes the
slope.

## Setup per concept

- A **curriculum**: an ordered list of correction utterances
  about the concept (typically 5–8).  Each correction is a real
  proposition the teaching review will accept under the existing
  identity-override defense.
- A **probe**: a single question whose expected answer is the
  union of tokens introduced by the curriculum.  Probes are
  re-asked after each cumulative correction count.

After teaching `k` corrections (k = 0, 1, 2, …, n), the runner
asks the probe and records:

- `cumulative_token_hit_count` — how many of the curriculum's
  expected tokens appear (case-insensitively, token-bounded) in
  the probe response's `surface` or `walk_surface`.
- `vault_hits` — direct vault retrieval count for the probe.
- `trace_hash` — the deterministic turn hash for this snapshot.

## Quantities published

For each concept the lane reports:

- The full curve: `[(k, cumulative_token_hit_count, vault_hits)]`
  for k from 0 to len(curriculum).
- `corrections_to_first_hit` — smallest k where
  `cumulative_token_hit_count ≥ 1`.  `None` if never.
- `corrections_to_saturation` — smallest k where
  `cumulative_token_hit_count == len(curriculum)`.  `None` if
  never reached.
- `saturation_score` — final `cumulative_token_hit_count /
  len(curriculum)` after all corrections taught.

Aggregate metrics across concepts:

- `mean_corrections_to_first_hit` (across concepts that hit).
- `mean_corrections_to_saturation` (across concepts that
  saturate).
- `saturation_rate` — fraction of concepts that reach
  full coverage by curriculum end.
- `replay_determinism` — fraction of snapshots where re-running
  the (curriculum-up-to-k, probe) sequence produces the same
  trace_hash.

## v1 thresholds (soft)

Per the Phase 4 framework discipline ("Plot, do not threshold"),
the lane does **not** have pass/fail thresholds in the usual
sense.  For monitoring purposes the report includes one structural
gate:

- `replay_determinism ≥ 0.95` — quantitative measurement is
  meaningful only when each data point is reproducible.

Curve quality is reported as data; interpretation is left to the
reader.

## Anti-overfitting (concept selection discipline)

- Concepts are drawn from `en_core_cognition_v1` so the curriculum
  is grounded in the standard pack.
- Public and holdouts use disjoint concept sets.
- Each correction in a curriculum introduces exactly one new
  token from the expected-token set (no compound corrections
  inflate the score).
- The probe form is fixed per concept and does not change between
  snapshots.

## Replay determinism

Each snapshot (curriculum-up-to-k, probe) is run on a *fresh*
`CognitiveTurnPipeline`.  The same snapshot is re-run a second
time on a second fresh pipeline; identical trace_hash is the
structural-correctness gate for this lane.  Without it the curve
is not reproducible and the published numbers cannot be trusted.

## What this lane does not measure

- Compositional generalisation (covered by compositionality).
- Cross-domain transfer (covered by cross-domain-transfer).
- Identity stability (covered by adversarial-identity).
- Vault-cost scaling (covered by long-context-cost — Phase 4
  follow-on lane).

The discipline is narrow: how fast does *this concept* gain
visible competence as corrections accumulate?
