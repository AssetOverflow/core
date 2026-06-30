# ADR-0042: Audit Tour Demo — `core demo audit-tour`

**Status:** Accepted (2026-05-17)
**Author:** Joshua Shay + planner pass
**Companion docs:** [`ADR-0027` through `ADR-0041`](.)

## Context

The pack-layer architecture story (ADR-0027 → ADR-0041) is
load-bearing but technical.  The strategic gap raised externally:

> Where's the demo I can show a non-technical investor in 90
> seconds?

`core pulse` exists; `core demo phase5 / phase6 / all` exist and
support the ADR-0024 chain claims.  Neither is the *audit-and-policy*
story.  The four pack-layer claims that should be the headline:

* identity is geometric and load-bearing (not prompt-veneer);
* safety is the universal floor, with deterministic typed refusal;
* ethics commitments choose their remediation per pack (audit /
  hedge / refuse);
* the same input always produces byte-identical audit lines.

These are *exactly* the claims that distinguish CORE from any LLM
wrapper, and the test suite already proves all four.  The missing
piece was a single-command narrative artifact that demonstrates each
claim with live evidence from the runtime, runs end-to-end with no
external dependencies, and emits both a human narration and a stable
machine-readable JSON report.

## Decision

Ship `core demo audit-tour` as a new target on the existing `core
demo` subcommand.  The tour runs four scenes; each scene exercises
the live pack-layer surface and reports a falsifiable result.

### Scene contract

| Scene | Claim | Evidence |
|---|---|---|
| **S1** | Identity is geometric, not prompt-veneer. | Load three identity packs (`default_general_v1`, `generosity_first_v1`, `precision_first_v1`); report distinct alignment thresholds and hedge phrases. Differences come from the JSON pack files, not from prompts. |
| **S2** | Safety is the universal floor. | Register a forced runtime-checkable safety predicate; show the deterministic typed refusal string and that `surface != walk_surface` (evidence preserved on `walk_surface`). |
| **S3** | Ethics commitments choose remediation. | Two runtimes; the second's ethics pack opts `acknowledge_uncertainty` into `hedge_commitments`. Construct a synthetic runtime-checkable violation and show `should_inject_hedge` returns False on the default pack and True on the deployment pack; print the hedge prefix and a worked example of `inject_hedge`. Stub/main path is orthogonal — the pack-driven policy decision is what's being demonstrated. |
| **S4** | Deterministic replay across runtime instances. | Two fresh `ChatRuntime` instances; same input; the emitted JSONL audit lines (ADR-0040) are byte-identical. |

### Design choices

* **Load-bearing evidence over surface inspection.**  The first draft
  compared `response.surface` across packs and across opt-in/no-opt-in.
  This was weak: cold-start hits the stub path, where pack differences
  don't manifest in the surface (by design).  The shipped version
  pulls evidence from the *structural* surface — loaded manifold
  fields, pack opt-in lists, pure helper functions — which is what
  actually distinguishes the packs.  No fake claims.
* **Pure-helper Scene 3.**  Scene 3 exercises `should_inject_hedge`,
  `build_hedge_prefix`, and `inject_hedge` against a synthetic
  ethics verdict rather than relying on `chat()` to fire a hedge.
  Rationale: ADR-0038 specifies that the stub path skips hedge
  injection by design, so a cold-start chat call would never hedge
  even with the opt-in.  The honest demonstration is "given a
  runtime-checkable violation, the pack-driven policy decides the
  remediation," which is exactly what the pure helpers verify.
  End-to-end main-path hedge injection is covered in
  `tests/test_hedge_injection.py` and referenced in the tour's
  evidence comment.
* **`emit_json` toggles all narration via a module-level
  `_VERBOSE` flag.**  When `--json` is passed, the entire scene
  print stack short-circuits to a no-op so the only output is the
  JSON report from the CLI command.  This keeps the JSON parseable
  for downstream tooling.
* **No external dependencies.**  No LLM API calls, no network, no
  filesystem writes beyond the existing `_write_results_index`
  hook on `core demo`.
* **Deterministic.**  Every claim flag — `all_claims_supported`,
  the per-scene booleans, the byte-identity check — is
  reproducible across runs.  Test harness verifies this.

### Wire format

The structured report (`run_tour(emit_json=True)`) returns:

```json
{
  "all_claims_supported": true,
  "scene_1_identity_geometric": {
    "distinct_alignment_thresholds": 3,
    "distinct_hedge_phrases": 2,
    "pack_shapes": { /* per-pack value_axes_count, alignment_threshold, hedge_soft */ }
  },
  "scene_2_safety_typed_refusal": {
    "refusal_emitted": true,
    "refused_surface": "I cannot proceed — boundary violated: safety:preserve_versor_closure",
    "walk_surface": "I don't know — insufficient grounding for that yet."
  },
  "scene_3_ethics_hedge_opt_in": {
    "default_fires": false,
    "deployment_fires": true,
    "hedge_prefix": "Perhaps",
    "hedged_surface": "Perhaps the answer is X",
    /* + pack opt-in lists + sample surface */
  },
  "scene_4_deterministic_replay": {
    "byte_identical": true,
    "line_1_sha_preview": "...",
    "line_2_sha_preview": "..."
  }
}
```

### CLI integration

```text
core demo audit-tour          # human narration to stdout
core demo audit-tour --json   # structured report to stdout, no narration
```

Lives alongside the existing `phase5` / `phase6` / `all` /
`list-results` targets.

## Consequences

### Positive

* **First investor-grade walkthrough of the pack-layer story.**
  Runs end-to-end, no external dependencies, in seconds.  Every
  claim is testable in the same repo.
* **Reusable substrate.**  The pack-shape comparison in Scene 1,
  the pure-helper evidence in Scene 3, and the cross-instance
  replay check in Scene 4 are all sub-components that can be reused
  for per-domain pack ratification demos and replay benchmarks
  down the line.
* **Honest evidence.**  No staged inputs, no LLM-prompt-engineering
  tricks.  The evidence comes from the same code paths the test
  suite exercises.  Anyone reading
  `tests/test_audit_tour.py` can verify the four claim flags hold.
* **JSON contract is stable.**  Downstream tooling (dashboards,
  CI gates, audit reports) can consume the JSON report and detect
  regressions automatically.
* **Test gate.**  `tests/test_audit_tour.py` asserts
  `all_claims_supported is True` — if any scene's claim flips to
  False, the test fails and we catch the regression before it
  ships.

### Negative / risks

* **Scene 3 is a synthetic-verdict demonstration, not an
  end-to-end chat call.**  This is an honest trade: ADR-0038 says
  stub paths skip hedge by design, so a cold-start chat call
  cannot demonstrate hedge injection end-to-end without first
  priming the vault.  The pure-helper evidence is load-bearing for
  the policy claim being made; main-path end-to-end is asserted
  separately by `tests/test_hedge_injection.py`.  The tour text
  explains this trade-off.
* **Scene 1's surface comparison was removed.**  The first draft
  printed `response.surface` per pack and tried to claim "three
  different surfaces."  This was false on cold start.  The
  shipped Scene 1 reports structural pack differences instead,
  which is honest but less visually striking than the original
  pitch implied.  Future work (vault priming for the demo, or a
  curated input that reaches the main path) could restore the
  surface-level comparison.
* **No vault priming for cold-start demo coverage.**  The tour
  intentionally runs on a cold vault to keep determinism and
  speed.  A future scene could ratify a tiny domain pack and
  demonstrate main-path articulation, but that's its own ADR.
* **Module-level `_VERBOSE` flag is a small global.**  Acceptable
  for a top-level demo entry point; would not survive in shared
  library code.

## Verification

* `tests/test_audit_tour.py` — 8 tests covering:
  `all_claims_supported` flag; Scene 1 distinct
  thresholds/hedges; Scene 2 typed refusal + walk-surface
  preservation; Scene 3 pack-drives-remediation (default off,
  deployment on, hedged surface starts with hedge prefix); Scene 4
  byte-identical replay; narration prints under no-JSON;
  `emit_json=True` suppresses narration entirely; JSON report
  round-trips through `json.dumps/loads`.
* Combined pack-layer + telemetry + tour suite: **220 tests, all
  green** (was 212 after ADR-0041; +8).
* CLI suites unchanged: smoke 67, runtime 19, cognition 121.
* `core eval cognition`: intent 100%, versor_closure 100% —
  baseline preserved.
* Manual smoke: `core demo audit-tour` and `core demo audit-tour
  --json` both produce expected output; `all_claims_supported`
  is `true`.

## Open questions deferred to a future ADR

1. **Vault priming for main-path scenes.**  A precomputed pack
   that seeds the vault with the demo input's terms would let
   Scene 1 demonstrate *surface-level* divergence across identity
   packs (not just structural divergence).
2. **Per-domain ratified pack demo.**  Once a medical or legal
   ethics pack is ratified end-to-end, the tour gains a fifth
   scene: "domain pack swap mid-session, same engine, different
   refusal/hedge behavior."  This is the natural extension that
   completes the BD pitch.
3. **Replay benchmark vs. transformer baseline.**  ADR-0040's
   JSONL sink + ADR-0042's byte-identity check could be wired
   into a published benchmark: "N runs, byte-identical N times."
   The transformer comparison number would speak for itself.
4. **Audit tour video / asciinema recording.**  The tour is built
   to be terminal-recorded with no edits; producing a 90-second
   asciinema cast is purely operational, not architectural.
5. **`core demo audit-tour --scene N`** — run a single scene at
   a time.  Useful when debugging or when only one claim needs
   live evidence.
