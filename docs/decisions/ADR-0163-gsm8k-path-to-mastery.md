# ADR-0163 — Path to GSM8K mastery: candidate-graph admissibility via the contemplation/HITL corridor

**Status:** Proposed
**Date:** 2026-05-26
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Parent:** [ADR-0114a — Capability Obligations](./ADR-0114a-capability-obligations.md), [ADR-0119 — GSM8K eval lane](./)
**Companions:** [ADR-0149 — Recognizer pipeline](./), [ADR-0151 — Auto-proposal pipeline](./ADR-0151-auto-proposal-pipeline.md), [ADR-0152 — Learning-arc proof corridor](./ADR-0152-learning-arc-demo.md), [ADR-0155 — CI contemplation runner](./ADR-0155-ci-contemplation-runner.md), [ADR-0161 — HITL async queue](./ADR-0161-hitl-async-queue.md), [ADR-0132/0133/0134/0135 — Binding graph](./)

---

## Context — what the audit found

A scoping pass across the unlanded math branches and the actually-shipped
state on `main` produced a result that reframes the math architecture
question entirely.

### State of the math substrate on `main`

The following components are **already landed** (worktrees on disk are
stale forks of work that landed via other PR paths):

| Component | Status |
|---|---|
| `generate/binding_graph/` (all 7 modules: model, allocation, adapter, admissibility, units, question_target, `__init__`) | ✅ landed (ADR-0132/0133/0134/0135) |
| `generate/math_versor_arithmetic.py` (221 lines) | ✅ landed (ADR-0139/0140) |
| `generate/math_symbolic_equivalence.py` (97 lines) + `math_symbolic_normalizer.py` (371 lines) | ✅ landed (ADR-0131.1) |
| `generate/math_parser.py` (1,106 lines) | ✅ landed |
| `generate/math_candidate_parser.py` (2,232 lines) | ✅ landed |
| `generate/math_candidate_graph.py` (511 lines) | ✅ landed |
| `generate/math_problem_graph.py` (490 lines) | ✅ landed |
| `generate/math_solver.py` (506 lines), `math_verifier.py` (501 lines), `math_realizer.py` (422 lines), `math_roundtrip.py` (484 lines) | ✅ landed |
| Capability axis lanes G1..G5, S1 | ✅ landed with v1 corpora |

### Capability axis lane results on `main`

Every named capability axis passes its controlled lane at **100% with
`wrong = 0`**:

| Lane | Cases | Solved correct | Refused as expected | Wrong | Verdict |
|---|---|---|---|---|---|
| G1 verb classes | 20 | 20 | 0 | 0 | ✅ exit_criterion passed |
| G2 comparatives | 29 | 29 | 0 | 0 | ✅ wrong_count_is_zero |
| G3 numerics v1 | 26 | 20 | 6 | 0 | ✅ overall_pass: true |
| G4 multi-clause | 32 | 32 | 0 | 0 | ✅ wrong_count_is_zero |
| G5 aggregate | 20 | 20 | 0 | 0 | ✅ wrong_count_is_zero |
| S1 rate events | 20 | 20 | 0 | 0 | ✅ wrong_count_is_zero |

### GSM8K train-sample result on `main` (50 cases, ADR-0126)

```text
correct: 0
refused: 50
wrong:   0
exit_criterion: { correct_min: 10, wrong_max: 0, passed: false }
```

Every refusal reason is identical in shape:

```text
candidate_graph: no admissible candidate for statement: "<STATEMENT>"
```

Sample refused statements:

- `"Tina makes $18.00 an hour."` — rate with currency
- `"She splits it up into 25-foot sections."` — division-into-sections + unit
- `"The student council sells scented erasers in the morning before school starts to help raise money for school dances."` — descriptive setup, no extractable quantity
- `"There are some kids in camp."` — indefinite quantity ("some")
- `"In one hour, Addison mountain's temperature will decrease to 3/4 of its temperature."` — rate of change + fraction

### The reframe

The gap is **not** in operator algebra, **not** in the binding graph
internals, **not** in symbolic equivalence, **not** in the capability
axes themselves.  The gap is in `generate/math_candidate_graph.py` —
the admissibility surface that turns a natural-language statement into
a candidate the downstream pipeline can consume.

> **The capability axes pass at 100% because they test statement shapes
> the candidate-graph already admits.  GSM8K refuses at 100% because its
> statements span shapes the candidate-graph has never been taught.**

Every downstream component (binding graph, versor arithmetic, symbolic
equivalence, multi-clause decomposer, aggregator) is **mastered in
isolation**.  The lift to GSM8K is *admissibility expansion*, not
operator development.

This is the most consequential single finding in the math work to date.
It reframes the entire roadmap.

---

## Decision — what to build, in what order, under what doctrine

### Doctrine

Three non-negotiables:

1. **`wrong = 0` is invariant at every phase.**  A `wrong` answer is an
   architectural regression, not a tuning miss.  A `refused` answer is
   honest; a `wrong` answer is not.  Every exit criterion in this ADR
   reads `wrong_max: 0`.

2. **No hand-rolled recognizers.**  New statement shapes land via the
   `DerivedRecognizer` pipeline that ADR-0149/0154 already wired.  The
   recognizer comes from corpus exemplars, not from operator-written
   regex.  This honors [[thesis-decoding-not-generating]]: we teach the
   engine to *find* better, not stuff it with more found patterns.

3. **Every new shape lands through the contemplation → proposal →
   review corridor.**  No parallel learning path.  Recognizers are
   proposed by contemplation (ADR-0150/0152), gated by replay-equivalence
   (ADR-0057), reviewed by the operator via the HITL queue
   (ADR-0161), and admitted to the active corpus only on ratification.

These three rules, applied consistently, make admissibility expansion a
**capability** of the engine rather than an editing task on the
operator.

### Phases

#### Phase A — Refusal taxonomy (measure before building)

Goal: categorize every refused statement in the GSM8K train sample by
*statement shape*, not by content.

Deliverables:

1. `evals/gsm8k_math/refusal_taxonomy/v1/taxonomy.jsonl` — one record
   per refused statement, carrying `case_id`, `statement`,
   `refusal_reason`, and a typed `shape_category` enum.
2. Initial shape categories (extend as the corpus grows):
   - `rate_with_currency` — "Tina makes $18.00 an hour."
   - `unit_partition` — "She splits it up into 25-foot sections."
   - `descriptive_setup_no_quantity` — pure context with no extractable
     measurement.
   - `indefinite_quantity` — "some", "a few", "several".
   - `fractional_rate_of_change` — "decreases to 3/4 of its temperature".
   - `comparative_with_unit` — "20% more than", "twice as long as".
   - `nested_question_target` — "How many more than X did Y have?"
   - `temporal_aggregation` — "over five days, she earns…"
   - `conditional_quantity` — "if she had 2 more, she would have…"
3. A new eval lane `evals/refusal_taxonomy/` that runs the categorizer
   over an arbitrary refused-statement set and emits the histogram.
4. Acceptance: every refused statement in the 50-case sample has a
   typed `shape_category`; "uncategorized" count is reported but
   non-blocking.

This phase produces no recognizers and no corpus changes.  It is the
load-bearing measurement that prevents Phase B from chasing the wrong
gap.

#### Phase B — Exemplar corpus per shape category

Goal: for each top-N shape category from Phase A, hand-author a small
exemplar corpus (≤ 20 statements per category) with the expected
`MathProblemGraph` shape annotated.

Deliverables:

1. `teaching/admissibility_exemplars/<shape_category>_v1.jsonl` per
   category, each line carrying `statement`, `expected_graph`, and
   `provenance`.
2. The exemplar corpus is **reviewed-evidence floor** material under
   ADR-0057 — pack-consistent, boundary-clean, polarity affirms.
3. Top-N is chosen by Phase A's histogram.  Three categories per
   round; ratchet rather than scope creep.

This phase is the only place hand-authoring happens.  Twenty
statements per category, three categories per round — sixty hand-
authored statements total per round.  Each one is a *seed* the
contemplation loop generalizes.

#### Phase C — Contemplation ingests exemplars and emits recognizer proposals

Goal: the contemplation runner (ADR-0150/0152/0155) ingests each
exemplar corpus, decomposes the statements, and emits one or more
`DerivedRecognizer` proposals per shape category.

Deliverables:

1. Contemplation runner extended to ingest the exemplar corpus path as
   a candidate source (alongside `discovery_candidates.jsonl`).
2. Each proposal carries:
   - the shape category it generalizes,
   - the recognizer's pattern in canonical form,
   - replay-equivalence evidence against the active corpus + the
     exemplar set,
   - per-shape coverage metrics.
3. Proposals land in `teaching/proposals/proposals.jsonl` as usual
   (ADR-0057), visible in the HITL queue (ADR-0161 §1).
4. **`wrong = 0` invariant**: each proposal's replay-equivalence gate
   runs against the GSM8K train sample.  If accepting the proposal
   would lift `wrong` above 0 even on a single case, the proposal is
   auto-rejected at the gate.

#### Phase D — Operator ratifies through HITL queue

Goal: the operator reviews each recognizer proposal through the
existing surfaces (CLI / workflow_dispatch / GitHub PR review) per
ADR-0161 §2.

Deliverables:

- No new operator surface.  The proposals appear in the queue with
  their shape category, exemplar coverage, replay evidence, and the
  ratification CLI command.
- Operator accepts, rejects, or withdraws.
- Engineering wiring (landed alongside the operator surface, ADR-0163.D PR):
  - `generate/recognizer_registry.py` — pure projection of
    accepted `exemplar_corpus` proposals from the proposal log into
    a sorted-tuple of :class:`RatifiedRecognizer` records.
    In-process cache keyed on the log's (mtime, sha256).
  - `generate/recognizer_match.py` — per-category rules-only
    matchers (no LLM, no embedding) honoring the Phase C
    synthesizer's narrowness rule: out-of-corpus surface forms
    return None.  ``parsed_anchors`` carry extracted tokens from
    the statement.
  - `generate/math_candidate_graph.py` — narrowest-edit guard at
    the per-statement choice loop: before the existing "no
    admissible candidate for statement" refusal, consult the
    ratified registry.  Recognized statements are skipped from
    ``per_sentence_choices`` (contribute zero math state),
    preserving wrong=0 by construction.  Empty registry is a
    no-op.
  - Downstream consumption of ``parsed_anchors`` (turning
    recognized rate/temporal surfaces into solver state) is
    Phase E follow-up.

#### Phase E — Re-baseline GSM8K train sample

Goal: after each ratification round, re-run the train-sample eval and
update the counts.

Deliverables:

1. Automated re-baseline triggered by any merge that adds a recognizer.
2. Pass criteria for this ADR:
   - **Round 1 exit**: `correct ≥ 10`, `wrong = 0` on the 50-case
     sample (matches the existing exit criterion in the report's
     `exit_criterion` block).
   - **Round 2 exit**: `correct ≥ 25`, `wrong = 0`.
   - **Round 3 exit**: `correct ≥ 35`, `wrong = 0`.
3. Each round runs Phases A → B → C → D → E in sequence.

#### Phase F — Scale to public, holdout, full GSM8K

Once the train sample clears Round 3, scope expands:

| Split | Cases | Target |
|---|---|---|
| `public/v1` | 200 | `correct ≥ 0.5 × cases`, `wrong = 0` |
| `holdout/v1` | 200 | first run is measurement-only; do not tune against |
| Full GSM8K (8,500) | 8,500 | post-Phase F follow-up ADR; out of scope here |

The holdout run is **never** used to drive recognizer additions.  Per
ADR-0114a doctrine, holdout is the OOD ratio check; tuning against it
would invalidate the eval.

---

## Constraints (non-negotiable)

1. **`wrong = 0` at every phase, every round, every split.**  Refusals
   are honest; wrong answers are architectural regressions.  Any
   recognizer that would lift `wrong` above 0 is auto-rejected by the
   replay gate, never by operator judgment alone.

2. **No hand-rolled recognizers in `generate/`.**  Every recognizer
   added to the runtime comes from the contemplation → proposal →
   review corridor.  Phase B's exemplar corpus is **input** to that
   corridor, not output of it.  A PR that adds a regex-style
   recognizer directly to `math_candidate_parser.py` violates this ADR
   and must be rejected.

3. **Replay-equivalence is a precondition, never permission.**  Per
   ADR-0057, replay-equivalence makes a proposal *eligible for
   review*, not *automatically accepted*.  This ADR does not weaken
   that.

4. **Active corpus mutation only via `accept_proposal`.**  Per ADR-0152
   and ADR-0156/0158, the only path that mutates the active teaching
   corpus is the reviewed accept path.  Recognizer additions land via
   that path or not at all.

5. **No tuning against holdout.**  Phase F's holdout split is
   measurement-only.  Tuning against it makes the eval lie.

6. **Determinism preserved.**  Each round's recognizer addition is a
   reviewed, append-only mutation.  GSM8K runs at any historical SHA
   replay byte-identically given the corpus at that SHA.

---

## Out of scope

This ADR does not commit to:

- a frontier-model comparison harness beyond what ADR-0119 already
  scoped;
- a benchmark publication strategy;
- patent prep work;
- Rust backend parity for the math path (waiting on Python semantics
  to lock, per CLAUDE.md work-sequencing);
- the full GSM8K split (8,500 problems) — that lives in a follow-up
  ADR after Phase F clears `public`;
- non-GSM8K math benchmarks (MATH, AQuA, ASDiv) — scoped by separate
  ADRs once the corridor proves itself on GSM8K;
- multimodal math (charts, geometry images);
- a math-specific workbench surface — the existing Workbench (ADR-0160
  / 0162) is sufficient; lane-level inspection of refusal histograms
  becomes a `RefusalHistogramPanel` in the Eval Center (W-030) once
  that lands.

---

## Implementation plan — first three PRs

### PR 1 — Phase A scaffolding (refusal taxonomy)

- `evals/refusal_taxonomy/` lane: contract.md, runner.py, v1/cases.jsonl
  (mirrors the 50 refused statements from `train_sample/v1/report.json`).
- `evals/refusal_taxonomy/v1/shape_categories.py` — the enum.
- `core teaching refusal-taxonomy --input <path>` CLI command for
  re-running over an arbitrary refused set.
- Tests pin the enum coverage and the shape-categorizer's
  deterministic output.
- Produces an initial histogram of the 50-case sample.

### PR 2 — Phase B round 1 exemplar corpora

For the top three shape categories from PR 1's histogram, hand-author
≤ 20 exemplar statements each with expected `MathProblemGraph` shape.
No runtime change.

### PR 3 — Phase C contemplation extension

Extend the contemplation runner to ingest exemplar paths as candidate
sources.  Surface the per-shape coverage metric in the proposal log.
No new ratification path; existing HITL queue (ADR-0161) handles it.

After PR 3 lands, the contemplation runner produces recognizer
proposals; the operator ratifies; Phase E re-baseline confirms `correct
≥ 10, wrong = 0`.  Round 1 closes.

---

## Acceptance criteria

This ADR is ratifiable when:

1. The audit findings above are independently verifiable by running
   each capability axis lane on `main` and observing `wrong = 0`.
2. The GSM8K train-sample `correct: 0, refused: 50, wrong: 0` baseline
   is reproducible at the current commit SHA.
3. The phase ordering (A → B → C → D → E → F) does not allow Phase B
   to start before Phase A produces a histogram, nor Phase C before
   Phase B writes exemplars.
4. The `wrong = 0` invariant is enforced as an auto-reject in the
   replay-equivalence gate, not as a post-hoc operator check.

This ADR is **delivered** when:

5. GSM8K `public/v1` (200 cases) reaches `correct ≥ 100, wrong = 0`.
6. GSM8K `holdout/v1` measurement-only run is recorded once at the
   end and never used to drive recognizer additions.

---

## Consequences

### Positive

- The math roadmap is reduced from "build operators, build axes, build
  decomposer, build aggregator" to **one** problem: expand the
  candidate-graph's admissibility surface through the contemplation
  corridor.  Every other math component is mastered.
- Recognizer additions become a *capability* of the engine, not an
  editing task on the operator.  The thesis ("decodes, not generates")
  manifests in the math lane directly.
- The exit criterion (`wrong = 0` at every round) is enforceable by the
  replay gate, not by operator vigilance.
- The HITL queue (ADR-0161) absorbs the curriculum-expansion pressure
  the master plan flagged as a future risk.  Math is the first lane
  that scales through it.

### Negative

- Phase A (refusal taxonomy) is upfront measurement work that ships no
  capability.  Two-three days of audit before any GSM8K case starts
  passing.  Worth it; the alternative is operators chasing whichever
  problem shape caught their eye first.
- The exemplar corpus (Phase B) is hand-authored.  Sixty statements
  per round, hand-checked for shape correctness, is real work.  The
  alternative — auto-mining exemplars from GSM8K itself — would
  violate the holdout discipline and tune against the benchmark we're
  trying to honestly measure.
- The `wrong = 0` auto-reject gate may auto-reject proposals that are
  *almost* right.  This is intentional.  An almost-right recognizer
  that produces one wrong answer is worse than a refusal.

### Risks

- **The taxonomy could fragment.**  Mitigation: cap initial shape
  categories at ~9 and require every new category to cite ≥ 3
  refused statements.  Phase A acceptance test enforces this.
- **The HITL queue could backlog.**  ADR-0161 §4's pending cap (256)
  applies here.  If math proposals saturate the queue, the operator
  raises the cap via repo variable or pauses contemplation runs.
- **Recognizer generalization could overfit to exemplars.**  Mitigation:
  every recognizer is replayed against the *entire* GSM8K train sample
  and the public capability axes; regression on any axis auto-rejects.

---

## Cross-references

- [ADR-0114a — Capability Obligations](./ADR-0114a-capability-obligations.md) — perturbation, OOD ratio, depth curve obligations the math lane must keep honoring
- [ADR-0119 — GSM8K eval lane](./) — eval lane definition
- [ADR-0131.G.* — capability axis lanes](./) — G1..G5, S1 mastered
- [ADR-0132/0133/0134/0135 — binding graph](./) — landed substrate
- [ADR-0139/0140 — versor arithmetic](./) — landed operator algebra
- [ADR-0149/0154 — recognizer pipeline](./) — substrate this ADR builds on
- [ADR-0150/0152 — autonomous contemplation + learning-arc corridor](./ADR-0152-learning-arc-demo.md) — proposal source
- [ADR-0155 — CI contemplation runner](./ADR-0155-ci-contemplation-runner.md) — async producer
- [ADR-0057 — proposal review + replay-equivalence](./ADR-0057-teaching-chain-proposal-review.md) — gating discipline
- [ADR-0161 — HITL async queue](./ADR-0161-hitl-async-queue.md) — review surface
- [CLAUDE.md](../../CLAUDE.md) — `wrong = 0` discipline, no hidden normalization, exact recall, proposal-only learning

### Memory cross-references

- [[thesis-decoding-not-generating]] — the load-bearing thesis this ADR
  applies to math.  Every recognizer comes from the engine learning a
  shape, not from the operator stuffing a regex.
- [[feedback-address-critiques-dont-waive]] — the audit critique
  ("the gap is admissibility, not operators") is acted on here, not
  noted.
- [[feedback-adr-cross-reference-discipline]] — every substrate this
  ADR builds on is cited; no parallel mechanism is introduced.
- [[feedback-cleanup-as-you-find]] — the stale `feat/adr-0131-*` and
  `feat/binding-graph-phase*` branches on disk should be deleted as a
  hygiene PR after this ADR ratifies; the work is already on main.
- [[feedback-scope-time-is-cheap]] — Phase A is the "pause and scope"
  move applied to math.  Two-three days of taxonomy before any
  recognizer work prevents weeks of chasing the wrong gap.
