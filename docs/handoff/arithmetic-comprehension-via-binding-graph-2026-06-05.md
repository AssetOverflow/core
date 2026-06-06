# Brief: arithmetic word-problem comprehension via binding_graph (5th comprehension domain)

**Status:** ready to execute (scoped 2026-06-05). One focused PR.
**Why a brief, not a tail-of-context build:** this is the binding_graph's *first
comprehension consumer* — a load-bearing integration whose correctness hinges on
*real* equation admissibility. Per CLAUDE.md's schema-defined-proof-obligations,
stamping `admissibility_status="admitted"` without a real check is decoration, not
proof. It deserves fresh context.

## Goal

Add `comprehension_relational_metric`: read arithmetic word-problem **prose**
("Liam has 6 stickers. Mia has 4 more stickers than Liam. How many stickers does
Mia have?") into the binding_graph **quantity substrate**, then project to the
existing independent `relational_metric` oracle and score `wrong=0`. This is the
**user-chosen, doctrine-aligned** path: CLAUDE.md says the `MeaningGraph`
deliberately excludes quantities (`= binding-graph's domain`), so quantities live
in `binding_graph`, not in an extended MeaningGraph.

This makes the comprehension organ read a **5th independent oracle** (after
set-membership, syllogism-validity, total-ordering, propositional-entailment) and
gives `generate/binding_graph` its **first real consumer** (memory: it has had
zero consumers since ADR-0132).

## Reuse — no gold authoring needed

`evals/relational_metric/v1/cases.jsonl` already has **15 cases** with
`text` + `relations` + `query` + `gold`. Reuse it verbatim (like the other
comprehension lanes reuse the staged gold lanes). Do **not** author new gold.

## The independent oracle (the arbiter)

`evals/relational_metric/oracle.py::oracle_answer(relations, query) -> int`
(forward substitution; raises `OracleError` on unknown kind / forward ref /
duplicate / missing query entity). Supported `kind`s:

| kind | shape | prose |
|---|---|---|
| `fact` | `entity = value` | `X has N <unit>.` |
| `more_than` | `entity = ref + delta` | `Y has N more <unit> than X.` |
| `fewer_than` | `entity = ref - delta` | `Y has N fewer <unit> than X.` |
| `sum_of` | `entity = sum(parts)` | query `How many <unit> do X and Y have?` |

`query` is `{"entity": <id>, "unit": <unit>}`. Single-entity query prose:
`How many <unit> does Y have?` Sum query prose: `How many <unit> do X and Y have?`
(the gold encodes a `sum_of` relation with `entity:"total", parts:[...]` plus the
query `entity:"total"`). Numbers are **digits** (2–18 in the lane).

## Pipeline (mirrors the existing comprehension lanes)

```
prose
  -> comprehend_quantitative(text)          # NEW: numeric reader -> binding_graph
  -> SemanticSymbolicBindingGraph           # quantities live here (doctrine)
  -> to_relational_metric(graph)            # NEW projector -> (relations, query) dicts
  -> oracle_answer(relations, query) -> int # INDEPENDENT arbiter
  -> == gold ?                              # wrong must stay 0
```

Refusal-first throughout: any clause/number that does not parse, any shape beyond
the 4 kinds, REFUSES (counts as refused, never wrong). The oracle is the
independent verdict — the reader never grades itself.

## New reader capability: NUMBER parsing

The current `meaning_graph` reader only mints **identifier** atoms; numbers are not
identifiers. Add a numeric token handler (digits → `int`; spelled-out numbers
optional/out-of-scope — the lane is digits-only, so digits suffice; refuse
non-digit number words rather than guess). Templates (function-word + order):

- `<X> has <N> <unit>` → fact(X, N, unit)
- `<Y> has <N> more <unit> than <X>` → more_than(Y, ref=X, delta=N)
- `<Y> has <N> fewer <unit> than <X>` → fewer_than(Y, ref=X, delta=N)
- query `how many <unit> does <Y> have` → query(entity=Y, unit)
- query `how many <unit> do <X> and <Y> have` → sum_of(total, [X,Y]) + query(total)

Entity names are single-token in the lane (liam, mia, …) → reuse the existing
`_chunk`. Units are single tokens (stickers, cards, …).

## Quantity representation in binding_graph (the careful part)

Build a `SemanticSymbolicBindingGraph` (see `generate/binding_graph/model.py`):

- `SymbolBinding(symbol_id, name, semantic_role, source_span, introduced_by,
  entity, unit)` — `semantic_role ∈ {entity, quantity, rate, duration, count,
  total, difference, ratio, unknown}` (closed). Use `"count"`/`"quantity"` for the
  countable quantities, `"total"` for a sum result.
- `BoundFact(symbol_id, value, source_span, unit)` — `value` is a **string**
  (`"6"`); unit carried.
- `BoundEquation(lhs_symbol_id, rhs_canonical, dependencies, operation_kind,
  unit_proof, admissibility_status, source_span, refusal_reason)` for
  more_than/fewer_than/sum_of. `rhs_canonical` is a deterministic **string**
  (`"liam + 4"`, `"noah - 6"`, `"dan + eva"`) — binding_graph deliberately does NOT
  import `Polynomial`.

**PROOF OBLIGATION (do not stamp):** `admissibility_status` must come from the real
admissibility check, not a hardcoded `"admitted"`. Use
`generate/binding_graph/admissibility.py::check_admissibility` (referenced by
`adapter.py`); a same-unit additive equation should verify. A test must FAIL if the
status is forced wrong (mutate to `"refused"` → projection/scoring must change).

**`unit_proof` — OPEN, resolve first:** it is a required non-empty field. Read
`generate/binding_graph/units.py` to produce a valid **same-unit** proof for
additive equations (all operands share `<unit>`). Do not invent a format; use the
unit module's constructor/representation.

## Key design sub-decision (recommendation: direct construction)

`generate/binding_graph/adapter.py` builds a binding_graph from a
**`MathProblemGraph`** (the GSM8K math structure). Two options:

1. **Reuse the adapter** (`MathProblemGraph → binding_graph`) — but that couples the
   comprehension organ to the GSM8K `MathProblemGraph`.
2. **Construct `SemanticSymbolicBindingGraph` directly** from the parsed clauses
   using the model's public dataclasses + `check_admissibility`. **RECOMMENDED.**

Rationale for (2): keep the comprehension organ **disjoint** from the GSM8K serving
path, mirroring CLAUDE.md's sensorium-track rule ("disjoint from the GSM8K serving
path — no `generate.derivation` / `core.reliability_gate` import, so it cannot
regress the serving metric"). **Hard constraint: the new code must NOT import
`generate.derivation` or `core.reliability_gate`**, and must not touch the
serving-frozen lane SHAs. Verify with the lane-SHA gate after.

## Projection: binding_graph → relational_metric dicts

`to_relational_metric(graph) -> (relations: list[dict], query: dict) | None`:
- each `BoundFact` → `{"kind":"fact","entity":sym,"value":int(value)}`
- each additive `BoundEquation` → `{"kind":"more_than"/"fewer_than","entity":lhs,
  "ref":dep,"delta":int}` (recover delta/ref from `rhs_canonical` or carry them as
  structured fields on a small wrapper so the projector need not re-parse strings —
  prefer carrying structured operands through the reader to avoid string re-parse)
- sum equation → `{"kind":"sum_of","entity":lhs,"parts":[...]}`
- the `BoundUnknown` / query symbol → `{"entity":..., "unit":...}`
- return `None` (→ refusal) unless exactly one query and ≥1 fact.

> Note: carrying `delta`/`ref`/`parts` as structured data from the reader (rather
> than re-parsing `rhs_canonical`) keeps the projector trivial and avoids a
> string-parse wrong=0 hazard. The binding_graph remains the doctrinal quantity
> *record*; the structured operands are the reader's parse output.

## Wiring + tests (match the existing lanes exactly)

- `evals/comprehension/relational_metric_runner.py` — `run()` over
  `evals.relational_metric.runner._load_cases`, refusal-safe, returns counts.
- `evals/capability_index/adapters.py` — add
  `comprehension_relational_metric_result` to `ADAPTERS`.
- `evals/capability_index/baseline.json` — re-freeze (breadth **7 → 8**); new digest.
- `tests/test_comprehension_relational_metric.py` — end-to-end `wrong=0` + pinned
  counts.
- `tests/test_comprehension_reader.py` — numeric templates (fact/more/fewer/query).
- `tests/test_meaning_graph_projectors.py` — `to_relational_metric` shape + None.
- `tests/test_capability_index.py` — breadth 7→8 + domain set.
- `tests/test_comprehension_wrong_zero_property.py` — **generative round-trip**:
  random additive chains (single-token entities, digit deltas) → render prose →
  comprehend → binding_graph → project → `oracle_answer` vs direct oracle. Verify it
  **bites** (e.g. mutate `more_than`→`fewer_than` in the projector → wrong verdict
  caught). This is the anti-overfit guarantee.

## Validation gates (pre-push)

1. `relational_metric` gold-only runner unchanged (lane untouched).
2. `comprehension_relational_metric` `wrong=0`; report coverage honestly (some of
   the 15 may refuse — e.g. sum_of query phrasing — that is fine, refusal ≠ wrong).
3. `core test --suite smoke -q` green.
4. `scripts/verify_lane_shas.py` — `deductive_logic_v1` + all GSM8K lanes unchanged
   (the sole expected miss is the `public_demo` env wall-clock flake). Confirms no
   GSM8K-path coupling.
5. Capability index `wrong_total == 0`, breadth 8, re-frozen baseline.

## Risks / lookback (first binding_graph consumer)

- **Admissibility must be real** (proof obligation above) — the single biggest
  integrity risk; a stamped status is decoration.
- **No GSM8K coupling** — grep the new files for `generate.derivation`,
  `core.reliability_gate`, `MathProblemGraph` imports; direct construction avoids
  them.
- **`unit_proof` format** — resolve from `units.py` before writing the projector.
- **Number scope** — digits only; refuse spelled-out/ordinals rather than guess.
- **Geomean** — adding domain 8 changes the geomean by design; if coverage on the
  15 cases is partial, the geomean reflects honest partial coverage (do not tune
  prose to the reader — the lane is fixed independent gold).

## Expected outcome

Breadth 7 → 8; the comprehension organ reads arithmetic (a genuinely new reading
capability — numbers), `wrong=0`, with the binding_graph as the doctrinal quantity
substrate and its first real consumer wired and admissibility-checked.
