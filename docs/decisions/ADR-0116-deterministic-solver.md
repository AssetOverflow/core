# ADR-0116 — Deterministic Solver (`MathProblemGraph` → `SolutionTrace`)

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114, ADR-0114a, ADR-0115

---

## Context

ADR-0114 §Phase 2 specified a deterministic solver for the GSM8K-math
roadmap. ADR-0114a then bound that solver to discharge four of the
ten anti-overfitting proof obligations:

- Obligation #3 — every correct answer ships with a replay-equal trace
- Obligation #4 — typed refusal on under-determined inputs
- Obligation #9 — determinism across runs
- Obligation #10 — operation provenance via the pack (not hardcoded
  strings in solver code)

This ADR ships the solver, the `SolutionTrace` schema, and the
arithmetic pack that closes Obligation #10.

---

## Decision

### `SolutionTrace` schema (`generate/math_solver.py`)

Two frozen dataclasses:

```text
SolutionStep:
    step_index      int          — 0-based position in the trace
    operation_kind  str          — add / subtract / transfer / multiply / divide
    pack_lemma_id   str          — "<pack_id>:<lemma>", resolved at solve time
    actor           str          — entity the operation applies to
    operand         Quantity     — value + unit of the operation
    target          str | None   — destination entity (transfer only)
    before_value    float        — actor's quantity before this step
    after_value     float        — actor's quantity after this step
    target_before   float | None — target's quantity before (transfer only)
    target_after    float | None — target's quantity after (transfer only)

SolutionTrace:
    pack_id              str               — "en_arithmetic_v1"
    graph_canonical_hash str               — SHA-256 of graph.canonical_bytes()
    steps                tuple[Step, ...]  — ordered, source-order
    answer_value         float
    answer_unit          str
    answer_entity        str | None        — None for total-across queries
```

`SolutionTrace.canonical_bytes()` is sorted-keys / compact-separators
JSON. Two solves of the same graph produce byte-equal bytes.

### Operation provenance via `en_arithmetic_v1`

A new operator-vocabulary pack ships under
`language_packs/data/en_arithmetic_v1/`. Five entries, all `pos=VERB`:

| entry_id | lemma | semantic domain |
|---|---|---|
| en-arith-001 | add | arithmetic.operation.addition |
| en-arith-002 | subtract | arithmetic.operation.subtraction |
| en-arith-003 | multiply | arithmetic.operation.multiplication |
| en-arith-004 | divide | arithmetic.operation.division |
| en-arith-005 | transfer | arithmetic.operation.transfer |

`role: operational_base` (not a domain claim — no `eval_lanes`, no
domain contract). Manifest carries `provenance: adr-0116:operator_seed:2026-05-22`.

The solver loads this pack at every `solve()` call via
`language_packs.compiler.load_pack_entries`. Each operation kind in
the input graph is dispatched through the pack's lemma table; a
missing or unloadable pack raises `SolveError` immediately.

**This is the load-bearing pack-binding mechanism for ADR-0114a
Obligation #10.** Every `SolutionStep.pack_lemma_id` value carries
the form `"en_arithmetic_v1:<lemma>"` and resolves to a real
lexicon entry. Changing the pack (renaming a lemma, removing one,
swapping pack ids) changes which traces resolve — deterministically
and inspectably.

### Solve semantics

```text
solve(graph):
    1. Resolve every operation kind → pack-qualified lemma id.
       Failure here = SolveError.
    2. Initialize state from graph.initial_state.
    3. For each operation in source order, apply to state and emit
       one SolutionStep. before_value and after_value pin the local
       state transition for replay.
    4. Resolve graph.unknown:
         - entity is None → sum every state entry matching unit
         - else → look up (entity, unit); missing key = SolveError
    5. Return SolutionTrace.
```

The arithmetic is pure-Python `float`: associative-add, scalar
multiply, exact divide. No platform-specific kernels.

### Refusal conditions (typed)

Every `SolveError` names its reason:

- missing or incomplete arithmetic pack
- division by zero
- unknown references state that was never asserted or produced
- transfer operation missing its target (defensive; the graph
  constructor already rejects this, so this is belt-and-suspenders)

The solver never produces a fabricated answer. **This is the
load-bearing refusal discipline for ADR-0114a Obligation #4.**

---

## Invariants

### `adr_0116_solver_meets_phase_2_exit_criterion`

Solver correctness on the 50-case dev set is **≥ 0.80**. Current
measurement: **50/50 = 1.00**. Pinned by
`tests/test_math_solver.py::TestSolverExitCriterion`.

### `adr_0116_determinism`

Same graph → byte-equal `SolutionTrace.canonical_bytes()` across two
consecutive solves. Tested parametrized over all 50 dev cases.
Discharges ADR-0114a Obligation #9 for this layer.

### `adr_0116_trace_replay_reproduces_answer`

Re-applying `SolutionTrace.steps` to the initial state reproduces
`answer_value` byte-equal. Rehearsal for ADR-0117 verifier;
discharges ADR-0114a Obligation #3 at solver-layer fidelity.

### `adr_0116_typed_refusal_on_under_determined_graphs`

Division by zero, missing pack, and unknown-references-nothing all
raise `SolveError`. The solver never returns a value it cannot
defend. Discharges ADR-0114a Obligation #4 at solver-layer fidelity.

### `adr_0116_operation_provenance_via_pack`

Every `SolutionStep.pack_lemma_id` resolves to a real lexicon entry
in `en_arithmetic_v1`. Every operation kind in the solver's dispatch
table requires the pack to provide the corresponding lemma; missing
lemma is a fail-loud `SolveError`. **Discharges ADR-0114a
Obligation #10 in full.**

---

## ADR-0114a obligation discharge summary

| Obligation | Status under ADR-0116 |
|---|---|
| #1 Sealed-holdout discipline | Substrate present; per-lane enforcement deferred to ADR-0119 |
| #2 OOD surface variation | Not addressed by solver; deferred to ADR-0118a / future |
| #3 Replay-equal trace | **Discharged** (rehearsal-quality; ADR-0117 hardens) |
| #4 Typed refusal | **Discharged at solver layer** |
| #5 Reasoning-isolation perturbation suite | Not addressed; deferred to future ADR |
| #6 Compositional-depth curve | Not addressed; measurement-time only at promotion |
| #7 Frontier-baseline comparison | Not addressed; deferred to ADR-0119 |
| #8 Adversarial generation | Not addressed; deferred to ADR-0119 |
| #9 Determinism | **Discharged at solver layer** |
| #10 Operation provenance via pack | **Discharged in full** |

Four of ten obligations now have load-bearing implementations.

---

## Acceptance evidence

Accepted when:

- `generate/math_solver.py` exports `solve`, `SolutionTrace`,
  `SolutionStep`, `SolveError`, and `REQUIRED_PACK_ID`
- `language_packs/data/en_arithmetic_v1/` ships with manifest,
  lexicon (5 entries), and glosses; checksums verified
- `tests/test_math_solver.py` (109 cases) is green
- Smoke suite is green
- Solver hits 50/50 on the 50-case dev set
- `core capability ledger` continues to load (pack discovery is
  additive; no domain contract changes)
- ADR linked from `docs/decisions/README.md` index and frontier

---

## Consequences

- Phase 2 of the GSM8K-math roadmap lands. ADR-0117 (verifier) can
  consume `SolutionTrace` directly without re-implementing
  semantics.
- Four ADR-0114a obligations are now load-bearing in code, not
  promissory. Future expert-tier work can rely on them.
- The arithmetic operator vocabulary is now a first-class pack,
  inspectable by external readers (`cat language_packs/data/en_arithmetic_v1/lexicon.jsonl`).
- The "operations bind to concepts, not hardcoded strings"
  architectural claim is now true rather than rhetorical. Inspecting
  any `SolutionTrace` shows the path from English verb (via the
  parser's verb table) to operation kind (via the solver's dispatch)
  to pack-lemma id (via the arithmetic pack's lexicon). Removing the
  pack breaks every solve loudly.

---

## Out of scope

- Verifier (ADR-0117). Distinct concern; consumes the trace produced
  here.
- Stepped-realizer extension (ADR-0118). Produces show-your-work
  prose from the trace.
- GSM8K eval lane (ADR-0119). Lane scaffolding, holdout sealing,
  frontier comparison, adversarial generation, depth-curve
  publication.
- First `expert` promotion contract (ADR-0120). Sets numeric
  thresholds and invokes all 10 ADR-0114a obligations.
- Extending the arithmetic pack with more operators (modulo, power,
  etc.). Future amendment if the parser/solver scope widens.
- Multi-currency / unit-conversion arithmetic. Out of scope per
  ADR-0115 Phase 1.1 boundary.

---

## Open candidate directions (no ADR yet)

- **Solver-level cross-checks.** The current solver applies
  operations strictly in source order. A future variant could
  validate that the operation graph is well-typed (no negative
  intermediate quantities for "physical" units, etc.). Belongs to
  a domain-specific solver layer, not this base.
- **Step-level provenance to the parser's source span.** Each step
  could carry a `source_span` indicating which sentence + token
  range produced it. Useful for explainability surfaces; not
  load-bearing for any current obligation.
- **Trace compression.** `SolutionTrace.canonical_bytes()` grows
  linearly with operation count. For very long problems (50+ steps)
  the trace could be SHA-anchored and offloaded. Not a concern at
  GSM8K depths (typically 2-8 steps).
