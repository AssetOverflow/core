# sample-efficiency lane — findings (v1)

## v1 result

| Split | concepts | first_hit (mean) | saturation (mean) | saturation_rate | mean_score | replay |
|---|---|---|---|---|---|---|
| public/v1 | 10 | **1.0** | **4.0** | **1.0** | **1.0** | **1.0** |
| holdouts/v1 | 7 | **1.0** | **4.0** | **1.0** | **1.0** | **1.0** |

Every concept's curve: `[0, 1, 2, 3, 4]`.  Every replay across
fresh pipelines matches by `trace_hash`.

## What this measures

For each of 17 concepts (10 public + 7 holdouts disjoint), CORE
was given a curriculum of 4 chain corrections (`X is Y`, `Y is Z`,
`Z is W`, `W is V`) and asked the chain head (`"What is X?"`) after
each cumulative-correction count k ∈ {0,1,2,3,4}.  The reported
metric is the count of expected chain-tail tokens that appear in
the probe response surface.

The curve is **monotonic and linear**: one correction → one new
chain hop → one new token visible in the surface.  First-hit is
always k=1; saturation is always k=4 (curriculum length).

## Phase 4 framework discipline

Per `docs/capability_roadmap.md` Phase 4 ("Plot, do not threshold")
the lane reports quantitative curves and structural guarantees
rather than pass/fail thresholds.  The single structural gate —
`replay_determinism ≥ 0.95` — is satisfied at 1.0 across every
concept × every snapshot.  Each (k-corrections, probe) snapshot
on a fresh pipeline reproduces bit-stably; the curve is publishable
as data.

## What this curve shape says about CORE

- **Sample efficiency is 1.0 per correction on chain curricula.**
  No diminishing returns over the 0–4 range; no plateau.  The
  pipeline integrates each typed correction into the teaching-store
  graph and the inference operator surfaces the chain endpoint on
  the next probe.
- **No spurious confabulation.**  At k=0 (no corrections taught),
  hits = 0 across every concept — the model does not invent the
  curriculum's tokens.  Each new token appears only after the
  correction that introduces it.
- **Replay determinism preserves the curve.**  The curve is not a
  sampled estimate of a stochastic process; it is the deterministic
  function of (concept, k).  Frontier baselines cannot publish this
  curve at all because their per-snapshot output is not
  reproducible.

## What this curve shape does NOT measure

The contract is narrow by design; the linearity here is partly a
consequence of the curriculum shape (each correction extends a
chain by exactly one hop, and the probe walks that chain).  The
curve does not tell us:

- **Sample efficiency on non-chain knowledge.**  If the 4 corrections
  introduced unrelated facts (not a connected chain), would each
  still raise the probe score by 1?  v2 candidate: curricula that
  branch (`X is Y`, `X precedes Z`, `X grounds W`, ...).
- **Sample efficiency with distractor corrections.**  Curricula
  that interleave one or two irrelevant corrections between the
  load-bearing ones.  Does CORE still saturate at k=4 useful
  corrections, or does it pay for the distractors?
- **Sample efficiency on OOD probes.**  We probe the chain head.
  A v2 probe variant could ask about a chain-middle entity or a
  related-but-unstated concept.
- **Sample efficiency on novel relations.**  All curricula here
  use `is`.  v2 candidates: mixed-relation chains, novel relation
  predicates not in the cognition pack.

## v2 contract refinements (recorded for follow-on work)

1. **Branching curricula.**  Replace chain shape with one
   correction per relation type rooted at the same head.  Probe
   asks "What does X precede?", "What does X cause?", etc., scoring
   per-relation surface tokens.
2. **Distractor corrections.**  Each curriculum gets one or two
   off-chain corrections injected at random positions; saturation
   metric measures "useful corrections to saturate," controlling
   for distractor cost.
3. **OOD probes.**  Each concept gets a second probe asking about
   a chain-middle entity (not the head); the curve is re-scored.
4. **Confidence intervals.**  Today the curve is exact (replay
   determinism is 1.0).  v2 should add a CI when curricula become
   non-deterministic (e.g., when distractors are randomly
   positioned — the deterministic seed makes the position fixed
   per case, but a multi-seed sweep would give a CI).

## Status

v1 establishes the methodology and publishes the baseline curve.
The lane is the first quantitative-curve lane in the framework.
Phase 4 sample-efficiency v1 is **COMPLETE** with a clean linear
result; v2 refinements above are scoped follow-on work.

Structural-zero frontier baseline recorded
(`baselines/v1_structural_zero.json`): the per-snapshot
reproducibility that makes this curve publishable does not exist
in frontier systems.
