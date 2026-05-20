# Frontier Compare Benchmarks — Wave 1

This directory contains CORE's first no-handicap benchmark wave for comparing the CORE architecture against frontier-model behavior without pretending the systems are the same kind of machine.

The guiding rule:

```text
If a frontier LLM can solve it, let it solve it.
If CORE can solve something the LLM cannot structurally audit, CORE must prove it.
If both solve it, compare correctness, determinism, traceability, latency, cost, memory, and failure mode.
```

Wave 1 is deliberately local and CORE-native.  It does **not** call external frontier APIs, does **not** require provider keys, and does **not** change runtime behavior.  It creates the benchmark harness, report schema, recording UI, and first suites that measure the things CORE should already be able to defend:

* deterministic replay
* truth-lock / groundedness behavior
* register vs anchor-lens axis discipline
* compact machine-readable reports suitable for later head-to-head frontier runs
* a static visual report viewer for clean recordings and demos

Provider adapters for GPT / Claude / Gemini / open-weight baselines are intentionally deferred to a later wave so this PR remains testable without secrets.

---

## Why this exists

Most frontier benchmarks primarily measure final answer quality.  That is necessary, but insufficient for CORE's architectural thesis.  CORE must also be scored on properties a stochastic frontier model often cannot expose natively:

* trace stability
* explicit grounding source
* refusal instead of fabrication when evidence is absent
* stable proposition identity under presentation-register variation
* substantive movement under anchor-lens engagement
* versor closure health
* cost / latency / memory class

This benchmark family does not handicap CORE or LLMs.  It separates score axes so every model gets credit only for what it actually proves.

---

## Suites in Wave 1

### `determinism`

Runs the same prompts across fresh runtimes and checks whether the surface, grounding source, and key provenance fields remain stable.

Primary metric:

```text
trace_hash_stability proxy = exact replay stability across surfaces + provenance fields
```

### `truth_lock`

Runs a small closed-world prompt set covering known pack terms and unknown/OOV-like prompts.  Scores whether CORE emits grounded pack/teaching surfaces when evidence exists and bounded disclosure/OOV behavior when it does not.

Primary metrics:

```text
grounded_correct
correct_refusal_or_learning_invitation
fabrication_flags
```

### `axis_orthogonality`

Runs the same prompt across register packs and anchor-lens packs.  The register axis should preserve proposition identity / canonical surface where R6 says it must; the anchor-lens axis may move substantive proposition behavior where it engages.

Primary metrics:

```text
register_canonical_stability
surface_variation_observed
anchor_lens_engagement_observed
```

---

## Run

From the repository root:

```bash
CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run python -m evals.frontier_compare --suite all --json
```

Write a report:

```bash
CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run python -m evals.frontier_compare --suite all --json --report frontier_wave1.json
```

Human-readable table:

```bash
uv run python -m evals.frontier_compare --suite all
```

---

## Recording UI

Wave 1 includes a zero-dependency static viewer:

```text
evals/frontier_compare/ui/report_viewer.html
```

Use it for clean screen recordings, investor-safe internal demos, and rapid operator review.

Suggested recording flow:

```bash
CORE_BACKEND=numpy CORE_STRICT_MLX_ON_APPLE=0 \
uv run python -m evals.frontier_compare --suite all --json --report frontier_wave1.json

open evals/frontier_compare/ui/report_viewer.html
```

Then drag `frontier_wave1.json` into the page.  The viewer renders:

* executive score cards
* suite pass/fail states
* per-case prompts
* failure reasons
* expandable raw details

The viewer is intentionally static:

* no build step
* no framework dependency
* no network calls
* no report data leaves the browser

This keeps the benchmark presentation simple, pretty, durable, and easy to record without adding UI bloat to the runtime.

---

## Report contract

The runner emits a stable JSON object:

```json
{
  "benchmark_family": "frontier_compare_wave1",
  "model": "core",
  "mode": "native",
  "suites": [...],
  "summary": {
    "suite_count": 3,
    "case_count": 0,
    "passed": true,
    "primary_score": 1.0
  }
}
```

Each case records:

* prompt/config identity
* pass/fail
* measured fields
* failure reasons
* elapsed milliseconds

No raw hidden state is emitted.  The report is safe for internal benchmarking and can be sanitized for public progress summaries later.

---

## Non-goals for Wave 1

* No provider API calls.
* No API key handling.
* No leaderboard claims.
* No SWE-bench clone.
* No multimodal tasks.
* No benchmark that depends on stochastic sampling.
* No changes to `ChatRuntime` behavior.
* No frontend framework or app server.

---

## Next waves

Suggested next branches:

1. `feat/frontier-compare-provider-adapters` — model adapter interface for frontier APIs and local baselines.
2. `feat/frontier-compare-reliability-surface` — repeated-run / perturbation / failure-injection surface.
3. `feat/frontier-compare-long-horizon-state` — 100+ turn state consistency sessions.
4. `feat/frontier-compare-curated-index` — closed-corpus provenance benchmark.
5. `feat/frontier-compare-coding-microbench` — generated private repo bug-fix benchmark.
