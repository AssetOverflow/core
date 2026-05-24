# ADR-0139 — Arithmetic-as-Versor Spike: `add` Only

**Status:** Draft
**Date:** 2026-05-24
**Author:** CORE agents
**Parent / supersedes context:** [ADR-0114a](./ADR-0114a-math-capability-substrate.md),
[ADR-0115](./ADR-0115-math-problem-parser-and-graph.md),
[ADR-0116](./ADR-0116-deterministic-solver.md)
**Engine target:** CGA cognitive engine (`algebra/versor.py`, `algebra/cga.py`,
`core/cognition/pipeline.py`)

---

## Context

CLAUDE.md commits the project to a single deterministic cognitive engine:

```text
listen → comprehend → recall → think → articulate → learn → replay
```

built on CGA Cl(4,1) versor algebra, exact recall, PropositionGraph,
ArticulationTarget, deterministic realizer, and trace-hash invariance.

Between ADR-0114a and the present, a second engine grew alongside the first:

| | Engine A (CGA cognitive engine) | Engine B (math pipeline) |
|---|---|---|
| Substrate | versor multivectors in Cl(4,1) | frozen Python dataclasses |
| Graph | `PropositionGraph` (from `graph_planner.py`) | `MathProblemGraph` (from `math_problem_graph.py`) |
| State propagation | `versor_apply(V, F)` — sandwich product | pure-Python arithmetic in `math_solver.py` |
| Closure invariant | `versor_condition(F) < 1e-6` | `assert`s on dataclass fields |
| Trace contract | `core/cognition/trace.py` | `SolutionTrace.canonical_bytes()` |
| Used by | `chat/runtime.py`, cognition eval | `evals/gsm8k_math/runner.py` |

Engine B was always intentional scaffolding — `math_solver.py:24` states
*"the 'expert' tier (ADR-0120) is not in scope here; ADR-0116 is the Phase 2
substrate the eventual capability claim will rest on."*

The GSM8K corridor (ADR-0123 / 0131 / 0136 / 0138) has been extending the
parser side of Engine B without ever testing the lift to Engine A. Every PR
through that corridor reports `cognition eval byte-identical` — the symptom
that Engine A is not being invoked by math work, even though math is the
nominal capability claim the engine should eventually demonstrate.

This ADR begins the lift. It does not finish it. It does not even cover one
GSM8K case end-to-end through Engine A. It does one thing: prove that one
arithmetic operation can be represented as a closed versor in Cl(4,1)
without weakening any existing invariant.

---

## Decision

Run a one-operation algebraic spike: **`add` only**, **algebra only**, **no
graph or pipeline wiring**.

### Embedding choice

A `Quantity(value: int|float, unit: str)` is embedded as a single conformal
point on the e1 axis:

```text
embed_quantity(value, unit) = embed_point([value, 0, 0])
```

Existing primitive: `algebra/cga.py:embed_point`.

This choice:

- Places quantities on the CGA null cone (`cga_inner(X, X) ≈ 0`).
- Uses only the existing CGA point-embedding primitive — no new algebra
  invented in this ADR.
- Treats the `unit` field as carried metadata, not as a multivector
  coordinate. Unit handling is propositional, not algebraic.
- Lets the standard CGA translator versor represent additive operations.

Open question (deferred): whether multi-unit problems require multiple axes
(e1 for unit A, e2 for unit B) or whether each unit gets its own embedding
context. ADR-0139 covers single-unit `add` only and does not commit either
way.

### Operation choice

`add(addend: int|float) → versor` is constructed as the standard CGA translator
along e1 by `addend`:

```text
T_a = 1 - 0.5 * a * e1 * n_inf
```

(exact sign/normalization to be derived against the existing `cga.py` /
`cl41.py` conventions during implementation; the construction must produce a
unit versor satisfying `versor_condition(T_a) < 1e-6` at runtime.)

This is well-known CGA — translators are the canonical versor representation
of Euclidean translations. Adding `b` to a quantity is geometrically
translating its point on e1 by `b`.

### Application

```text
result = versor_apply(T_addend, embed_quantity(value, unit))
```

`versor_apply` already has the correct dual-path behavior for this
embedding: null inputs (CGA points) get the raw sandwich path
(`algebra/versor.py:160-162`) so the null property is preserved through
the operation. No change to `versor_apply` is required.

### Decoding

A `decode_quantity(F, unit) → (value, unit)` extracts the e1 coordinate of
the result point. This is the inverse of `embed_point` restricted to the
e1 axis.

---

## Acceptance

A single test module — `tests/test_arithmetic_as_versor_add.py` — passes
with these assertions on a small fixed set of `(a, b)` pairs covering
integer, fractional, negative, and zero cases:

1. **Embedding well-formedness.** For each input `value`:
   - `cga_inner(embed_quantity(value, "u"), embed_quantity(value, "u")) ≈ 0`
     (null cone preserved).

2. **Translator well-formedness.** For each addend `b`:
   - `versor_condition(translator(b)) < 1e-6`.

3. **Closure.** For each `(a, b)`:
   - Let `R = versor_apply(translator(b), embed_quantity(a, "u"))`.
   - `cga_inner(R, R) ≈ 0` (result remains on null cone).

4. **Arithmetic correctness.** For each `(a, b)`:
   - `decode_quantity(R, "u") == (a + b, "u")` byte-equal at the tolerance
     chosen by the embedding (decimal value match within `1e-9` for the
     fixed-point test cases listed below).

5. **Replay determinism.** Running the test twice produces byte-identical
   multivector arrays (no nondeterministic float ordering, no platform
   drift).

6. **Composability (in-ADR scope).** `versor_apply(translator(c),
   versor_apply(translator(b), embed_quantity(a, "u")))` decodes to
   `(a + b + c, "u")` — proves two consecutive translations compose
   correctly. This is the smallest two-step program the engine path
   could run.

### Fixed test cases

```text
(0, 0), (0, 1), (1, 0),
(3, 4), (7, -3),
(0.25, 0.75), (1.5, 2.5),
(-5, 5), (-2, -3),
(100, 1), (1, 100),
```

Plus the composability case `(2, 3, 5) → 10`.

---

## Non-goals

Explicit out-of-scope for this ADR:

- No `subtract`, `multiply`, `divide`, `transfer`, `apply_rate`,
  `compare_additive`, `compare_multiplicative` operations. Each gets its
  own follow-on ADR once `add` is proven.
- No `MathProblemGraph` consumer. The new functions take typed inputs
  directly. They do not import from `math_problem_graph.py`.
- No `PropositionGraph` construction. Engine A's graph layer is not
  touched.
- No `CognitiveTurnPipeline` integration. The pipeline file is not
  imported.
- No `chat/runtime.py` invocation path. The chat surface is not touched.
- No GSM8K case routed through this code. The runner is not modified.
- No deprecation of Engine B. `math_solver.py`, `math_verifier.py`,
  `math_realizer.py`, and the S.x corridor parsers remain in place,
  unmodified, scoring GSM8K as they do today. The 3/50 admission set is
  preserved.
- No pack changes. `en_arithmetic_v1` is not touched. Pack-binding for the
  versor path is a separate concern.

The ADR succeeds if `add` works algebraically. It does not claim that
the math pipeline has been lifted. It only proves the lift is feasible
for one operation.

---

## Rationale

Two design choices are load-bearing and should be defended explicitly:

**Why a spike instead of a phased plan?**

The arithmetic-as-versor algebra is the single load-bearing unknown for
the entire lift program. Every follow-on ADR — subtract, multiply,
compare, graph integration, pipeline integration, GSM8K routing —
assumes that arithmetic can be represented as closed versors at the
required tolerance. If `add` doesn't work cleanly, every downstream ADR
is built on sand. The spike forces that assumption to be tested in code,
not in design documents.

**Why `add` instead of `multiply` or `compare`?**

Translators are the most canonical CGA versor. The construction
`T_t = 1 - 0.5 * t * n_inf` is textbook. If anything in the CGA
substrate is going to behave well, translators will.

Multiplication is dilation in CGA — also a known versor, but it requires
the `n_o ∧ n_inf` blade and exponentiation. Riskier first step.

Comparisons (`compare_additive`, `compare_multiplicative`) are relational
predicates, not transformations. They may not be versor-shaped at all —
they might land at the proposition layer instead. Trying to make them
versor-shaped first would entangle two unknowns.

So `add` is the smallest, cleanest, most-textbook starting point.

**Why no graph or pipeline wiring?**

Engine A's graph and pipeline layers already exist and work. The risk
isn't whether `versor_apply` integrates with `graph_from_intent` — that's
plumbing. The risk is whether arithmetic can be represented as versors
at all. Wiring before the algebra is proven would create the appearance
of progress without removing the load-bearing unknown.

---

## Open questions for follow-on ADRs

The following must be answered, but not by this ADR:

1. **Multi-axis embedding.** Does a two-unit problem (`5 apples + 3
   oranges` style — even though that's not valid arithmetic, mixed-unit
   intermediate states do appear in word problems) need orthogonal axes
   (e1 for apples, e2 for oranges)? Or does each unit context get its
   own embedding session?

2. **Multiplication as dilation.** The dilator
   `D_s = cosh(α/2) + sinh(α/2)·(n_o ∧ n_inf)` where `s = exp(α)`
   represents scaling. Does it close at `versor_condition < 1e-6` for
   the value ranges GSM8K actually requires? At what precision?

3. **Comparison as proposition vs versor.** Is `compare_additive("more
   by 5", x)` a versor operation, a proposition node, or both? Strongest
   guess: proposition. But this needs an ADR.

4. **`Rate` as bivector.** A `Rate(2.0, "dollars", "apple")` is
   inherently two-axis. It is probably a grade-2 object connecting two
   Euclidean axes. Does the existing CGA substrate support this cleanly?

5. **PropositionGraph construction from MathProblemGraph.** Once `add`
   and `subtract` are proven as versors, an ADR is needed that
   constructs a `PropositionGraph` from a `MathProblemGraph` so the
   engine pipeline can articulate the answer through the existing
   realizer.

6. **Trace-hash story.** Engine A's `compute_trace_hash` and Engine B's
   `SolutionTrace.canonical_bytes()` need to converge. Probably the
   versor sequence becomes the trace, with the existing hash function
   applied. Defer to the integration ADR.

7. **Refusal floor.** The versor path must preserve `wrong == 0`. When
   the algebra cannot represent a needed operation, the engine must
   refuse, not approximate. Mechanism TBD by the integration ADR.

---

## Risks

- **The translator construction may not close at `1e-6`.** The
  construction-residue tolerance in `algebra/versor.py:13` is `1e-2` and
  the runtime closure tolerance is `1e-6`. If `translator(b)` lands
  between those, `_close_applied_versor` will project it through
  `_seed_to_rotor`, which may not preserve the exact translation. The
  spike must verify this empirically; if it fails, the embedding or the
  construction has to be reconsidered before the ADR can ship.

- **Float32 truncation.** `algebra/cl41.py` uses float32 for
  multivectors. Large additions (e.g. `100 + 1`) may not decode back to
  exactly `101.0` after the sandwich. The test cases above include
  values that probe this. If float32 doesn't carry the required
  precision, the embedding may need to use the float64 path that
  `algebra/versor.py:18` already defines for runtime fields.

- **Decoding may not be exact for arbitrary float values.** The e1
  component of an embedded point is the raw value, but the e4/e5
  coefficients carry `0.5 * (value^2 ± 1)`. Round-tripping requires the
  e1 coordinate alone — the e4/e5 components are dependent. If the
  sandwich introduces error in e1 vs e4/e5 differently, decoding from
  e1 alone may not equal the input. This is the most likely failure
  mode and the spike's primary falsification target.

- **The user-facing capability gauge does not move in this ADR.** GSM8K
  admissions stay at 3/50. The cognition eval stays byte-identical. The
  only signal this ADR produces is a test file that does or does not
  pass. That is intentional but easy to misread as "no progress."

---

## Replay & invariants

The spike is governed by the same invariants as the rest of CORE:

- `versor_condition(F) < 1e-6` for all unit versors constructed
  (translators in this ADR).
- Null inputs to `versor_apply` stay null. Verified by `cga_inner(R, R)
  ≈ 0` on every result.
- No normalization is introduced outside the allowed sites
  (`ingest/gate.py`, `language_packs/compiler.py`,
  `algebra/versor.py`). The new functions live in a new module —
  proposed path `generate/math_versor_arithmetic.py` — and call only
  existing primitives. They do not add any new normalization.
- Determinism: float64 path used end-to-end where precision matters;
  no platform-conditional code; no randomness.

---

## Work sequencing for follow-on

Only if this ADR's tests pass:

1. ADR-0140: `subtract` as inverse translator. (Trivial follow-on; should
   pass nearly for free.)
2. ADR-0141: `multiply` as dilator. (Risk concentrates here.)
3. ADR-0142: `Rate` as bivector and `apply_rate` as combined
   translator-dilator. (Open question 4.)
4. ADR-0143: `compare_*` at the proposition layer, not versor layer.
   (Open question 3.)
5. ADR-0144: `PropositionGraph` from `MathProblemGraph`. (Open
   question 5.)
6. ADR-0145: One GSM8K case (gsm8k-0014) routed end-to-end through
   Engine A. First moment the capability gauge is honestly attached to
   the engine.

If this ADR's tests fail, the lift program is paused and the failure
mode is documented. Engine B continues serving GSM8K. A revised
embedding strategy is required before any follow-on ADR.

---

## Decision summary

Add one new module (`generate/math_versor_arithmetic.py` — name
provisional) with three functions: `embed_quantity`, `translator`,
`decode_quantity`. Add one test module verifying `add` works as a closed
versor at the required tolerance. Change nothing else. Ship as a single
PR small enough to audit in one sitting.

Acceptance is binary: every test in the new module passes, or the ADR is
withdrawn and the lift program is paused pending a new embedding choice.
