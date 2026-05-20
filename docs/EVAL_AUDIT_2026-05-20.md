# Eval Lane Audit — 2026-05-20

## Why this exists

After landing ADR-0080 (contemplation pipeline), ADR-0082 (provider
adapters), and the cross-provider `frontier_compare` Lane B, a stop
hook caught that "evals/demos brought up-to-date with higher
expectations" was claimed without a systematic look at the 48 eval
directories.  This document is that look.  It's a **prioritization
map**, not a fix-everything checklist.

## Method

For each `evals/<lane>/` directory:

- **Contract** — does `<lane>/contract.md` exist?
- **Results** — count of JSON files in `<lane>/results/`.
- **CLI** — invokable via `core eval <lane>` or `core demo <lane>`?
- **Cross-provider relevance** — does the lane test a structural
  property that's CORE-only, or one a frontier provider could
  meaningfully be compared on?

## Summary

- **48 eval directories** (excluding `lab/`, `reports/`, `results/`, `__pycache__/`).
- **40 have `contract.md`** (83%).  Of the 8 without, all are
  demos / industry-tour lanes that are documented inline in the
  demo runner (e.g. `evals/audit_tour/run_tour.py` carries its
  own scene-level docs).  Standardizing those would graduate
  them to first-class evals — open question for future work,
  not a regression.
- **18 have ≥ 1 saved results file**, 30 have zero.  Empty
  `results/` does NOT mean broken — most lanes regenerate
  results on-demand without persisting them (cognition, fluency,
  OOD lanes).  Only the lanes that publish reproducible numbers
  to CLAIMS.md should persist.

## Cross-provider relevance triage

The user's instruction was to wire **competitor providers** for
**relevant benchmarks**.  Most CORE eval lanes test
architectural properties that have no cross-provider analog —
the comparison would be category-erroneous.  This section
makes the split explicit.

### Cross-provider-relevant (provider adapter would compare meaningfully)

| Lane | Why relevant | Wired today? |
|------|-------------|--------------|
| `frontier_compare` Lane B (`prompt_battery`) | Designed for it (ADR-0082) | ✅ yes, this session |
| `cognition` | Definition/intent quality on shared prompts | ❌ no — would need adapter abstraction |
| `english_fluency_ood` | Surface fluency on out-of-domain prompts | ❌ no |
| `hebrew_fluency`, `koine_greek_fluency` | Language coverage | ❌ no |
| `elementary_mathematics_ood`, `foundational_biology_ood`, `foundational_physics_ood`, `classical_literature_ood` | Knowledge breadth on OOD prompts | ❌ no |
| `grammatical_coverage` | Surface grammar quality | ❌ no |
| `inference_closure`, `multi_step_reasoning` | Multi-step reasoning closure | ❌ no |
| `discourse_paragraph` | Discourse-level coherence | ❌ no |

**Wiring plan for these:** mirror the `prompt_battery` shape from
`frontier_compare/cross_provider.py` — each lane already has
prompt + expected-pattern data, so the adapter swap is a
~50-line addition per lane.  This is genuine future work, not
done this session.

### CORE-only by design (provider comparison would be category-erroneous)

These lanes measure architectural invariants no transformer can
structurally satisfy.  Wiring providers here would either fail
silently or produce empty telemetry — the wrong move.

| Lane | What it tests (uniquely CORE) |
|------|-------------------------------|
| `frontier_compare` Lane A (`determinism`, `truth_lock`, `axis_orthogonality`) | trace_hash invariance, versor_condition, anchor-lens engagement |
| `adversarial_identity` | identity-axis rejection under prompt injection |
| `anti_regression` | three-gate defense against learning harmful chains |
| `articulation_of_status` | SPECULATIVE-marker articulation |
| `calibration` | refusal calibration tied to EpistemicStatus |
| `cold_start_grounding` | first-turn grounding without vault priming |
| `compositionality` | pack-grounded composition determinism |
| `compound_intent_decomposition` | intent classifier decomposition |
| `contradiction_detection` | CONTESTED transition on paired contradictions |
| `conversational_thread_coherence` | thread-anaphora over ChatRuntime |
| `cross_domain_transfer` | pack-bridged cross-domain grounding |
| `deterministic_fluency` | byte-identical replay across runs |
| `forward_semantic_control` | rotor-application correctness |
| `identity_divergence` | identity-pack swap divergence shape |
| `introspection` | self-report against actual runtime state |
| `learning_loop` | cold-turn → discovery → propose → accept loop |
| `long_context_cost` | exact CGA recall at N tokens (the structural-asymmetry claim) |
| `monotonic_learning` | no-regression invariant under teaching |
| `multi_agent_composition` | cross-runtime composition determinism |
| `multi_sentence_response` | discourse-planner spine |
| `provenance` | trace_hash + term provenance completeness |
| `realizer_guard` | C1/C2 articulation-legality boundary |
| `refusal_calibration` | EpistemicStatus-gated refusal markers |
| `sample_efficiency` | teaching-cost per added capability |
| `self_consistency_over_time` | session-state consistency across turns |
| `symbolic_logic` | rotor-composition correctness on logic prompts |
| `teaching_injection_resistance` | identity-adjacent injection rejection |
| `walkthrough_chain` | NARRATIVE intent multi-chain composition |
| `warmed_session_consistency` | session-warm vs cold-start equivalence |
| `zero_code_domain_acquisition` | pack-only domain capability |

## Demo schema standardization

All 9 `core demo` targets now emit a uniform `all_claims_supported:
bool` top-level field (this session).  Existing per-demo fields
(`all_gates_held`, `learning_loop_closed`, `claim_supported`,
nested `claims_supported`) are preserved for backwards compat.
Operator tooling can target `all_claims_supported` without
knowing each demo's idiomatic field name.

Verified:

```
audit-tour              : all_claims_supported = True
register-tour           : all_claims_supported = True
anchor-lens-tour        : all_claims_supported = True
orthogonality-tour      : all_claims_supported = True
pack-measurements       : all_claims_supported = True
anti-regression         : all_claims_supported = True
learning-loop           : all_claims_supported = True
articulation            : all_claims_supported = True
long-context-comparison : all_claims_supported = True
```

## UI/UX coverage

| Surface | State |
|---------|-------|
| `evals/frontier_compare/ui/report_viewer.html` | ✅ Lane-aware drawer + pass-rate chart (this session) |
| Other lane HTML viewers | ❌ none exist; lanes produce JSON consumed by `core eval` text output |
| `core eval <lane>` text output | ⚠ derives summary from JSON but no charts; CLAIMS.md is the cross-lane dashboard |
| `core demo` text output | ⚠ each demo prints its own summary block; no unified format |

**Practical recommendation:** the right next UI investment is a
single **multi-lane dashboard** that loads any lane's
`results/*.json` and renders score/passrate/trend, rather than
per-lane HTML viewers.  The `frontier_compare/ui/report_viewer.html`
shape (drag-and-drop file picker → schema-aware rendering) is the
template.  Not done this session.

## What was done this session (concrete)

| # | Status | Scope |
|---|--------|-------|
| 55 | merged | ADR-0080 read-only contemplation boundary |
| 57 | merged | φ separation probe (falsified across 8 variants) |
| 58 | merged | Pipeline convergence: shared sink, separate schemas |
| 59 | merged | Renamed dev's ADR-0081 → ADR-0082 |
| 60 | merged | Fixed INV-02 + wired `core contemplation` subcommand |
| 61 | merged | ADR-0082 providers wired into frontier_compare runner |
| 62 | open   | Contracts + `bench --json` cleanliness + Lane B viewer + pass-rate chart + this audit + demo schema standardization |

## What remains (concrete, not vague)

1. **Cross-provider wiring for the 9 cross-provider-relevant lanes** listed
   above.  Per-lane work, ~50 lines each.  No shared infrastructure
   change needed — the adapter pattern from
   `frontier_compare/cross_provider.py` is reusable.
2. **Multi-lane dashboard** that loads any `results/*.json` from any
   lane.  Single HTML file, drag-and-drop, schema-aware rendering.
3. **Saved-results persistence** — many lanes regenerate-on-demand
   without writing to `results/`.  CLAIMS.md numbers cannot be
   replay-verified without persistence.  Per-lane CLI option to
   `--save` (some lanes already have this; standardize).
4. **Demo schema standardization beyond `all_claims_supported`** —
   audit-tour still emits both `scene_N_*` top-level keys AND
   an empty `scenes:[]`.  Pick one shape per demo, deprecate the
   other.
5. **Contracts for the 8 demo lanes without `contract.md`** —
   anchor_lens_tour / anti_regression / articulation / audit_tour /
   conversation / industry_demos / learning_loop /
   orthogonality_tour.  Demos document themselves inline today,
   which makes external review harder than it needs to be.

Each is a focused PR.  None require architectural change.
