# frontier-compare benchmark family

## What it measures

Two complementary lanes, with explicit guardrails against mixing them:

### Lane A — CORE-only suites (telemetry-rich)
Three suites that exercise structural properties only CORE can
expose:

- **`determinism`** — same prompt × N fresh runtimes → byte-identical
  `surface`, `grounding_source`, `register_canonical_surface`, and
  `trace_hash`.  `max_versor_condition` stays under `1e-6` throughout.
- **`truth_lock`** — known-truth + unknown-relation cases.  The
  known case must ground via pack/teaching; the unknown case must
  route to the deterministic refusal surface (no fabrication).
- **`axis_orthogonality`** — register / anchor-lens / language axes
  must compose without interfering: register variation moves the
  surface while holding `trace_hash` invariant; anchor-lens engages
  on the right lemmas only.

Lane A reads CORE-internal fields (`trace_hash`, `versor_condition`,
`register_id`, `register_variant_id`, `anchor_lens_id`,
`register_canonical_surface`, `pre_decoration_surface`) — these have
no equivalent on a frontier provider's stream of bytes, so the lane
requires `--provider core`.

### Lane B — Cross-provider suites (provider-agnostic)
One suite that runs over any registered provider:

- **`prompt_battery`** — 7 fixed prompts (definition, cause,
  verification, comparison, procedure, unknown intent shapes) ×
  adapter `(prompt) → surface`.  Per-case `passed` is loose by
  design: non-empty surface within elapsed-ms budget.  The point
  of the suite is **side-by-side surface evidence** across
  providers, not a quality verdict — reviewers diff
  `details.observation.surface` rows themselves.

Lane B uses the provider adapter pattern from ADR-0082:
`build_adapter(ProviderConfig) → (prompt) → str`.  CORE is one
adapter among `{core, openai, anthropic, ollama}`.

## Why it matters (structural win)

The frontier-comparison rule (`README.md`):

> If a frontier LLM can solve it, let it solve it.
> If CORE can solve something the LLM cannot structurally audit, CORE must prove it.
> If both solve it, compare correctness, determinism, traceability, latency, cost, memory, and failure mode.

Lane A measures the "structurally audit" half: properties an
external API stream cannot supply at all.  Lane B measures the
"both solve it" half: same prompt, side-by-side surfaces, operator
makes the judgment.

The lane split is **load-bearing**.  Forcing CORE-only suites
through non-CORE providers would silently produce reports with
empty telemetry fields — a worse failure mode than refusing.  The
runner enforces this at the CLI boundary (`--provider openai
--suite determinism` exits 2 with an operator-helpful message).

## How to run

### Lane A (CORE-only)
```bash
# All CORE-only suites
python -m evals.frontier_compare

# One suite, machine-readable
python -m evals.frontier_compare --suite determinism --json --report path/to/out.json
```

### Lane B (cross-provider)
```bash
# CORE adapter — no credentials needed
python -m evals.frontier_compare --provider core --suite prompt_battery --json

# Real provider — requires .env with credentials
python -m evals.frontier_compare --provider openai --suite prompt_battery
python -m evals.frontier_compare --provider openai --model gpt-4o-2024-08-06 --suite prompt_battery
python -m evals.frontier_compare --provider anthropic --model claude-sonnet-4-5 --suite prompt_battery
python -m evals.frontier_compare --provider ollama --model llama3.2 --suite prompt_battery
```

Non-CORE runs are **always persisted** to
`evals/frontier_compare/results/<provider>_<model>_<utc>.json`
even without `--report` — API calls are rate-limited / paid, so
losing the artifact is genuinely costly.

The `--model` flag is validated against `model_registry.py` —
floating aliases (e.g. raw `gpt-4o`) are rejected before any
benchmark cycles burn.  Dated snapshots only.

## How to read the report

Both lanes emit a `BenchmarkReport` JSON:

```json
{
  "benchmark_family": "frontier_compare_wave1",
  "model": "core-native",          // adapter model id
  "mode": "core",                  // provider name
  "suites": [
    {
      "suite": "prompt_battery",
      "case_count": 7,
      "primary_score": 1.000,
      "passed": true,
      "cases": [
        {
          "suite": "prompt_battery",
          "case_id": "definition_truth",
          "prompt": "What is truth?",
          "passed": true,
          "score": 1.0,
          "elapsed_ms": 12.4,
          "details": { "observation": { "surface": "...", ... } },
          "failures": []
        },
        ...
      ]
    }
  ],
  "summary": { "suite_count": 1, "case_count": 7, "primary_score": 1.0, "passed": true }
}
```

The HTML viewer at `evals/frontier_compare/ui/report_viewer.html`
loads any report JSON via a drag-and-drop / file picker.  It surfaces:

- Per-suite PASS/FAIL with primary score.
- Per-case row with case_id, status, failures, elapsed_ms.
- Drawer view of the full observation (CORE-only suites: full
  telemetry; cross-provider: surface + provider + model).

## Pass criteria

| Lane | Suite | Metric | Threshold | Current |
|------|-------|--------|-----------|---------|
| A | `determinism` | every prompt → 1 unique surface across `--runs` repeats | 1.00 | ✅ 1.00 |
| A | `determinism` | `max_versor_condition` | < 1e-6 | ✅ |
| A | `truth_lock` | known cases ground; unknown cases refuse | 1.00 | ✅ |
| A | `axis_orthogonality` | trace_hash invariant under register variation | true | ✅ |
| B | `prompt_battery` | all 7 cases produce non-empty surface w/ no adapter exception (CORE) | 1.00 | ✅ 1.00 |
| B | `prompt_battery` | cross-provider rows persisted to `results/` | true | ✅ |

`prompt_battery` does NOT score semantic quality — that is for human
review.  A green row means "the adapter answered without crashing,"
not "the answer was correct."

## When it has failed and why

- **2026-05-17** — `frontier_compare_wave1` Lane A first shipped (`#52`),
  all CORE-only suites green from day one.
- **2026-05-20** — ADR-0082 provider adapters shipped (`#58`,
  renumbered in `#59`) but were **unwired** — `runner.py` hardcoded
  `ChatRuntime`.  Cross-provider promise was shelf-ware.
- **2026-05-20** — Cross-provider Lane B added (`#61`).  Routing
  bug caught in the same PR: initial CLI dispatch sent
  `--suite prompt_battery` to the CORE-native runner even when
  `--provider=core`.  Fixed by making suite name the load-bearing
  axis (any `prompt_battery` request goes through the adapter
  path, CORE included).
- **2026-05-20** — Existing CORE-only telemetry would have been
  silently dropped if Lane B reused those suites.  Avoided by
  explicit lane split + loud CLI rejection of cross combinations.

## Runner

- `runner.py` — CORE-only suites (Lane A).
- `cross_provider.py` — `run_prompt_battery(adapter, *, cfg)` for
  Lane B.
- `__main__.py` — CLI dispatch.
- `providers.py` — `ProviderConfig`, `build_adapter`,
  `load_dotenv_if_present` (ADR-0082).
- `model_registry.py` — `ModelCard`, `require_model_card`,
  `list_registered_models` (ADR-0082).
- `ui/report_viewer.html` — standalone viewer.
- `results/` — per-run JSON artifacts.
