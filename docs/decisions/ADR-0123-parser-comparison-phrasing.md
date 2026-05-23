# ADR-0123 — Comparison-Phrasing Realizer (surface increment on the ADR-0123 substrate)

**Status:** Accepted (surface increment; substrate landed in PR #155)
**Date:** 2026-05-23
**Author:** CORE agents + reviewers
**Depends on:**
- ADR-0115 (parser substrate),
- ADR-0116 (deterministic solver),
- ADR-0117 (`SolutionTrace` verifier),
- ADR-0118 (stepped realizer),
- ADR-0119 (+ all 8 sub-phases),
- ADR-0121 (math `expert` promotion deferred),
- the ADR-0123 **substrate commit** (`feat/adr-0123-substrate`, commit
  `c9bd5d4`): `Comparison` dataclass + `compare_additive` /
  `compare_multiplicative` operation kinds + parser patterns +
  solver / verifier wiring + `en_arithmetic_v1:compare_additive`
  (en-arith-006) + `en_arithmetic_v1:compare_multiplicative`
  (en-arith-007) pack lemmas.
**Supersedes:** none

> Disambiguation: this is **ADR-0123-parser-comparison-phrasing**, the
> parser-arc ADR. It is distinct from
> `ADR-0123-symbolic-logic-shape-remap.md` (the lane-shape governance
> ADR that happens to share the number). The disambiguation pattern
> follows the same convention as the audit-passed / parser-rate split
> (e.g., `ADR-0122-systems-software-audit-passed-deferred.md` vs the
> parser-rate work pinned in a parallel PR). Two ADRs with the same
> number, distinct slugs, distinct subject-matter streams.

---

## Context

ADR-0121 deferred the first `expert` promotion with named blocker
`correct_rate = 0/1319` on sealed GSM8K. ADR-0121 §"What would
unlock the promotion" enumerates a parser-expansion arc of 4–8
construction classes. **Comparison phrasing** is the second class
in that arc (the first was rate / per-unit, currently in flight as
a parallel parser-rate ADR; the two are non-blocking siblings).

PR #155 (`feat/adr-0123-substrate`, commit `c9bd5d4`) shipped the
*substrate* — the typed graph operand (`Comparison`), the two new
operation kinds (`compare_additive`, `compare_multiplicative`),
the parser patterns for the four canonical English surfaces
(`N more / N fewer / twice / N times / half`), the solver
handlers, the verifier replay-equality extensions, and the two
pack lemmas. What the substrate did *not* ship — by deliberate
scope discipline mirroring ADR-0119's sub-phase decomposition — is
the **surface realization** of comparison steps in
`generate/math_realizer.py`. Without realizer phrasing, a problem
that solves successfully under the new operation kinds still
raises `RealizerError("unknown operation_kind 'compare_additive'")`
when the stepped explanation is requested.

This ADR closes that one-line architectural gap: the surface
sentence templates for the four comparison shapes, wired into
`_step_sentence` so the full
`parse_problem → solve → verify → realize` pipeline operates on
comparison problems end-to-end.

---

## Decision

Extend `generate/math_realizer.py` with **two helper functions**
(`_compare_additive_sentence`, `_compare_multiplicative_sentence`)
plus a **dispatch branch** in `_step_sentence` that consumes the
new operation kinds. The signature of `_step_sentence` widens by
one optional parameter (`entity_units`) carrying a
`{entity_name: unit}` mapping derived once-per-trace from
`graph_initial_state` in `realize()`. This is the load-bearing
plumbing change: the multiplicative comparison helper needs the
reference actor's unit at render time, and the substrate
deliberately does not carry that on `Comparison` itself when
`factor` is set (the substrate's solver derives it from
in-flight state, which the realizer cannot reach without
re-running the solver).

### Realizer-level additions (`generate/math_realizer.py`)

1. **`_compare_additive_sentence(step: SolutionStep) -> str`** —
   renders an additive-comparison step as one of two templates,
   selected by `step.operand.direction`:

   ```
   direction='more':
     "<actor> has <delta.value> more <delta.unit> than <ref>,
      giving <actor> a total of <after> <delta.unit>."

   direction='fewer':
     "<actor> has <delta.value> fewer <delta.unit> than <ref>,
      leaving <actor> with a total of <after> <delta.unit>."
   ```

   The two-clause shape — *comparison clause* + *resolved-state
   clause* — is pinned as a structural invariant. `delta.value`
   and `after_value` pluralize independently via the existing
   `_unit_surface` helper, so "1 more apple" and the resolved
   state "3 apples" coexist without forcing one count's
   plurality onto the other.

2. **`_compare_multiplicative_sentence(step: SolutionStep,
   entity_units: dict[str, str]) -> str`** — renders a
   multiplicative comparison step as one of three templates,
   selected by `step.operand.direction` and `factor`:

   ```
   direction='times':
     "<actor> has <factor> times as many <unit> as <ref>,
      giving <actor> a total of <after> <unit>."

   direction='fraction' (factor == 0.5):
     "<actor> has half as many <unit> as <ref>,
      giving <actor> a total of <after> <unit>."

   direction='fraction' (other factor):
     "<actor> has <factor> as many <unit> as <ref>,
      giving <actor> a total of <after> <unit>."
   ```

   `unit` is resolved via `entity_units[reference_actor]` — the
   initial-state lookup is sufficient because the substrate's
   solver refuses multi-unit reference actors (`SolveError("…is
   ambiguous: reference actor … holds quantities in multiple
   units…")`) and refuses to overwrite a comparison actor's
   existing state. Both refusals guarantee that the reference's
   initial unit and the comparison-time unit are the same string.

3. **`_step_sentence` dispatch widened** with two prepended
   branches:

   ```python
   if step.operation_kind == "compare_additive":
       return _compare_additive_sentence(step)
   if step.operation_kind == "compare_multiplicative":
       if entity_units is None:
           raise RealizerError(...)
       return _compare_multiplicative_sentence(step, entity_units)
   ```

   The pre-existing `add` / `subtract` / `transfer` / `multiply`
   / `divide` branches are unchanged, byte-identically. The new
   branches sit at the top because the substrate's solver already
   refuses ambiguous comparisons; the realizer's job is to
   *render* what survived solver refusal, not to re-validate.

4. **`realize()` builds `entity_units` once** from
   `graph_initial_state`:

   ```python
   entity_units = {p.entity: p.quantity.unit for p in graph_initial_state}
   ```

   and threads it through to every `_step_sentence` call. The
   add/subtract/transfer/multiply/divide branches accept the
   parameter and ignore it (default `None`), preserving the
   existing behavior on pre-comparison traces.

### Refusal discipline (load-bearing)

The helpers raise `RealizerError` on every shape the substrate
already refuses *plus* one shape the substrate cannot see:

| Refusal | Substrate or Realizer |
|---|---|
| operand not a `Comparison` | realizer (defensive — substrate guarantees this via `Operation.__post_init__`) |
| `delta is None` in additive branch (multiplicative shape leaked) | realizer |
| `factor is None` in multiplicative branch (additive shape leaked) | realizer |
| `direction not in {'more','fewer'}` for additive | realizer |
| `direction not in {'times','fraction'}` for multiplicative | realizer |
| `actor == reference_actor` (self-comparison) | both (substrate at parse time; realizer at render time as defense in depth) |
| `reference_actor` not in `entity_units` | realizer (multiplicative only — substrate guarantees this for parsed problems but does not for hand-constructed graphs) |

ADR-0114a Obligation #4 (`wrong == 0`) holds by construction —
the new branches only fire when the substrate has already
emitted a successful step; if the substrate refused, no step
exists to render.

### What this ADR does NOT touch

- `generate/math_problem_graph.py` — `Comparison` is already
  shipped by the substrate; not modified.
- `generate/math_parser.py` — `_try_comparison_declaration` is
  already shipped by the substrate; not modified.
- `generate/math_solver.py` — `_apply_compare_additive` /
  `_apply_compare_multiplicative` are already shipped; not
  modified.
- `generate/math_verifier.py` — comparison-step verification is
  already shipped; not modified.
- `language_packs/data/en_arithmetic_v1/*` — `en-arith-006`
  (compare_additive) and `en-arith-007` (compare_multiplicative)
  are already shipped at manifest version 1.1.0; this ADR adds
  no further pack vocabulary.

The scope discipline matches ADR-0119's sub-phase decomposition
exactly: substrate ships first (PR #155), surface ships second
(this PR), each with its own re-measurable invariants.

---

## Anti-overfit re-measurement (load-bearing — per ADR-0121)

This ADR ships **only** when every measurement below holds.

### 1. Sealed-GSM8K correct_rate + wrong count

Run `evals/gsm8k_math/runner.py` against the decrypted sealed
holdout (1319 cases). **Pass condition**: `wrong == 0` (the
absolute discipline). The `correct_rate > 0.0` lift gate is
**deferred** — the substrate ADR pre-measured zero sealed lift
(every comparison-matching sealed case also requires aggregation
/ rate / conditional structure not yet in the parser), and the
realizer surface cannot create matches the parser refuses.

### 2. ADR-0118a OOD re-measurement

Run the OOD perturbation suite (`evals/gsm8k_parser_dev/ood_score.py`).
**Pass condition**: OOD/public ratio remains ≥ 0.95. Adding two
realizer branches and threading one extra parameter must not move
this number.

### 3. ADR-0125 perturbation re-measurement

Run the invariance perturbation suite. **Pass condition**:
invariance-preserving rate = 1.0; invariance-breaking rate = 1.0.

### 4. ADR-0119.5 adversarial re-measurement

Run `evals/gsm8k_math/adversarial/`. **Pass condition**:
`wrong == 0` across all 38 cases × 12 families.

### 5. ADR-0119.7 sealed-seal integrity

The sealed holdout `cases.jsonl.age` file is **not modified**.
SHA-256 digest unchanged.

### 6. ADR-0117 replay-equality

Runner remains deterministic — same case set → byte-equal
`LaneReport.canonical_bytes()`. The realizer change extends to
new step kinds but does not modify the existing kinds'
rendering, so prior traces re-render byte-identically.

### 7. Substrate measurement preservation

Every invariant the substrate ADR pinned (parser, solver,
verifier, pack-binding) continues to hold byte-identically. The
substrate's test suite re-runs cleanly under this PR.

### 8. ADR-0118 stepped-realizer preservation

The pre-existing add/subtract/transfer/multiply/divide step
sentences re-render byte-identically. ADR-0118's pinning of
those templates is not weakened.

---

## Invariants

### `adr_0123_realize_compare_additive_more_canonical`

`parse_problem("Alice has 5 apples. Bob has 3 more apples than
Alice. How many apples does Bob have?") → solve() → realize()`
produces prose containing **all** of:
- `"3 more apples than Alice"`
- `"Bob a total of 8 apples"`
- the final `"Bob has 8 apples."` answer sentence.

### `adr_0123_realize_compare_additive_fewer_canonical`

`"Anna has 10 flowers. Mary has 5 fewer flowers than Anna. How
many flowers does Mary have?"` → prose containing:
- `"5 fewer flowers than Anna"`
- `"Mary with a total of 5 flowers"`

### `adr_0123_realize_compare_multiplicative_twice_canonical`

`"Carla has 7 marbles. Ben has twice as many marbles as Carla.
How many marbles does Ben have?"` → prose containing:
- `"2 times as many marbles as Carla"`
- `"Ben a total of 14 marbles"`

### `adr_0123_realize_compare_multiplicative_n_times_canonical`

`"Tom has 3 cookies. Sara has 4 times as many cookies as Tom.
How many cookies does Sara have?"` → prose containing:
- `"4 times as many cookies as Tom"`
- `"Sara a total of 12 cookies"`

### `adr_0123_realize_compare_fraction_half_canonical`

`"Tom has 8 cookies. Lisa has half as many cookies as Tom. How
many cookies does Lisa have?"` → prose containing:
- `"half as many cookies as Tom"` (the literal word "half", not
  "0.5 as many")
- `"Lisa a total of 4 cookies"`

### `adr_0123_realize_byte_deterministic`

Two `realize()` calls on the same `(graph_initial_state, trace)`
produce byte-equal `RealizedTrace.canonical_bytes()`. Pinned for
both additive and multiplicative cases.

### `adr_0123_realize_singular_plural_independence`

A `compare_additive` step with `delta.value=1` and `after_value=5`
renders `"1 more apple"` (singular delta clause) and
`"5 apples"` (plural resolved state). Symmetric: `delta.value=3`
and `after_value=1` renders `"3 more apples"` and
`"1 apple"`.

### `adr_0123_realize_refuses_non_comparison_operand`

A hand-constructed `SolutionStep` with `operation_kind="compare_additive"`
but `operand=Quantity(...)` raises `RealizerError("requires a
Comparison operand")`.

### `adr_0123_realize_refuses_missing_delta`

A `Comparison(direction='more', delta=None, factor=2.0)`
operand on a `compare_additive` step raises `RealizerError`
matching `/requires Comparison.delta/`.

### `adr_0123_realize_refuses_missing_factor`

A `Comparison(direction='times', delta=Quantity(3,'a'),
factor=None)` operand on a `compare_multiplicative` step raises
`RealizerError` matching `/requires Comparison.factor/`.

### `adr_0123_realize_refuses_missing_entity_units`

`_compare_multiplicative_sentence(step, entity_units={})` for a
reference actor not in the map raises `RealizerError` matching
`/initial state/`. This catches hand-constructed graph traces
that omit the reference actor from initial state.

### `adr_0123_realize_pre_comparison_traces_byte_identical`

A trace containing only add/subtract/transfer/multiply/divide
steps renders **byte-identically** to its pre-this-PR rendering
on the substrate branch. The realizer change does not modify
the prior templates.

### `adr_0123_sealed_correct_rate_zero_at_landing`

`run_lane(sealed_cases).metrics["correct_rate"] == 0.0` at the
time of landing. Inherits the substrate ADR's deferral mechanic:
the multi-construction barrier (every sealed comparison-matching
case combines with at least one other class not yet in the
parser) holds at the surface layer too — comparison alone
matches zero sealed cases. The test fails (correctly) only when
a future composition ADR finally lifts the number above 0.

### `adr_0123_sealed_wrong_zero_holds`

`run_lane(sealed_cases).metrics["wrong"] == 0`. Inherits the
substrate's wrong-zero discipline. The realizer cannot create
new misparses; it only renders successful traces.

### `adr_0123_adr_0118_stepped_realizer_unchanged`

ADR-0118's canonical realization tests pin the
add/subtract/transfer surfaces. They continue to pass
byte-identically.

---

## Measurement (at landing)

| Metric | Pre-ADR (substrate tip) | Post-ADR (this branch) | Gate | Pass? |
|---|---|---|---|---|
| `parse_problem → solve → realize` on 4 canonical comparison shapes | refuses at realize() with `unknown operation_kind` | **all four render** (more, fewer, twice/N times, half) | end-to-end pipeline | ✓ |
| sealed `correct_rate` | 0.0 (0/1319) | **0.0 (0/1319)** | deferred (see Decision) | ✓ (deferred) |
| sealed `wrong` | 0 | **0** | must remain 0 | ✓ |
| public `correct_rate` | 1.0 (150/150) | unchanged | ≥ 0.95 | ✓ |
| OOD/public ratio | 1.00 | unchanged | ≥ 0.95 | ✓ |
| perturbation invariance-preserving | 1.0 | unchanged | 1.0 | ✓ |
| perturbation invariance-breaking | 1.0 | unchanged | 1.0 | ✓ |
| adversarial `wrong` | 0 | **0** | 0 | ✓ |
| sealed seal SHA-256 | (pinned by ADR-0119.7) | unchanged | byte-equal | ✓ |
| ADR-0118 stepped-realizer canonical surfaces | pinned templates | unchanged | byte-equal | ✓ |

**Honest finding:** the realizer surface closes the last
architectural gap in the comparison-phrasing class. A problem
that the substrate's solver evaluates successfully now produces
show-your-work prose — without this ADR, every successful
comparison solve raises `RealizerError` at the explanation
step. The lift gate stays at zero because the parser only
recognizes the four canonical comparison surfaces in isolation,
not in composition with rate / aggregation / unit conversion
(the multi-construction barrier the substrate ADR documented).

---

## Out of scope

- **Composed rate × comparison constructions** ("A watermelon
  costs three times what each pepper costs") — composition ADR.
- **Comparative ratio phrasing beyond half** (`"X has 2/3 as
  many as Y"`, `"X has 75% of Y"`) — percentage / fraction ADR
  (the third foundational class).
- **Multi-step comparison chains** ("A has 3 more than B; B has
  twice as many as C") — composition ADR.
- **Comparative superlatives** ("X has the most apples", "Y has
  more than anyone else") — out of arc.
- **Negative-direction additive with non-positive delta** —
  refused by substrate at construction time; realizer inherits.
- **Round-trip equality between realized prose and re-parsed
  graph** — deferred to a future ADR. The current realizer
  surfaces are *human-readable*; they are not yet a strict
  fixed point of the parse → realize → parse → realize loop.
  ADR-0118 holds this distinction for its own operation kinds;
  ADR-0123 inherits it.

---

## What this proves (and what it doesn't)

### Proves

- The full `parse_problem → solve → verify → realize` pipeline
  now operates end-to-end on the four canonical comparison
  surfaces (`N more`, `N fewer`, `twice`/`N times`, `half`).
  Before this ADR, the pipeline crashed at the last step.
- The wrong-zero discipline (ADR-0114a Obligation #4) holds
  against an expanded grammar surface. Adding two realizer
  branches did not introduce a single new misparse on any of
  the existing eval lanes.
- ADR-0118's pinned templates re-render byte-identically. The
  realizer change is purely additive at the dispatch layer.

### Does NOT prove

- That comparison problems will eventually lift sealed
  `correct_rate`. They won't, in isolation — the multi-
  construction barrier documented in the substrate ADR and
  inherited here is the load-bearing reason. The cumulative
  lift signal arrives after the 3rd or 4th foundational class
  composes.
- That the chosen prose templates are the *best* templates
  for downstream consumers. They are deterministic, structurally
  invariant, and human-readable. If a future composition ADR
  finds them ambiguous (e.g., the parser misparses its own
  realizer output during round-trip), the templates get revised
  at that point.
- That the `fraction` direction with non-`0.5` factors is
  well-tested. The substrate parser only emits `factor=0.5` for
  `fraction`; the realizer's fall-through template
  (`"<factor> as many ..."`) exists for future
  parser extensions but is not exercised by any parsed problem
  today.

---

## Consequences

- The realizer covers all six operation kinds the substrate
  emits (add/subtract/transfer/multiply/divide/compare_*).
  ADR-0114a Obligation #5 (realizer coverage parity) holds
  across the full graph vocabulary.
- ADR-0121's deferral remains in place — surface-layer ADRs
  cannot move the sealed `correct_rate` gate because they only
  render what the parser+solver already produce.
- Substrate measurements continue to hold byte-identically.
  The realizer change is fully additive at the dispatch layer.
- The parser-expansion arc gains its second class **fully
  end-to-end** (substrate + surface). Per ADR-0121's revised
  sequencing, no lift signal is expected until at least the
  3rd or 4th class lands. The next ADR is percentage /
  fraction.
- The substrate-then-surface decomposition pattern (PR #155 →
  this PR) is reusable for future parser-expansion classes.
  Substrate ADRs ship the typed graph operand + parser/solver/
  verifier wiring; surface ADRs ship the realizer phrasing.
  Each measures independently.

---

## Why this ADR is small on purpose

ADR-0114a's honest-fitting discipline rewards narrow expansions
that each get fully re-measured across all anti-overfit lanes.
The substrate ADR shipped 4,798 lines of new code (parser
patterns + solver handlers + verifier extensions + pack lemmas
+ tests for adjacent ADRs that were caught in the same merge);
this ADR ships ~140 lines of realizer code and one ADR doc.

The substrate-then-surface split exists for two reasons:

1. **Independent bisection.** If a regression appears on OOD or
   perturbation, the bisection points at one of: (a) the
   substrate's parser/solver changes, or (b) this PR's
   realizer phrasing. Bundling them into one PR loses the
   bisection signal.
2. **Independent reviewability.** A reviewer who knows the
   parser/solver subsystem need not also be a realizer expert,
   and vice versa. Each PR has a tractable diff for a single
   reviewer to load into working memory.

This is the same load-bearing rule as ADR-0119's sub-phase
decomposition and the substrate ADR's own scope discipline,
applied one level finer.
