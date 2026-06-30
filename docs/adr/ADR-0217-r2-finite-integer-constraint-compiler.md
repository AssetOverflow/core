# ADR-0217 — R2: Finite-Integer Linear-Constraint Setup Compiler (off-serving)

> **Renumbered 2026-06-08:** originally landed as ADR-0211, which collided with
> ADR-0211 (Conformal Falsification Bench, 2026-06-06). The conformal ADR is the
> incumbent (earlier, test-pinned, depended on by ADR-0216); this R2 ADR moves to
> the next free number 0217. The ratified decision content is unchanged.

**Status:** Accepted (ratified 2026-06-07)
**Date:** 2026-06-07
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Current execution state:** IR (C1) + setup oracle / gold (C2) landed with this ADR;
the integer solver (C3), answer-choice verifier (C4), and reader (C5–C9) execute against
the gates below. R1 stays frozen at 7/0/3 (ADR-0207 surface untouched).
**Builds on (does not replace):** ADR-0207 (GSM8K substrate), ADR-0175 (calibrated
learning), ADR-0083 (transitive chain — the one executing R1 reasoning primitive).

---

## 1. The shift this ratifies

R1 grew one reader template per problem shape (`more_than`, `times_as_many`, `half`,
partition, aggregate-query, inverse). That ladder is now **closed** (R1 = 7/0/3; see
`docs/analysis/r1-inventory-ledger-2026-06-07.md`) and the per-shape path does not
generalize to harder problems. R2 changes the unit of work from

```text
one problem shape  ->  one reader patch
```

to a **small algebra of reusable setup primitives**:

```text
problem text -> entities -> quantities -> relations -> CONSTRAINTS -> goal -> solver -> verifier
```

A new problem family is admitted only when it can be expressed as **known primitive
composition + setup oracle + answer verifier + refusal tests** — never as a bespoke matcher.
This is the same discipline ADR-0207 ratified for the comprehension substrate, extended one
level up to constraint *systems*.

> If anyone proposes a "new GSM8K reader" or a per-shape matcher for two-category constraint
> problems after this ADR, it is redundant with this document. Redirect here.

## 2. Scope — R2 v1

**In:** a single **two-category, finite-integer linear system** of exactly two equations:

```text
x + y = N            (total count)
a·x + b·y = T        (weighted total)
x, y ∈ nonnegative integers
```

covering buses/seats, chickens/legs, tickets/prices, coins/values, boxes/items,
vehicles/wheels — anything that reduces to this shape. The deliverable is a **verified
setup first**, then an exact integer solve, then answer-choice verification.

**Deferred to R3 (explicitly NOT in this batch):** ≥3 categories, inequalities, multi-step /
mixed constraints, distractor exclusion, rates / unit conversion, and the **typed
contemplation loop + reviewed-failure learning** (the plan's Phases 6–7). When the
failure-learning half is built it routes through the existing `teaching/*` proposal-only
flywheel (ADR-0055/0056/0057) — it MUST NOT become a parallel correction path (CLAUDE.md).

## 3. The IR — `generate/constraint_comprehension`

Strings are serialization only; meaning lives in typed, frozen, slotted dataclasses (the R2
twin of `generate.quantitative_expr`):

- `expr.py` — `LinearExpr(terms: ((symbol, coeff), …), constant)`, `LinearConstraint(lhs,
  relation="eq", rhs, source_span?)`. Integers only; no floats representable.
- `model.py` — `Unknown(symbol, entity, unit, domain)` with `domain ∈ {nonnegative_integer,
  integer}`; `AttributeFact(category, measured_unit, value)` (per-category coefficient
  provenance); `ConstraintQuery(symbol, unit)`; `ConstraintProblem(unknowns, facts,
  constraints, query)`.

The query is a dedicated `ConstraintQuery`, **not** R1's `BoundUnknown` — R2 has no
state-index / question-form axis, and forcing R1's type would be a degenerate fit.

## 4. The ruler — `evals/constraint_oracle` (independent)

The setup oracle grades a comprehended `ConstraintProblem` against independent gold by a
**span-free canonical signature** (`signature.py`): unknowns `(symbol, unit, domain)`,
attribute coefficients, the canonical linear system (terms merged + sorted, the lhs constant
folded into the rhs, source spans stripped), and the query. Two setups are equal iff every
component matches; a mismatch localizes the diverging axis. This is the R2 twin of
`evals.setup_oracle.signature`, and — like it — imports **no** `generate.derivation` /
`core.reliability_gate` (§6).

The gold (`r2_gold.jsonl`, 13 fixtures) carries a **closed `expect` taxonomy**:

| `expect` | meaning | gold | graded by |
|---|---|---|---|
| `solved` | well-formed setup; integer answer; `options[answer] == gold` | int | reader (C5–C9) + solver (C3) + answer-choice (C4) |
| `solver_refuses` | well-formed setup, but no nonnegative-integer answer | none | solver (C3) |
| `reader_refuses` | incomplete/ambiguous prose the reader must not assemble | none | reader (C5–C9) |

Closed refusal sets (grow only by ratified extension, each with its fixture):

- `solver_reason ∈ {indistinguishable_weights, non_integer_solution, negative_solution,
  verification_failed}`
- `reader_reason ∈ {missing_total_count, missing_weighted_total, too_many_categories}`
  (C6/C8 may add coefficient-level reasons — equal coefficients, unit mismatch — each
  ratified with a fixture).

C2 ships a **gold-validation lane** only (no reader yet): every fixture deserializes into the
IR, canonicalizes deterministically, has a closed taxonomy, and — for `solved` — a coherent
answer key. `python -m evals.constraint_oracle` exits 0 iff `invalid == 0` (currently 13/13).

## 5. The wrong=0 contract

R2 carries the same invariant as the rest of the engine: **never emit a wrong answer; refuse
instead.** It is enforced at four independent gates, each wired to fail loudly:

1. **Setup oracle** — any drift in unknowns/units/constraints/query vs gold ⇒ `setup_wrong`
   (the reader must refuse an unsupported shape, never misread it as a simpler one).
2. **Reader** — incomplete or ambiguous prose (missing a constraint, >2 categories) ⇒ a typed
   refusal at assembly time, never a fabricated constraint.
3. **Solver (C3)** — exact integer arithmetic only: `indistinguishable_weights` (equal
   coefficients), `non_integer_solution` (`numer % denom ≠ 0` — never rounds),
   `negative_solution`, and a final `verification_failed` re-substitution check. No floats,
   no nearest-option snapping.
4. **Answer-choice verifier (C4)** — exactly one option may match the proven value;
   `0`/`>1` matches refuse; a provided key that disagrees with the proven value is **flagged
   as a contradiction**, not silently accepted (truth discipline: "the math says A; the key
   says C — the key is wrong").

### Schema-proof obligations (per CLAUDE.md)

Each gate above is real only because a test fails under the violation it catches: the C2
validator has per-branch meaningful-fail tests (incoherent answer key, three categories,
constraint referencing an unknown symbol, refusal carrying a gold, unknown reason/expect);
C3/C4 ship the same for their refusals. A gate without such a test is decoration, not proof.

## 6. Off-serving disjointness

`generate/constraint_comprehension` and `evals/constraint_oracle` import **no**
`generate.derivation` and **no** `core.reliability_gate` — the GSM8K serving path. R2 is a
parallel organ graded by its own independent oracle, so it **cannot regress** the sealed
serving metric (`train_sample`) or any pinned lane SHA. Consequently the per-commit gate is
`pytest` on the R2 files + the R1/15-case regression, **not** the pinned-SHA lane; the SHA
gate runs once at PR-submission to confirm zero serving drift.

## 7. Build ladder

| Commit | Adds | Local gate |
|---|---|---|
| C1 | constraint IR (`expr`, `model`) | IR tests |
| C2 | gold + signature + validation runner + **this ADR** | `constraint_oracle` 13/13 valid |
| C3 | two-variable integer solver + refusal tests | buses→4, chickens→11; refusals fire |
| C4 | answer-choice parse + verify (contradiction flag) | computed-vs-key contradiction test |
| C5–C9 | reader: category-pair → coefficients → total-count → weighted-total → query-target | setup_wrong stays 0; supported fixtures flip |

After C9: R2 setup nonzero-correct / **0 wrong** / rest refused; answers likewise; answer-key
contradictions flagged; serving unchanged. (Plan Phases 6–7 are a later batch — §2.)

## 8. What this reuses, and does not reinvent

- **ADR-0207** — R2 is the constraint-systems layer *above* the comprehension substrate, off
  the serving path; it does not touch `generate.derivation`.
- **ADR-0175** — a new capability family is admitted only with gold + oracle + refusal tests;
  R2 adds no per-shape matcher and no serving bridge.
- **ADR-0083** — the R1 transitive chain is the one executing R1 reasoning primitive; R2 adds
  *linear-system solving* as a new, independently-verified primitive (the C3 solver).
- **`evals.setup_oracle` pattern** — R2 mirrors the R1 ruler (signature + gold + runner)
  rather than inventing a new scoring mechanism.
- **ADR-0055/0056/0057** — the future failure-learning half (R3) routes through the existing
  proposal-only teaching flywheel; no parallel correction path.

## 9. Decision

Build R2 v1 as the off-serving finite-integer constraint setup compiler on the C1–C9 ladder.
The contract is pinned by the gold and this ADR; capability grows only where the gold +
oracle + refusal tests already license it. No guessed math, no silent correction, no answer
without a proven setup.

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
