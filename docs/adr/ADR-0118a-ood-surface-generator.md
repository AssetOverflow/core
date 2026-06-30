# ADR-0118a — OOD Surface Generator for GSM8K-Style Parser Dev

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114, ADR-0114a, ADR-0115, ADR-0116

---

## Context

ADR-0114a Obligation #2 requires a capability lane that scores `S` on
its public split to score at least `0.95 * S` on a programmatically
derived out-of-distribution split that holds the underlying graph
constant while varying surface form.

The current GSM8K-style parser development lane has 50 authored public
cases in `evals/gsm8k_parser_dev/cases.jsonl`. ADR-0115 fixes the
Phase 1.1 parser grammar and `MathProblemGraph` schema; ADR-0116 fixes
the deterministic solver. This ADR adds the missing OOD surface lane
without changing the parser, solver, graph schema, or public cases.

---

## Decision

### OOD variant generator

`generate/ood_surface_generator.py` exports:

```text
generate_ood_variants(problem, ground_truth_graph, *, seed, n=3)
```

and the frozen, slotted `OODVariant` record. The generator is pure and
deterministic: same `problem`, `ground_truth_graph`, `seed`, and `n`
produce byte-equal variant records.

The generator renders from `MathProblemGraph` rather than performing
free-form text edits. This keeps the surface inside ADR-0115 Phase 1.1:

- Title-cased one-word entities
- lowercase single-token plural units
- direct declarative possession and operation sentences
- one `How many ...` question
- parser-supported add/subtract/transfer/multiply/divide forms

The default `n=3` emits one variant in each transform class:

| Transform | Behavior |
|---|---|
| `rename_entities` | Replaces every entity with a fixed-registry OOD proper noun in order of introduction. |
| `rename_units` | Replaces every unit with a fixed-registry OOD lowercase plural noun, preserving singular/plural surface rendering. |
| `scale_numbers_by_k` | Multiplies initial quantities and add/subtract/transfer operands by `k in {2, 3, 5}`; multiply/divide scalar operands are unchanged. |

Every rendered variant uses OOD entity names and OOD units so the
surface does not overlap with public dev entity or unit strings. The
required fixed registries are shipped in the module. `Wren` remains in
the registry as specified, but is excluded from selection because it
appears in the public split; `nebulae` remains in the registry but is
not selected because the current parser's canonical plural rule would
map that surface to `nebulaes`.

### OOD scorer

`evals/gsm8k_parser_dev/ood_score.py` exposes:

```bash
python3 -m evals.gsm8k_parser_dev.ood_score
```

The scorer:

1. Loads the 50 public dev cases.
2. Scores public parser+solver correctness.
3. Generates three OOD variants per case with a deterministic seed
   derived from the case id.
4. Parses and solves every variant.
5. Prints per-variant pass/fail, per-transform ratios, public ratio,
   OOD ratio, and `ood/public`.
6. Exits `0` when `ood/public >= 0.95`, else exits `1`.

---

## Invariants

### `adr_0118a_generator_determinism`

Two calls with the same `problem`, `ground_truth_graph`, `seed`, and
`n` produce byte-equal serialized variants.

### `adr_0118a_unrename_preserves_original_graph`

Each variant carries `expected_graph_after_unrename` byte-equal to the
source `ground_truth_graph`. Entity and unit relabeling are reversible
and structure-preserving.

### `adr_0118a_live_parser_solver_accepts_variants`

Every generated variant is parsed and solved by the live ADR-0115 /
ADR-0116 contracts, and the solver answer matches the variant's
expected answer and unit.

### `adr_0118a_ood_public_ratio_gate`

Across the 50-case public dev set, OOD/public score ratio is at least
`0.95`.

### `adr_0118a_no_public_surface_overlap`

No generated variant uses an entity or unit string from the public dev
set.

### `adr_0118a_scale_is_linear`

For scale-by-`k` variants, `original_answer * k ==
variant.expected_answer`.

---

## ADR-0114a obligation discharge summary

This ADR closes ADR-0114a Obligation #2 for the GSM8K-style parser
development lane: public score `S` and programmatic OOD score are both
measured by the same parser+solver contract, and the OOD/public ratio
is pinned in acceptance evidence.

| Obligation | Status under ADR-0118a |
|---|---|
| #1 Sealed-holdout discipline | Substrate present; per-lane enforcement remains for later ADRs |
| #2 OOD surface variation | **Discharged** |
| #3 Replay-equal trace | Discharged by ADR-0116/0117 path, not changed here |
| #4 Typed refusal | Discharged by ADR-0115/0116 path, not changed here |
| #5 Reasoning-isolation perturbation suite | Remains for later ADRs |
| #6 Compositional-depth curve | Remains for later ADRs |
| #7 Frontier-baseline comparison | Remains for later ADRs |
| #8 Adversarial generation | Remains for later ADRs |
| #9 Determinism | Discharged at solver layer by ADR-0116; generator determinism added here |
| #10 Operation provenance via pack | Discharged by ADR-0116 |

#1, #5, #6, #7, and #8 remain for later ADRs.

---

## Acceptance evidence

Accepted when:

- `generate/ood_surface_generator.py` exports `generate_ood_variants`
  and `OODVariant`
- `evals/gsm8k_parser_dev/ood_score.py` runs as
  `python3 -m evals.gsm8k_parser_dev.ood_score`
- `tests/test_ood_surface_generator.py` is green
- Smoke suite is green
- The OOD scorer reports:
  - `rename_entities`: 50/50 = 1.0000
  - `rename_units`: 50/50 = 1.0000
  - `scale_numbers_by_k`: 50/50 = 1.0000
  - public: 50/50 = 1.0000
  - OOD: 150/150 = 1.0000
  - OOD/public: 1.0000
- ADR linked from `docs/decisions/README.md` index and frontier

---

## Consequences

- ADR-0114a Obligation #2 is now executable evidence rather than a
  promissory requirement.
- Parser/solver surface dependence is measured without extending the
  grammar, changing schemas, or modifying public cases.
- The future `expert` promotion ledger can cite an OOD/public ratio
  produced by a deterministic local command.
- The generator creates a reusable shape for later perturbation suites,
  but does not claim to discharge the broader ADR-0114a Obligation #5.

---

## Out of scope

- Independent-sentence reordering. ADR-0114a lists it as an OOD
  example, but this ADR implements the three requested transform
  classes only.
- Adversarial generation and misparse probing. Remains for ADR-0114a
  Obligation #8.
- Reasoning-isolation perturbations that intentionally change answers
  beyond linear scaling. Remains for ADR-0114a Obligation #5.
- Any parser, solver, graph schema, or dev-case expansion.
- LLMs, sampling, stochastic generation, or approximate scoring.
