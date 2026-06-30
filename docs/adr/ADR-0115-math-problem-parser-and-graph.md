# ADR-0115 — Math Problem Parser and Typed Proposition Graph

**Status:** Phase 1.1 Accepted (schema + 5 seed cases + tests); Phases 1.2–1.4 In Progress
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114

---

## Context

ADR-0114 laid out the path toward an actual `expert` ledger tier. Phase 1
of that arc is a deterministic parser that turns a grade-school math word
problem into a typed proposition graph the solver (ADR-0116) and verifier
(ADR-0117) will consume.

This ADR is decomposed into four sub-phases so each lands as its own
auditable step:

- **Phase 1.1** — Define the typed graph schema, author seed cases,
  pin invariants. (**This commit.**)
- **Phase 1.2** — Author the full 50-case curated dev set against the
  Phase 1.1 schema. (Delegated to Codex; tracked in PR follow-up.)
- **Phase 1.3** — Implement the deterministic parser. Exit criterion:
  ≥ 0.90 parse correctness against the 50-case dev set.
- **Phase 1.4** — Bind the parser to the existing CORE intent/realizer
  surface so a math word problem becomes a first-class runtime input.

Decomposing the phase keeps the schema (1.1) load-bearing for the
parser (1.3) without coupling their cadence to each other.

---

## Decision

### Phase 1.1 — what landed here

1. `generate/math_problem_graph.py` defines the schema:

   - `Quantity(value, unit)` — frozen dataclass.
   - `InitialPossession(entity, quantity)` — frozen dataclass.
   - `Operation(actor, kind, operand, target?)` — frozen dataclass.
     `kind ∈ {add, subtract, transfer, multiply, divide}`. `target`
     required when `kind=transfer` and must differ from `actor`.
   - `Unknown(entity?, unit)` — frozen dataclass; `entity=None` means
     "total across every entity holding `unit`".
   - `MathProblemGraph(entities, initial_state, operations, unknown)` —
     order-of-introduction tuples; validates referential integrity at
     construction (every reference to an entity must resolve).
   - `graph_from_dict(d)` and `MathProblemGraph.canonical_bytes()` close
     the JSON round-trip. Two logically-equal graphs produce byte-equal
     canonical serializations (sorted keys, compact separators).

2. `evals/gsm8k_parser_dev/cases.jsonl` carries the **first five seed
   cases** (`gpd-001` … `gpd-005`):

   | id | construction | answer |
   |---|---|---|
   | gpd-001 | single-entity / single-add | 8 apples |
   | gpd-002 | single-entity / single-subtract | 8 candies |
   | gpd-003 | single-entity / multi-step (add then subtract) | 12 books |
   | gpd-004 | two-entity transfer | 5 marbles |
   | gpd-005 | multi-entity sum (no operations) | 11 stickers |

3. `evals/gsm8k_parser_dev/README.md` is the **authoring contract**:
   pattern registry, canonicalization rules, scope boundary for Phase
   1.1, hand-solving rubric, distribution target for the remaining 45
   cases.

4. `tests/test_math_problem_graph.py` pins five invariants:

   - Each seed case round-trips through `graph_from_dict → as_json` byte-equal.
   - `canonical_bytes()` is deterministic across two identical constructions.
   - Constructor refuses every malformed graph case listed in the schema.
   - Hand-solving each ground-truth graph reproduces the case's
     `expected_answer` — catches mis-authored cases.
   - Case ids are sequential `gpd-NNN`.

### Phase 1.1 scope boundary (documented for Phase 1.2 authors)

The Phase 1.1 schema covers grade-school arithmetic constructions
expressible as a state-mutation event log. The dev-set README enumerates
exactly which patterns are in scope. **Out of scope for Phase 1.1**:

- Conditional / time-modal phrasing ("If Sam had ...").
- Rate-and-quantity inference ("Each apple costs $2, Sam buys 4").
- Compound questions / multiple unknowns per case.
- Generic-plural / implicit entities ("There are 5 boys").
- Comparative phrasing without explicit numbers ("twice as many as").

These are not architectural limits; they are Phase 1.1 cadence limits.
Phase 1.2+ may lift them under their own ADRs.

### Phase 1.2 — authoring contract (delegated)

The remaining 45 dev-set cases (`gpd-006` … `gpd-050`) are authored by
following `evals/gsm8k_parser_dev/README.md` against the Phase 1.1
schema. Distribution target documented there:

- 30 single-entity cases (`gpd-001` … `gpd-030`)
- 12 two-entity transfer cases (`gpd-031` … `gpd-042`)
- 8 multi-entity sum / no-op cases (`gpd-043` … `gpd-050`)

Verification: every authored case must (a) pass
`tests/test_math_problem_graph.py::TestSeedCasesRoundTrip`, (b) pass
`TestGroundTruthGraphsAgreeWithExpectedAnswers` (the hand-solver
reproduces `expected_answer`), and (c) tag only patterns from the
registered list.

### Phase 1.3 — parser exit criterion

The parser landing under Phase 1.3 produces `MathProblemGraph` instances
from natural-language input deterministically (no LLM, no sampling).
**Exit criterion**: for ≥ 45 of 50 dev-set cases,

```python
parser(case["problem"]).canonical_bytes() == graph_from_dict(case["ground_truth_graph"]).canonical_bytes()
```

i.e. ≥ 0.90 parse-correctness measured by byte-equality of the canonical
graph serialization. A failing case is reported with the diff between
parser output and ground truth.

### Phase 1.4 — runtime binding

Once Phase 1.3 lands, the parser is wired through the existing CORE
intent classifier so `RuntimeConfig.math_parser_enabled=True` routes
math-shaped intents through it. Out of scope for this ADR; will be its
own ADR if non-trivial.

---

## Invariants pinned now

### `adr_0115_schema_round_trip_byte_equal`

For every case in `evals/gsm8k_parser_dev/cases.jsonl`,
`graph_from_dict → as_json → graph_from_dict` produces byte-equal
`canonical_bytes()`. Tested by `TestSeedCasesRoundTrip`.

### `adr_0115_schema_validates_construction`

`MathProblemGraph` rejects graphs with: empty entities, duplicate
entities, references to undefined entities, transfers without a target,
non-transfer operations carrying a target, transfer-to-self. Tested by
`TestSchemaRejectsMalformed`.

### `adr_0115_ground_truth_graphs_match_expected_answers`

Hand-solving every seed case's `ground_truth_graph` reproduces its
declared `expected_answer`. This invariant is what makes the dev set
usable as a parser test bed: a wrong ground-truth would silently grade
the parser against itself. Tested by
`TestGroundTruthGraphsAgreeWithExpectedAnswers`.

---

## Acceptance evidence (for Phase 1.1)

- `generate/math_problem_graph.py` exports the typed dataclasses,
  `VALID_OPERATION_KINDS`, `MathGraphError`, and `graph_from_dict`
- `evals/gsm8k_parser_dev/cases.jsonl` contains 5 seed cases with the
  documented `gpd-NNN` id pattern
- `evals/gsm8k_parser_dev/README.md` documents the schema, pattern
  registry, scope boundary, and authoring contract
- `tests/test_math_problem_graph.py` is 26/26 green and pins the five
  invariants above
- README + `docs/decisions/README.md` link this ADR

---

## Consequences

- Phase 1 of ADR-0114 now has a concrete shape. Subsequent phase ADRs
  (0116 solver, 0117 verifier, etc.) consume this graph type.
- The schema is **load-bearing for the dev-set authoring contract**.
  Once `gpd-050` lands, changing the schema requires an amendment ADR
  plus rewriting cases — so the schema choices here should be sticky.
- The solver (ADR-0116) gets a clean input contract. It must implement
  exactly the semantics documented in this ADR's pattern registry
  (transfer = subtract+add, multiply/divide on actor's quantity,
  unknown-entity=null means sum-across).
- The hand-solver inside the test module is a **reference**
  implementation. ADR-0116 supersedes it with a real solver that can
  handle multi-step graphs with shared state across operations and
  produce a step-trace for the realizer (ADR-0118).

---

## Out of scope

- The parser itself. Phase 1.3, separate ADR (or this ADR's extension).
- Anything beyond the documented patterns. Phase 1.1 chooses sticky
  boundaries deliberately.
- GSM8K corpus integration. Phase 5 (ADR-0119).
- Defining the `expert` ledger tier predicates. Phase 6 (ADR-0120).
- A rate / per-unit pricing pattern. Future Phase 1.X amendment.
- Comparative-without-explicit-numbers phrasing. Future.

---

## Open candidate directions (no ADR yet)

- **Fractional / decimal answers.** Phase 1.1 keeps `Quantity.value` typed
  as `int | float` but every seed case is integer-valued. If a future
  pattern needs fractional intermediate state (e.g. "splits evenly into
  3"), the schema already supports it; what changes is the canonical
  comparison rule for the parser exit criterion (currently exact
  equality).
- **Multi-currency normalization.** Currently all "$" surfaces are
  normalized to `unit="dollars"`. Other currencies would need their own
  canonical unit string.
- **Time / duration.** Out of scope for Phase 1; will need its own
  arithmetic (hours/minutes/days) when introduced.
