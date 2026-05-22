# ADR-0114a — Anti-Overfitting Proof Obligations for `expert` Promotion

**Status:** Accepted (documentation-only; no code change)
**Date:** 2026-05-22
**Author:** CORE agents + reviewers
**Type:** Amendment to ADR-0114
**Depends on:** ADR-0091, ADR-0105, ADR-0106, ADR-0109, ADR-0113, ADR-0114, ADR-0115

---

## Context

ADR-0113 reserved the `expert` namespace for a future ledger tier above
`audit-passed`. ADR-0114 laid out a 7-phase arc toward a first `expert`
promotion (GSM8K-math), with ADR-0120 designated as the eventual
"first `expert` promotion contract."

The intervening discussion surfaced a load-bearing question: **how
does CORE prove a domain's `expert` claim is reasoning from concepts
rather than pattern-matching from seen examples?** This is *the*
distinguishing question for any capability claim beyond the structural
asymmetries `audit-passed` already verifies. An LLM scoring 95% on a
benchmark may be memorizing or surface-pattern-matching; the claim
"reasons from concepts" requires structural evidence that cannot be
faked.

The audit-passed gate does not need this discussion — it verifies
*claim shapes* (signed digest, replay determinism, typed refusal,
exact recall) that transformer LLMs structurally cannot produce
regardless of accuracy. But the moment a domain reaches for `expert`
on a public benchmark, that's a raw-capability comparison, and the
"is it actually reasoning?" question is the only credibility-bearing
question.

ADR-0114a writes down, before any `expert` promotion code is built,
the 10-point proof framework that ADR-0120's promotion contract must
enforce.

---

## Decision

The eventual `expert` promotion contract (ADR-0120) MUST require all
ten obligations below. Each obligation is **load-bearing and
falsifiable**: a domain that cannot satisfy any one of them stays at
`audit-passed`.

These obligations apply to every `expert` promotion, not just
GSM8K-math. Future expert domains (symbolic logic, DSL codegen,
etc.) inherit the same framework; per-domain specializations may
add further requirements but cannot weaken these.

### Obligation 1 — Sealed-holdout discipline

**Requirement.** The capability benchmark must include a held-out
split that is never read by any CORE component during development.
Holdout sealing per ADR-0105 (age-encrypted, recipient-keyed).

**Falsification.** If commit history shows any access to the
holdout cases during the window between dev-set authoring and the
release event, the promotion is invalid.

**Status.** Substrate already in place (ADR-0105 sealed holdouts;
ADR-0114 §5 GSM8K-test-set-is-holdout commitment). Per-lane
enforcement lands in ADR-0119.

### Obligation 2 — OOD surface variation must score ≥ 0.95 of dev

**Requirement.** A capability lane that scores `S` on its public
split must score ≥ `0.95 · S` on a programmatically-derived
out-of-distribution split that holds the underlying graph constant
but varies surface form:

- Entity-name renaming
- Unit relabeling (apples → nebulae, dollars → drachmas)
- Number-magnitude scaling (multiply all by k; for linear-arithmetic
  domains, answer must scale by k)
- Independent-sentence reordering

If CORE handles graph G correctly, it should handle every surface
that lexes to graph G. A drop > 5% from public to OOD signals
surface-feature dependence rather than reasoning from concepts.

**Falsification.** Score the same graphs through three surface
renderings; if the lowest-scoring rendering falls below
`0.95 · public_score`, the promotion is invalid.

**Status.** OOD generator authoring required. Likely ADR-0118
(stepped realizer extension can do double duty) or a separate
ADR-0118a.

### Obligation 3 — Every correct answer ships with a replay-equal trace

**Requirement.** For every problem CORE marks "correct" on the
public + holdout splits, an inspectable `SolutionTrace` artifact
exists with:

- Ordered sequence of operations
- Each operation tagged with the pack-lemma identifier it invokes
  (operation provenance)
- A byte-deterministic trace hash
- Verifier (ADR-0117) re-applies the trace and reproduces the
  declared answer

**Falsification.** If any "correct" answer cannot be paired with a
trace whose replay reproduces the answer, the promotion is invalid.
A trace that reproduces the *wrong* answer is more useful than no
trace at all — the *wrong* answer is then known to be a real CORE
mistake, not a fake reasoning artifact.

**Status.** Trace produced by ADR-0116 (solver). Verifier in ADR-0117.

### Obligation 4 — Refusal is a first-class outcome; misparse rate is zero

**Requirement.** Every problem produces exactly one of three
outcomes:

- `correct` — answer matches ground truth AND trace replays
- `wrong` — answer differs from ground truth (trace may still replay)
- `refused` — typed `ParseError` / `SolveError` with a reason naming
  the unsupported construction

**The `expert` threshold per ADR-0120 must require zero `wrong`
answers.** A high `refused` rate is acceptable and informative; a
nonzero `wrong` rate fails the gate. CORE cannot claim to reason if
it sometimes produces silent confabulations.

The distinction vs. LLMs is intentional: a frontier LLM scoring 95%
on GSM8K typically has ~5% wrong and ~0% refused (it confabulates
when uncertain). CORE's expert claim requires the opposite shape:
high correct + nonzero refused + **zero wrong**.

**Falsification.** Any verified wrong answer on the public or
holdout split — where "verified wrong" means the trace replays but
yields a value differing from ground truth — invalidates the
promotion.

**Status.** Parser (ADR-0115 Phase 1.3) already enforces typed
refusal; solver (ADR-0116) must enforce the same discipline. The
zero-wrong-on-public requirement is per-domain calibration; ADR-0120
sets it.

### Obligation 5 — Reasoning-isolation perturbation suite

**Requirement.** A programmatic perturbation generator produces an
unbounded test suite by applying invariance-preserving and
invariance-breaking transforms to dev/holdout cases:

| Transform | Expected behavior |
|---|---|
| Rename all entities | Answer unchanged |
| Rename all units | Answer unchanged |
| Multiply all numbers by k | Answer × k (linear domains); changes predictably (general) |
| Reorder independent sentences | Answer unchanged |
| Swap order of non-commuting operations | Answer changes predictably |
| Replace verb with synonym in registry | Answer unchanged |

CORE must pass 100% of invariance-preserving perturbations and produce
the predicted change on every invariance-breaking one. A pattern-matcher
that learned superficial features fails some perturbations; a system
reasoning from concepts passes all.

**Falsification.** ≥ 1% perturbation failure on any single transform
class invalidates the promotion.

**Status.** Generator authoring required. New ADR (likely ADR-0119
subsidiary or its own).

### Obligation 6 — Compositional-depth curve published

**Requirement.** Score correctness as a function of reasoning depth
(number of operations in the ground-truth graph). Publish the depth-
vs-accuracy curve from depth 1 through the maximum depth in the
benchmark. **The curve must be approximately flat** — accuracy at
depth N should not drop by more than `1 − (1 − ε)^N` for some
documented `ε`, where ε represents per-step parser/solver error.

A monotonically-decreasing curve indicates probabilistic
accumulation of errors; a flat curve indicates the architecture
handles N-step problems by the same mechanism as 1-step problems.

For comparison, LLM GSM8K curves typically decay sharply past
depth 4-5. CORE's curve should not.

**Falsification.** If any depth bucket scores below `(1 − ε)^N`
for the documented `ε`, the promotion is invalid (or `ε` must be
raised, with justification, in the published curve).

**Status.** Measurement only; no new code. Computed at promotion time.

### Obligation 7 — Frontier-baseline comparison on identical items

**Requirement.** Run the holdout split through at least one frontier
LLM baseline (citation-only, no live API call) and publish:

- Both raw scores
- A per-item disagreement matrix (CORE-correct × LLM-correct,
  -wrong, -refused/n/a; CORE-refused × LLM-correct, -wrong; etc.)
- Trace replay verification for every CORE-correct answer

The interesting cell — and the honest one to publish — is
**"LLM correct ∧ CORE refused"**. Those are problems where rule-based
grammar caps out; refusing them is correct behavior but it leaves
capability on the table. The size of this cell is a public, durable
measurement of CORE's current grammar coverage vs. frontier LLM
breadth. ADR-0120's expert threshold sets a maximum acceptable size.

**Falsification.** If the comparison report cannot demonstrate
trace replay on every CORE-correct answer, the promotion is invalid.

**Status.** Pattern established by ADR-0045 (long-context comparison);
GSM8K equivalent landed in ADR-0119.

### Obligation 8 — Adversarial generation; misparse rate zero

**Requirement.** A separate generator produces problems specifically
designed to exploit weak grammar / solver coverage:

- Edge-case phrasings within the documented grammar
- Problems combining patterns in untested ways
- Problems with deceptive surface (e.g. red-herring numbers)

Every adversarial problem must produce one of: `correct`, `refused`,
or — never — silent misparse. A **misparse** is defined as: parser
produces a graph that does NOT correspond to the surface meaning AND
the resulting answer is wrong.

**Misparse rate must be zero on the adversarial suite.** Refused
rate may be arbitrarily high; that's the safe failure mode.

**Falsification.** Any single observed misparse (graph + answer
disagreement with the surface) invalidates the promotion.

**Status.** Generator authoring required; likely under ADR-0119.

### Obligation 9 — Determinism across release boundaries

**Requirement.** Same problem text + same pack revision + same
solver revision → byte-equal trace hash across N runs (N ≥ 100) and
across at least one re-build of the runtime (proves no
floating-point-platform drift, no thread-order drift, no random
seed drift).

**Falsification.** Any non-determinism observation invalidates
the promotion until the source is identified and eliminated.

**Status.** Already an architectural invariant of CORE
(versor-closure, replay-determinism). Per-lane test gates run at
promotion time.

### Obligation 10 — Operation provenance via the pack

**Requirement.** Every operation in every published `SolutionTrace`
dispatches through a math-pack (or relevant-domain-pack) lemma
identifier, not a hardcoded string in solver code. The trace
includes the resolved lemma id for every operation, and changing the
pack changes the resolved set deterministically.

This obligation makes "reasons from concepts" architecturally true
rather than rhetorical. Without it, the parser-to-pack binding is
informal and the claim "the math pack provides the operation
vocabulary" is decorative.

**Falsification.** If any operation in a published trace cannot
resolve to a pack-lemma id, the promotion is invalid.

**Status.** Currently informal (parser hardcodes verb→operation-kind
mapping in ADR-0115 Phase 1.3). **Closing this gap is in-scope for
ADR-0116 (solver).** ADR-0114a documents the requirement; ADR-0116
implements the binding.

---

## Acceptance & enforcement

ADR-0114a is a **documentation-only contract**. No code lands with
this ADR.

It binds future ADRs:

- **ADR-0116 (solver)** — must add operation-provenance binding
  (#10) and trace shape that supports #3.
- **ADR-0117 (verifier)** — must produce replay-verdicts that
  support #3 and #9.
- **ADR-0118 / ADR-0118a (realizer + OOD surface generator)** —
  must produce OOD-rendering capability for #2.
- **ADR-0119 (GSM8K eval lane)** — must wire #1, #6, #7, #8 into
  the lane runner.
- **ADR-0120 (first expert promotion contract)** — must require
  all 10 obligations as hard gates, including the explicit numeric
  thresholds (zero wrong; ≥ 0.95·S on OOD; flat depth curve within
  documented ε).

Each downstream ADR cites which obligation it discharges. ADR-0120
finally invokes all ten.

---

## Invariants

### `adr_0114a_obligations_enumerated`

The 10 obligations above are the complete, ordered list. Adding an
obligation, removing one, or weakening one requires a numbered
amendment ADR. The list itself is sticky.

### `adr_0114a_no_silent_overfit`

Any future `expert` promotion ADR that omits one of the ten
obligations from its acceptance criteria is invalid. Reviewers
checking promotion ADRs MUST verify the obligations checklist is
populated. Skipping the checklist is grounds for refusal at review.

### `adr_0114a_audit_passed_unaffected`

ADR-0114a does NOT amend ADR-0106 / ADR-0109 / ADR-0113. The
`audit-passed` gate continues to verify CORE claim-shape compliance
(signed digest + replay determinism + typed refusal + exact recall)
without any of these ten obligations. The two tiers measure
orthogonal properties.

---

## Out of scope

- Specific numeric thresholds. Those belong to ADR-0120 (e.g. "depth
  curve ε ≤ 0.02"; "OOD score ≥ 0.95 · public_score"). ADR-0114a
  documents the *shape* of each obligation, not the numbers.
- Implementation of the perturbation generator. Future ADR.
- Implementation of the adversarial generator. Future ADR.
- LLM-vendor selection for #7 (frontier comparison). ADR-0045 set
  the convention (citation, not live API); ADR-0119 picks the
  specific baseline.
- Domains beyond mathematics_logic. The framework is domain-agnostic;
  each future expert domain (symbolic logic, DSL codegen, ...)
  inherits it. Per-domain specializations may add obligations but
  cannot remove any of these ten.
- Writing / open-prose capability. Even with all ten obligations
  satisfied, prose-domain `expert` claims need additional discussion
  (what "correct" means for prose is fuzzily defined); deferred per
  ADR-0114 §Phase F.

---

## Consequences

- The repo carries a public, dated commitment to a falsifiable proof
  framework for any future `expert` claim. The "are you sure you're
  reasoning, not pattern-matching?" question has a written answer:
  the 10 obligations, every one checkable.
- ADR-0116 / ADR-0117 / ADR-0118 / ADR-0119 / ADR-0120 each gain a
  subset of these obligations as scope items. Each downstream ADR
  cites which obligations it discharges.
- The `audit-passed` tier and the `expert` tier remain
  cleanly distinguished. Audit-passed verifies claim *shapes*
  (transformer-unreachable invariants); expert verifies *capability*
  with anti-overfitting proof. A domain can be one without the other,
  though in practice `audit-passed` is a prerequisite for `expert`.
- External readers (reviewers, investors, skeptics) now have
  an enumerated checklist to evaluate any future `expert` claim
  against. Promotions that omit obligations are easily distinguished
  from promotions that satisfy them.

---

## Open candidate directions (no ADR yet)

- **Cross-domain transfer probes.** Once two domains land at
  `expert`, can CORE solve a problem that requires combining
  operations from both packs (e.g. physics-units-aware arithmetic)?
  Not part of these 10 obligations but a natural next-tier question.
- **Adversarial generation budget.** How many adversarial problems
  is "enough" for #8? Likely answer: keep generating until refused
  rate stabilizes. ADR-0119 picks the convention.
- **Frontier baseline freshness.** ADR-0045's citation freezes
  vendor numbers at a point in time. Frontier scores drift up; CORE's
  comparison should be re-cited periodically. The cadence is a
  governance choice deferred to a future ADR.
