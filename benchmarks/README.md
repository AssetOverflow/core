# Benchmarks

Operator-runnable measurement harnesses for CORE. Each suite anchors a
specific load-bearing claim in numbers an outsider can reproduce.

```
core bench --suite articulation
core bench --suite determinism --runs 50
core bench --suite teaching-loop --runs 100
core bench --suite cost --runs 100
core bench --suite latency
core bench --suite speedup
core bench --suite versor
core bench --suite convergence
core bench --suite realizer
```

This document covers all benchmark suites in the harness, with
emphasis on the post-Phase-4 articulation suite (the newest and most
comparative one).

---

## Why these benchmarks exist

CORE makes three structurally unusual claims:

1. **Reconstruction over storage.** The user-facing surface is
   re-derived from immutable corpora + ratified packs every turn,
   not sampled from a stochastic process. → *Same input must produce
   byte-identical output across runs.*
2. **Bounded footprint.** No transformer weights, no rolling token
   history, no embedding store. → *Memory stays flat across thousands
   of turns.*
3. **Traceable grounding.** Every surface carries a grounding tag
   pointing at the resolving pack id or chain id. → *We can audit
   why a sentence was produced.*

These claims need evidence, not assertions. The benchmarks here are
the evidence.

---

## Suite catalogue

| Suite | Anchors | What it does | How to read it |
|---|---|---|---|
| `articulation` | Phase 4 capability claim | Fires every supported intent shape; reruns to prove determinism; samples RSS across many turns; walks cross-topic prompts; side-by-side with Ollama | All-identical on determinism; flat RSS; OOV fall-through visible; ollama shows ≥2 unique surfaces per prompt |
| `determinism` | "Same input → same output" | N reruns of the pulse loop, compares trace hashes | `unique_hashes` should be 1 |
| `teaching-loop` | "Replayable learning" | Builds a proposal, runs replay, accepts, asserts active corpus is byte-identical to a deterministic baseline across N runs | `unique(proposal_id)` and `unique(chain_id)` should both be 1 |
| `cost` | Tier-4 CLAIMS.md cost claim | Wall + CPU seconds per turn, $/1000-turn at a disclosed cloud rate, frontier price context | Higher throughput / lower $ = better; frontier pricing context for apples-to-apples |
| `latency` | Time-to-first-surface | Single pulse call timed | Lower ms = better |
| `speedup` | Rust backend lift | Python vs Rust on identical workload | Speedup factor > 1× when Rust available |
| `versor` | CGA field invariant | Walks the pulse loop and checks `versor_condition(F) < 1e-6` on every transition | Must always pass; failures point at the operator that broke closure |
| `convergence` | Pulse loop terminates | Field returns to a stable state within bounded iterations | Bounded — no runaway |
| `realizer` | Pack template coverage | Counts realizer hits vs misses on a fixed prompt set | Higher coverage = better |

---

## The `articulation` suite (Phase 4)

The newest and most operator-facing bench. Anchors the post-ADR-0067
claim that CORE can:

- Reach every supported intent shape (DEFINITION / RECALL / CAUSE /
  VERIFICATION / COMPARISON / CORRECTION / PROCEDURE / NARRATIVE /
  EXAMPLE) plus the OOV fall-through plus cross-pack chains.
- Emit byte-identical surfaces across reruns.
- Hold memory roughly flat across hundreds of turns.
- Maintain thread context across topic shifts.
- Outperform stochastic models on the determinism axis the system is
  actually designed for.

### Running it

```
# Quick smoke (no Ollama):
core bench --suite articulation --runs 5 --turns 50

# Full run with Ollama side-by-side (needs `ollama` on PATH + a model):
core bench --suite articulation \
    --runs 10 --turns 200 \
    --ollama-model llama3:8b --ollama-reruns 3 \
    --report bench_reports/articulation.json

# Machine-readable JSON:
core bench --suite articulation --json
```

Flags:

- `--runs N` — Determinism rerun count per prompt. Higher is stricter.
- `--turns N` — Footprint sample run length. The bench drives one
  `ChatRuntime` through `N` cold-start prompts and samples RSS.
- `--ollama-model MODEL` — Ollama model id (e.g. `llama3:8b`,
  `granite3.3:8b`). Omit to skip the side-by-side.
- `--ollama-reruns N` — Per-prompt rerun count for Ollama. The bench
  measures `unique_surfaces / reruns` for each side.
- `--report PATH` — Write the full JSON report to disk in addition to
  printing.

### Sub-benches

#### 1. Intent breadth

Sends one prompt per intent shape (12 prompts total covering 9
intents + OOV + 2 cross-pack variants) through fresh `ChatRuntime`
instances. Reports the classified intent, the grounding tag, and a
surface snippet.

**Read it like this:**

- **Good:** Every intent fires; grounding tier matches the prompt
  (e.g. CAUSE on `knowledge` should route to `teaching`).
- **Neutral:** A prompt routes to `vault` instead of `pack`/`teaching`
  — that's CORE's normal recall path on warm vaults, but the breadth
  bench uses fresh runtimes so vault hits would indicate a stub
  injection issue worth investigating.
- **Bad:** Any prompt routes to `none` when the breadth set says it
  shouldn't. Means a pack/teaching path regressed.

#### 2. Determinism

Five prompts × N reruns × fresh `ChatRuntime` each time. Counts
unique surfaces per prompt.

**Read it like this:**

- **Good:** `unique_surfaces == 1` for every prompt. This is the
  *primary* claim — any failure here is load-bearing.
- **Neutral:** `unique_surfaces > 1` only for prompts that route
  through `vault` (vault recall is content-similar but not
  byte-stable across compile permutations); reroute the prompt or
  fix the cold-start path.
- **Bad:** `unique_surfaces > 1` on a pack/teaching/cross-pack
  prompt. That means a supposedly deterministic composer is reading
  non-deterministic state. Stop and bisect.

#### 3. Memory footprint

Single `ChatRuntime`, `turns` prompts (cycling through the breadth
set), RSS sampled every `sample_every` turns via psutil.

**Read it like this:**

- **Good:** Per-turn ΔRSS in the low tens of KiB. Vault grows
  bounded with stored states; pack caches are immutable.
- **Neutral:** Linear growth on the first ~100 turns as caches warm
  up, then flat. Inspect the samples list — if it plateaus, healthy.
- **Bad:** Per-turn ΔRSS in MiB or growth that does not plateau.
  Points at unbounded list/dict accumulation; check vault eviction
  and any `lru_cache(maxsize=None)` introductions.

#### 4. Cross-topic context

One runtime with `thread_anaphora=True`. Walks 8 prompts that switch
between cognition, relations, and cross-pack subjects. Reports per-
turn anaphora-fire status.

**Read it like this:**

- **Good:** The state survives across the walk — `thread_context`
  retains every turn's `TurnSummary`. The bench prints which turns
  fired anaphora.
- **Neutral / expected:** `anaphora_fire_count == 0` once the vault
  has content. Per ADR-0066 §Future ADRs, anaphora today fires only
  when BOTH the prior and current turn are pack/teaching tier. After
  the first turn populates the vault, recall hits the vault and the
  anaphora prefix is suppressed. This is the architectural ceiling,
  not a defect.
- **Bad:** Exceptions or `grounding_source == "none"` on prompts
  that should ground. Means an intent route or pack mount broke.

#### 5. Ollama side-by-side

Opt-in. Runs three prompts through both CORE and an Ollama model,
each `N` times. Reports unique-surface count per side.

**Read it like this:**

- **Good (the whole point):** CORE shows `unique_surfaces == 1` for
  every prompt regardless of rerun count. Ollama shows
  `unique_surfaces >= 2` on most prompts even with low rerun count
  because LLMs are stochastic.
- **Why this matters:** A user asking the same question twice should
  get the same answer. CORE guarantees this structurally. LLMs at
  `temperature=0` come close but still vary because of GPU
  non-determinism, MoE routing, and sampling on tie-break logits.
- **Comparing surfaces:** Don't compare *content quality* between
  CORE and Ollama. They optimise different objectives:
  - CORE: traceable, deterministic, every token sourced.
  - Ollama: fluent, broad, stochastic, no provenance.
- **What "fail" looks like:** Ollama is not on PATH → skipped (not
  failed). Ollama returns `<ollama error: ...>` → that prompt is
  excluded from the unique-surface count.

### Comparison caveat

CORE and Ollama are not running the same task in a fair sense:

- **Different vocabulary surface area.** Ollama has read most of the
  internet. CORE has 3 ratified packs (~150 lemmas total). Asking
  `"What is photosynthesis?"` of CORE produces the OOV invitation by
  design; asking it of Ollama produces a paragraph. *Neither is
  wrong* — the systems make different promises.
- **Different success criteria.** CORE wins on determinism,
  provenance, footprint, replayability. Ollama wins on coverage and
  fluency. The bench measures the axes CORE was designed for.
- **Different latency profile.** CORE: single-digit ms. Ollama:
  hundreds of ms to seconds depending on model. The articulation
  bench does not time Ollama; the `cost` bench is the place for
  per-turn timing.

If a prompt is in CORE's pack vocabulary, the side-by-side is
direct: same prompt, identical surface from CORE every run, varying
surface from Ollama every run. If a prompt is OOV for CORE, the
side-by-side is informational: shows what the gradient does (CORE
admits it doesn't know; Ollama hallucinates plausibly).

---

## Other suites — quick reference

### `determinism`

`core bench --suite determinism --runs 50`

The original determinism bench: drives the *pulse loop* (not the
chat runtime) N times, hashes the full trace, asserts a single
unique hash. The articulation suite's determinism sub-bench tests
the chat runtime; this one tests the deeper pulse loop.

### `teaching-loop`

`core bench --suite teaching-loop --runs 100`

Anchors ADR-0055..0057. Drives the discovery → proposal → replay →
accept loop end-to-end N times. Asserts the resulting active
corpus is byte-identical to a deterministic baseline and that the
proposal id + chain id are stable across runs.

### `cost`

`core bench --suite cost --runs 100`

Measures wall-seconds, CPU-seconds, throughput, and derives
$/1000-turn at a disclosed cloud-instance rate. Reports frontier
LLM per-token pricing context. Energy/joules is *not* reported
because honest measurement requires privileged RAPL/IOKit access.

### `latency` / `speedup` / `versor` / `convergence` / `realizer`

These are the original benches in `benchmarks/run_benchmarks.py` —
each runs a single measurement and emits a `BenchResult(passed,
metric, unit, detail)`. Run them when investigating regressions in
the specific axis named.

---

## Operator workflow

1. **After any non-trivial change**, run:
   ```
   core test --suite cognition -q
   core eval cognition
   core bench --suite articulation --runs 5 --turns 50
   ```
2. **Before merging a PR that touches surface composers, runtime,
   packs, or teaching corpora**, also run:
   ```
   core bench --suite teaching-loop --runs 50
   core bench --suite articulation --runs 20 --turns 200 \
       --ollama-model llama3:8b --report bench_reports/<branch>.json
   ```
3. **When investigating a regression**, run the targeted suite:
   - Determinism breakage → `--suite determinism --runs 50`
   - Memory growth → `--suite articulation --turns 1000`
   - Versor closure error → `--suite versor`
   - Pack template miss → `--suite realizer`

The bench reports go under `bench_reports/` (gitignored by
default). Include the JSON report path in the PR description when
the change is bench-relevant.

---

## What the benchmarks intentionally do NOT do

- **Score linguistic quality.** Fluency, helpfulness, "naturalness"
  — none of these are CORE's optimisation target. The system
  optimises for determinism, provenance, and bounded footprint.
- **Report fabricated joules.** Energy measurement requires
  privileged RAPL/IOKit access we don't have in a plain Python
  process. `cost.cpu_seconds` is the honest proxy.
- **Compare against LLMs on tasks LLMs are designed for.** A bench
  that asks "who writes the better essay?" is the wrong question
  for CORE. The Ollama side-by-side measures the *one axis where
  the comparison is meaningful*: same input → same output.
- **Bench-game CORE.** Every prompt set is in-tree; modifications
  show up in PRs; no "private eval set" trick.

---

## Adding a new bench

1. Drop a module in `benchmarks/<name>.py` with a `run_<name>()`
   entrypoint returning a dataclass `Report` with `as_dict()` and
   `summary()` methods.
2. Add a dispatch branch in `core/cli.py:cmd_bench`.
3. Add the suite name to `bench.add_argument("--suite", choices=...)`.
4. Add a row to the catalogue table at the top of this README.
5. Add tests under `tests/test_<name>_bench.py` that pin the report
   shape (not the runtime behaviour — that's covered by lanes).
