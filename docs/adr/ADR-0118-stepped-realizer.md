# ADR-0118 — Stepped Realizer (`SolutionTrace` → Prose)

**Status:** Accepted
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0114, ADR-0114a, ADR-0115, ADR-0116, ADR-0117

---

## Context

ADR-0116 emits `SolutionTrace` records; ADR-0117 verifies them
independently. Phase 4 of the ADR-0114 GSM8K-math roadmap converts
those traces into **show-your-work prose** — one sentence per step,
plus setup sentences for initial state and an answer sentence at the
end. The eventual GSM8K eval lane (ADR-0119) needs this surface
because external readers and benchmark scorers consume prose, not
JSON traces.

The realizer is deliberately **separate** from the parser. The parser
maps prose → graph (consume); the realizer maps trace → prose
(produce). Their grammars overlap but are not symmetric.

---

## Decision

### `generate/math_realizer.py`

Exposes `realize(initial_state, trace) -> RealizedTrace`. Pure
function; same inputs → byte-equal output.

```text
RealizedTrace:
    setup_sentences   tuple[str, ...]   — one per InitialPossession
    step_sentences    tuple[str, ...]   — one per SolutionStep
    answer_sentence   str               — names the resolved unknown
    pack_id           str               — inherited from trace
```

`RealizedTrace.canonical_bytes()` is sorted-keys / compact-separators
JSON. `RealizedTrace.as_prose()` joins all sentences with spaces and
returns a single paragraph.

### Surface rules per step kind

| Kind | Phrasing |
|---|---|
| `add` | `<Actor> buys <N> more <unit>, raising the total to <after>.` |
| `subtract` | `<Actor> loses <N> <unit>, leaving <after>.` |
| `transfer` | `<Actor> gives <N> <unit> to <Target>, leaving <Actor> with <after>.` |
| `multiply (×2)` | `<Actor> doubles their <unit>, reaching <after>.` |
| `multiply (×3)` | `<Actor> triples their <unit>, reaching <after>.` |
| `multiply (other)` | `<Actor> multiplies their <unit> by <N>, reaching <after>.` |
| `divide` | `<Actor> splits their <unit> evenly into <N> groups and keeps one group, leaving <after>.` |

### Answer sentence rule

| Question shape | Phrasing |
|---|---|
| `Unknown.entity is None` (total-across) | `In total, they have <value> <unit>.` |
| `Unknown.entity == X` | `<X> has <value> <unit>.` |

### Singular / plural rule

Quantities of exactly 1 take the singular form ("1 apple"), all others
keep the canonical plural ("3 apples"). Matches the parser's
`_canonical_unit` round-trip — the parser maps "1 apple" → unit
"apples" at graph-time, so writing singular here does not break
round-trip on the noun.

---

## Round-trippability — explicitly out of scope

The realizer's prose is **not** guaranteed to re-parse through
`generate/math_parser.py`. The "raising the total to N", "leaving N",
etc. trailing phrases use comma-introduced clauses that the parser's
trailing-PP rule does not cover. Adding them to the parser is
deliberately deferred: the trace is the verifiable artifact
(ADR-0117), the prose is human-readable documentation.

A future Phase 4.X could ship a "compact realizer" that produces only
parser-grammar-compatible sentences (no explanatory tails) if
ADR-0119's lane needs round-trip property checks. For now the prose
is one-way: trace → prose, never prose → trace.

---

## Invariants

### `adr_0118_every_dev_set_case_realizes`

Every case in `evals/gsm8k_parser_dev/cases.jsonl` produces a
`RealizedTrace` without error. Parametrized over all 50 cases.

### `adr_0118_determinism`

Two `realize()` calls on the same trace produce byte-equal
`RealizedTrace.canonical_bytes()`. Parametrized over all 50 cases.

### `adr_0118_setup_count_equals_initial_state_count`

`len(result.setup_sentences) == len(graph.initial_state)` —
one setup sentence per asserted initial possession.

### `adr_0118_step_count_equals_operation_count`

`len(result.step_sentences) == len(trace.steps)` —
one step sentence per recorded solution step.

### `adr_0118_answer_sentence_contains_answer`

The numeric value and unit from `trace.answer_value` /
`trace.answer_unit` both appear in the answer sentence's text.

---

## ADR-0114a obligation discharge update

ADR-0118 does **not** directly discharge any of the ten
ADR-0114a obligations. It is **substrate for ADR-0119's GSM8K eval
lane**: a problem CORE answered correctly will now ship with both
the trace (Obligation #3) and a readable explanation. This makes the
"every correct answer ships with replay-equal trace" claim concretely
inspectable by a human reviewer who does not read JSON.

| Obligation | Status |
|---|---|
| #1 Sealed-holdout | Substrate present; per-lane enforcement deferred to ADR-0119 |
| #2 OOD surface variation | Discharged in full (ADR-0118a) |
| #3 Replay-equal trace | Discharged at verifier fidelity (ADR-0117); ADR-0118 makes the trace human-inspectable |
| #4 Typed refusal | Discharged at solver layer (ADR-0116) |
| #5 Reasoning-isolation perturbation suite | In flight (Codex, ADR-0125) |
| #6 Compositional-depth curve | Measurement-only at promotion |
| #7 Frontier-baseline comparison | Deferred to ADR-0119 |
| #8 Adversarial generation | Deferred to ADR-0119 |
| #9 Determinism | Discharged at solver + verifier + realizer layers |
| #10 Operation provenance via pack | Discharged in full (ADR-0116); realizer surfaces it via `pack_id` |

Five of ten obligations now load-bearing in code; ADR-0118 hardens
#9 across a third layer (realizer) and surfaces #3 / #10 to a human-
inspectable form.

---

## Acceptance evidence

Accepted when:

- `generate/math_realizer.py` exports `realize`, `RealizedTrace`,
  `RealizerError`
- `tests/test_math_realizer.py` is green
- All 50 dev-set cases realize without error
- Smoke suite green
- ADR linked from `docs/decisions/README.md` index and frontier

---

## Consequences

- Phase 4 of the ADR-0114 GSM8K-math roadmap lands. ADR-0119
  (eval lane) can now produce per-case scoring records that
  include both a verifiable trace AND a human-readable
  explanation.
- The "show-your-work" claim is now a first-class artifact. An
  external reviewer who runs the parser → solver → verifier →
  realizer pipeline can read CORE's reasoning step by step.
- The realizer's prose deliberately favors readability over
  round-trip parseability. A future Phase 4.X may add a compact
  round-trip-only mode if needed; for now the trace is the
  load-bearing verifiable artifact.

---

## Out of scope

- Round-trip parseability of realizer prose. Future Phase 4.X.
- Multi-paragraph or rhetorical variation (formal / casual /
  layperson register). Could integrate with the existing register
  system (ADR-0068..0072) in a future ADR if needed.
- Per-case explanation budgets (max length, max steps surfaced).
  Current implementation surfaces every step; future may compress.
- GSM8K-specific surface conventions. ADR-0119's lane may post-
  process the realized prose for benchmark presentation.
