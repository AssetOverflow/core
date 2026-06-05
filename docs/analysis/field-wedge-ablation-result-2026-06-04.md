<!-- CANONICAL | docs/analysis/field-wedge-ablation-result-2026-06-04.md | 2026-06-04 | research/experimental-result | the field-reasoner wedge ablation verdict: the field reads correctly (wrong=0) but adds no independent signal over a symbolic reader on the metric-trivial micro-domain — C3 | verified: ablation run committed; field_wrong=[], field_caught_symbolic_errors=[] -->

# The field-reasoner wedge ablation — result: C3 (decoration on this domain)

This records the outcome of the falsifiable experiment designed in
[`field-reasoner-wedge-design-and-falsification-2026-06-04.md`](./field-reasoner-wedge-design-and-falsification-2026-06-04.md).
The verdict is the dossier's sanctioned negative: **the field reads correctly but is
decoration here.** That is a success — it answers the field-as-reasoner question with
evidence instead of deferring it.

## What was measured

Two readings of the same forward-substitutable quantitative-relational micro-domain
(additive / part-whole), scored against an independent arithmetic oracle:

- **Field reader** (`generate/relational_field_reader.py`) — reads TEXT into conformal
  points on the e1 number line; additive relations are conformal translator versors;
  the answer reads back by projective dehomogenization. (The geometric SUT.)
- **Symbolic reader** (`generate/relational_symbolic_reader.py`) — a competent,
  code-disjoint reading by plain integer arithmetic; no `algebra` (INV-27 disjoint).

The ablation (`evals/relational_metric/ablation.py`) runs both through the real
`verify_tier2_agreement` gate and asks the only questions that matter.

## Result

| Measurement | Value | Meaning |
|---|---|---|
| **field_wrong_commits** | `[]` | wrong=0 holds — the field never commits a bad integer (the per-step drift guard refuses instead). |
| **field_caught_symbolic_errors** | `[]` | The field caught **zero** comprehension errors the symbolic reader made. (Measurement #2 = fail.) |
| **field_lost_coverage** | `[rm-v1-0015]` | The only admitted-set change is the field **refusing a correct answer** at the precision ceiling — a liability, not signal. |
| **per-class diversity** | `0` everywhere | On every committable class the readers AGREE and are BOTH CORRECT: `disagree=0`, `double_fault=0`. (Measurement #3 = no diversity.) |
| **verdict** | **`C3`** | The field is decoration / a coverage liability on this domain. |

## Why — the load-bearing insight

**On forward-substitutable relations, geometric translation *is* arithmetic addition.**
`versor_apply(T_δ, embed[x]) = embed[x+δ]` is exactly `x + δ`. There is no metric
over-determination — no betweenness, incidence, or continuous-constraint structure —
for the field to exploit that a competent symbolic reader lacks. So the two readings are
**redundant** (the common-mode the dossier predicted via Knight–Leveson), and agreement
adds no independent soundness signal. The field's *one* genuine marginal check
(over-determination coherence) is matched by the symbolic reader's `over_determined_conflict`
refusal, so even there it is not unique. And the field's precision ceiling makes it a
strict coverage liability versus pure integer arithmetic.

This is the deductive-logic finding's twin: there, logic was *combinatorial* not metric,
so the field could not earn it; here, the metric domain is *arithmetically trivial*, so
the geometry adds nothing. **The field earns a reasoning role only where geometry
genuinely exceeds the symbolic alternative — not yet demonstrated on any built domain.**

## What this changes

- **Field-as-reasoner is NOT earned.** No field vote enters any serving or capability
  path. The field stays a servant (its existing cognition-turn role). No "the field
  reasons" claim is made.
- **The capability path is symbolic (C3).** The symbolic reader is correct (15/15 here,
  including the case the field refuses). Shipping quantitative capability safely is the
  dossier's Phase 3+ on the symbolic path — **two** code-disjoint symbolic readings
  agreeing + independent/sealed gold (one reader alone is the resolve_pooled risk). Not
  built here; this slice answered the experiment, it did not ship serving.
- **The `t2_precision` lever stays dormant** for this domain — there is no genuine second
  derivation to feed it (field⟂symbol is common-mode here).

## What stays (all load-bearing, none reverted)

- The **f64 conformal foundation** (Phase 0A) — net infrastructure hardening.
- The **reader-lineage firewall + INV-27** (Phase 0B/0C) — backs any future agreement gate.
- The **field reader + relational-metric lane** — a real wrong=0 demonstration that the
  field *can* read (Phase W.1), and a valid 3rd independently-golded panel domain.
- The **symbolic reader + ablation instrument** — the C3 reader and a reusable decoration
  test for the next domain.

## The honest next bet (dedicated research, not the near-term sequence)

Field-as-reasoner remains an open question for a domain where geometry genuinely beats
arithmetic: **continuous / over-determined / multi-constraint** structure (relative
position, betweenness, incidence among many points, ratio as cross-ratio on a
non-degenerate frame) — where a symbolic step-arithmetic reader and a field constraint
reading could genuinely diverge, and agreement would be a real second derivation. Until
such a domain is built and the ablation shows `field_caught_symbolic_errors > 0`, the
field stays a servant. Two negative domains (logic: combinatorial; additive: trivial)
now bound the search: the field needs *metric-nontrivial, arithmetically-hard* structure.
