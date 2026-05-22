# ADR-0114 — Expert-Capability Roadmap: GSM8K-Math First

**Status:** Proposed
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Depends on:** ADR-0091, ADR-0106, ADR-0109, ADR-0110, ADR-0111, ADR-0112, ADR-0113
**Supersedes:** none (greenfield)

---

## Context

ADR-0113 reserved the `expert` namespace for a future ledger tier
above `audit-passed`. `audit-passed` verifies CORE *claim-shape
compliance* (signed digest, replay determinism, typed refusal, exact
recall) — a real, transformer-unreachable property. It does **not**
verify raw task performance against external benchmarks.

This ADR proposes the first concrete path toward an `expert` ledger
status. It is greenfield: no engine for it exists today.

### Honest framing of distance

The current architecture is impressive at the substrate level
(determinism, exact CGA recall, reviewed teaching, audit trail). It
is **far from expert-level on generative tasks**:

- The deterministic realizer composes pack lemmas via fixed templates
  and reviewed teaching chains. There is no symbolic solver, no proof
  search, no multi-step problem decomposition.
- `en_mathematics_logic_v1` pack has 16 lemmas. Solving an
  AMC-10 problem requires a working pipeline that does not exist.
- "Expert prose" is fuzzily defined and would need ~30k+ lemma
  lexicon plus discourse-level planning beyond current capability.

The honest current state is: **no domain is at expert-level capability
by any external measure**. The `audit-passed` rows for math and
physics describe CORE-specific claim shapes, not raw-task supremacy.

This ADR proposes building toward that — starting with the lowest-
hanging credible target: **grade-school math word problems on GSM8K**.

### Why GSM8K first

- **Public benchmark with established frontier baselines.** Frontier
  LLMs report 92-95% on GSM8K. Smaller open models report 30-70%. The
  comparison space is well-mapped.
- **Checkable answers.** Each problem has a single integer answer; no
  fuzzy grading required.
- **Smallest architectural delta.** The math pack already names the
  right operators (`adds`, `subtracts`, `multiplies`, `divides`); the
  realizer already composes deterministic surfaces. The missing piece
  is a real solver loop, not a fundamentally different substrate.
- **Honest first step.** If CORE scores at 6th-grader level on GSM8K,
  the result is *still load-bearing* — because the score would be
  replayable, traceable, and grounded in a way frontier LLM scores
  structurally cannot be. We can claim "Nth-percentile GSM8K, with
  trace-verifiable solutions" — a claim no LLM can make.
- **Compositional fit.** GSM8K's reasoning depth (typically 2-8 steps)
  fits CORE's proposition-graph + teaching-chain substrate without
  requiring an unbounded search.

---

## Decision

Establish a phased path to a first `expert` ledger tier claim, scoped
to **`mathematics_logic`** as the first domain and **GSM8K** as the
first benchmark. Each phase is its own ADR; this ADR proposes the
sequence and defines exit criteria.

### Phase 1 — Problem Parser (ADR-0115, future)

Build `generate/math_parser.py`: turns a natural-language word problem
into a typed proposition graph.

- Input: GSM8K problem string.
- Output: a `MathProblemGraph` with typed nodes: `entity`, `quantity`,
  `unit`, `operation`, `unknown`, `relation`.
- Constraint: deterministic. Same input → byte-identical graph.
- No solver yet — just structured parse.

Exit criterion: on a curated dev set of 50 GSM8K-style problems
(authored, not from GSM8K to avoid contamination), parse correctness
≥ 0.90 measured by human review against a published rubric.

### Phase 2 — Deterministic Solver (ADR-0116, future)

Build `generate/math_solver.py`: a tiny term-rewriting system over the
`MathProblemGraph` using the existing math-pack operator vocabulary.

- Input: `MathProblemGraph`.
- Output: a `SolutionTrace` — ordered list of operation applications
  ending at a numeric answer (or a typed refusal if the graph is
  under-determined).
- Constraint: pure function. No sampling. Trace is byte-deterministic
  from input.

Exit criterion: on the Phase 1 curated dev set, solver yields correct
final answer on ≥ 80% of graphs the parser produces correctly. The
solver does **not** need to solve every problem; it needs to be honest
about which it can.

### Phase 3 — Verifier (ADR-0117, future)

The verifier re-derives the answer from the `SolutionTrace` and emits
a typed verdict. This is the easy phase — CORE's substrate already
has replayability. The verifier just enforces it on this new artifact.

Exit criterion: replay determinism = 1.0 on all Phase 2 outputs.

### Phase 4 — Stepped-Realizer Extension (ADR-0118, future)

Extend the existing realizer to emit show-your-work prose from a
`SolutionTrace` — one sentence per operation, with pack-grounded
operator vocabulary.

Exit criterion: every Phase 2 success produces a stepped explanation
of length proportional to trace length, with each sentence
pack-grounded.

### Phase 5 — GSM8K Eval Lane (ADR-0119, future)

Author `evals/gsm8k/`:

- `dev/cases.jsonl` — curated subset of GSM8K train (300 problems).
- `public/v1/cases.jsonl` — curated subset of GSM8K train (1500
  problems; disjoint from dev).
- `holdouts/v1/cases_plaintext.jsonl` — curated subset of GSM8K
  *test* (300 problems; never read during development).
- `runner.py` — drives parser → solver → verifier → realizer and
  scores against the integer answer.
- `contract.md` — lane contract; lane shape `gsm8k_capability_shape`
  (new shape; introduced by ADR-0119 amendment to ADR-0109).

Exit criterion: lane runner produces deterministic results. Honest
first number reported (whatever it is).

### Phase 6 — First `expert` Promotion Contract (ADR-0120, future)

Define the `expert` ledger status:

- `expert=true` iff:
  1. `audit_passed=true` predicates pass (ADR-0106 + ADR-0109)
  2. At least one **capability lane** attached to the domain meets a
     **human-expert-calibrated threshold** declared in the lane's
     `contract.md`
  3. Reviewer-signed `expert_claims` entry whose evidence-bundle
     digest reproduces byte-for-byte (mirrors ADR-0106 §1.5 exactly)
  4. The capability lane's threshold is declared **publicly** in the
     ADR, not buried in a config — so external readers can debate the
     calibration.

For GSM8K specifically, candidate human-expert-calibrated thresholds:

| Threshold | Interpretation |
|---|---|
| ≥ 0.40 | "competent" — beats average 14-year-old human |
| ≥ 0.60 | "advanced" — competitive open-source LLM territory |
| ≥ 0.85 | "expert" — frontier-LLM territory; published-paper bar |

ADR-0120 must pick one and justify the choice. The chosen number is
*falsifiable*: if CORE scores below it, no `expert` row.

### Phase 7 — Second Capability Domain (ADR-0121+, future)

Pick a second capability domain only after Phase 6 lands. Likely
candidates: symbolic logic with quantifiers (closest cousin to math),
or DSL code generation (checkable, lexicon-bounded). Defer until
math expertise is real.

### Writing / open-prose capability — explicitly deferred

Open prose ("expert essay" / "expert article") is **not** on this
roadmap. Reasons:

- "Correct prose" is fuzzily defined; no GSM8K-equivalent benchmark
  exists with sharp scoring.
- Required lexicon (~30k+ working English lemmas) is two orders of
  magnitude larger than the current cognition pack.
- Discourse-level planning beyond current capability would need a
  separate architectural arc.

Writing capability becomes appropriate once at least two symbolic
domains have landed at `expert` and the substrate has been stress-tested
against checkable benchmarks.

---

## Non-Decisions

This ADR explicitly does **not**:

- Commit to a phase timeline. Each phase is its own ADR with its own
  scope. The ADR sequence is the durable artifact; the schedule is not.
- Promise CORE will reach 85% GSM8K. We commit to *honest scoring*,
  not to a target. If the architecture caps out at 35%, we report 35%.
- Pretend the audit-passed gate is a capability claim. The two tiers
  are distinct and remain distinct.
- Re-render existing audit-passed claims as expert claims. Math and
  physics audit-passed promotions stand independently of any future
  expert promotion on the same domain.

---

## Invariants

### `adr_0114_expert_namespace_undefined_until_adr_0120`

No code ships an `expert` ledger status before ADR-0120 lands. The
`_EXPERT_DOMAIN_STATUSES` tuple in `core.capability.reporting` stays
at 5 entries. Tested by the existing reporting tests.

### `adr_0114_gsm8k_is_first_capability_target`

The first capability lane authored under this roadmap is GSM8K
(ADR-0119). No other capability lane lands first.

### `adr_0114_expert_requires_explicit_threshold`

The first `expert` promotion contract (ADR-0120) must declare a
public threshold number for the underlying capability lane. No
hidden calibration.

---

## Acceptance evidence (for this proposed ADR)

ADR-0114 is accepted when:

- The ADR file exists in `docs/decisions/` and is linked from
  `docs/decisions/README.md`
- No code changes — this is a roadmap ADR only
- README updated to point at this sequence as the path-to-expert

No tests need to be added by this ADR. Tests are scoped to each
implementation ADR.

---

## Consequences

- The repo has a public, dated commitment to a first expert-capability
  target. The "what are you actually claiming is expert-level?"
  question now has a written answer: nothing yet; the path is ADR-0115
  through ADR-0120.
- The first `expert` claim, when it lands, will be *falsifiable*: tied
  to a public benchmark with a stated threshold. If CORE underperforms,
  the row stays at `audit-passed`.
- The `audit-passed` status remains the load-bearing CORE-vs-LLM claim
  in the interim. Nothing about the expert roadmap diminishes it; the
  two tiers measure orthogonal properties.

---

## Out of scope

- Implementation of any of Phases 1-7. Each is its own ADR.
- Writing / open-prose roadmap. Deferred until at least one symbolic
  domain lands at `expert`.
- Specific GSM8K threshold choice. ADR-0120's job.
- Alternative first benchmarks (MATH, MMLU-math, AIME). All are
  candidates after GSM8K; none replace it as Phase 1.
