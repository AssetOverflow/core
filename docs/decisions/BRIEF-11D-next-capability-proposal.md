# BRIEF-11D — Next-Capability Proposal (post GSM8K reader closure)

**Status:** Proposed (decision artifact)
**Date:** 2026-05-27
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Parent brief:** [BRIEF-11](../handoff/BRIEF-11-phase-2-reader-closure-and-capability-snapshot.md)
**Gating rule:** [ADR-0166 — Measurement-Capability Sequencing Discipline](./ADR-0166-measurement-capability-sequencing.md)

---

## Purpose

Pick the single next capability to land after the Phase 2 reader closure pass
(Brief 11B-step-2 + 11C snapshot). One choice. Defended. Three rejected with
reasons. Per Brief 11 §"lead engineer has a yes/no decision artifact, not
another sprawling roadmap."

ADR-0166's three-question test gates every candidate:

- **Q1** What capability does this build before measurement?
- **Q2** What existing lane validates it? (No new lanes.)
- **Q3** What invariant proves `wrong=0` / closure / determinism?

---

## Candidates

### Candidate A — Continued GSM8K operator closure

Extend the comprehension reader (ADR-0164) for the remaining bottleneck
classes from `audit_brief_11.md`: `multi_quantity_composition` (8),
`quantity_extraction` (9), `fraction_percentage_literal` (3),
`comparatives`, rate parsing. Mechanical, per-frame work in
`generate/comprehension/`.

- **Q1 — Capability**: Each frame is a new composition rule on the
  existing `ComprehensionState` machine. The reader, state shape, and
  lexicon pack already exist on main; this is operator-level extension.
- **Q2 — Lane**: `evals/gsm8k_math/train_sample/v1` (canonical, in
  place). Capability-axis G1–G5, S1 lanes act as the regression net.
- **Q3 — Invariant**: `wrong == 0` by construction (admissibility +
  unit-proof + multi-branch-disagreement refusal stay in force).
  Determinism: frozen-dataclass state + canonical-bytes
  serialization → byte-equal trace hash on rerun. Closure: bottleneck
  audit row count strictly decreases.

### Candidate B — Cross-domain reader generalization

Port the incremental comprehension reader pattern to a non-math
domain (e.g. `en_core_relations_v1` kinship statements or
`en_core_cognition_v1` belief statements) to prove the architecture
isn't math-overfit. Authors a sibling lexicon pack and a parallel
state machine.

- **Q1 — Capability**: A second reader instance, sharing the
  `ComprehensionState` abstraction but with a domain lexicon + frame
  rules. Reader machinery is generic; domain coupling is the test.
- **Q2 — Lane**: Existing `evals/identity_divergence/` and the
  cognition-axis lanes consume relations/cognition packs today. No
  new lane required.
- **Q3 — Invariant**: Same admissibility + refusal contract as the
  math reader; pack-level mastery report + manifest checksum +
  byte-equal trace hash. **But:** the math reader has not yet
  cleared its first capability gate (GSM8K Round-2 exit
  `correct ≥ 25`). ADR-0166 §"Forbidden work" — measurement of a
  generalization before the original capability is anchored
  produces noise, not signal.

### Candidate C — Tool-use trace integration

Let the engine invoke deterministic tools (calculator, unit
canonicalizer, ratified-pack lookup) within a turn and record the
invocation in the trace. Hardens the teaching corridor by giving
contemplation a deterministic compute primitive.

- **Q1 — Capability**: A typed `ToolCall` record on the turn trace,
  whitelisted to deterministic pure-function tools (no network, no
  filesystem, no LLM), with replay-equivalence guarantees.
- **Q2 — Lane**: None of the existing canonical lanes exercise
  tool-use. `evals/long_context_cost/` and capability-axis lanes
  measure end-to-end accuracy, not intermediate compute. Adding a
  lane would violate ADR-0166. Existing teaching-corridor tests
  (`evals/identity_divergence/`, `evals/cognition/`) do not
  branch on tool presence — so they cannot distinguish
  capability-present from capability-absent.
- **Q3 — Invariant**: `wrong == 0` extends only if every tool is
  pure and deterministic. Determinism: tool output canonicalized
  into trace hash. Closure: undefined — the set of useful tools is
  open-ended.

### Candidate D — Workbench demo hardening

Make the read-only operator UI (ADR-0160/0162) load-bearing for
HITL ratification (ADR-0161), replay theater (W-031), and proposal
queue (W-029). Moves the workbench from demo-tier to operator-tier
infrastructure.

- **Q1 — Capability**: Surface-level integration of
  already-shipped backend mechanisms (ratification queue,
  contemplation candidates, replay). No new operator, no new
  recognizer, no new composition rule.
- **Q2 — Lane**: Workbench has no canonical capability lane in
  Tier 3 or capability-axis tables; it is operator-facing infra,
  not a measured capability. ADR-0166 §"Boundaries" — the rule
  governs eval lanes; UI work is out of scope for this ADR but
  also out of scope for Brief 11's "next capability" question.
- **Q3 — Invariant**: Determinism inherited from the underlying
  ratification + replay paths. `wrong == 0` not directly
  applicable — workbench is an inspector, not an admitter. Closure:
  W-029/W-031 acceptance criteria, not capability closure.

---

## Recommendation

**Recommended next: Candidate A — Continued GSM8K operator closure.**

### Why it beats the others on lift-per-risk

1. **Three-question test passes cleanly.** Capability exists
   (reader scaffolding on main); lane exists
   (`gsm8k_math/train_sample/v1` with a real baseline at 3/47/0
   today, the Phase 2 closure baseline after 11B-step-2); the
   invariant is mechanical (`wrong == 0` by construction +
   determinism by frozen state).
2. **The bottleneck audit names the work.** `audit_brief_11.md`
   has already ranked the highest-leverage missing operators
   (`lexicon_entry: 9`, `multi_quantity_composition: 8`,
   `quantity_extraction: 9`). The backlog is queued, sized, and
   risk-categorized.
3. **It is the only candidate that converges.** Phase 2 reader
   closure has an explicit exit criterion (ADR-0163 Round-3
   `correct ≥ 35`, `wrong = 0`). The work has a finish line.
   Candidates B, C, D do not — each opens new surface area.
4. **It unblocks every other candidate.** ADR-0166 §"Forbidden
   work" rejects authoring lanes/generalizations ahead of the
   capability that produces signal. Math reader closure is the
   gate every other candidate inherits.

### Rejection rationale

- **B (cross-domain reader)** — Generalizing the reader before
  the math reader clears Round-2 (`correct ≥ 25`) measures a
  generalization of an unanchored capability. The cross-domain
  result would be uninterpretable: a refusal could mean either
  the pattern doesn't generalize *or* the underlying reader is
  still under-built. Defer until math reader clears Round-3.
- **C (tool-use trace integration)** — Fails Q2 (no existing
  lane distinguishes tool-present from tool-absent) and Q3
  (closure is undefined). The mechanism is conceptually clean
  but ADR-0166 forbids building a capability whose signal would
  require a new lane to register. Revisit once a math problem
  class demonstrably refuses for reasons a calculator would
  resolve — that grounds the tool surface in real data.
- **D (workbench demo hardening)** — UI work is not a capability
  in the ADR-0166 sense. It does not advance
  `listen → comprehend → recall → think → articulate → learn`.
  It hardens a viewing surface for mechanisms that already work.
  Worth doing when the operator workflow demands it; not the
  next *capability* commit.

### First sub-PR scope

**Branch:** `feat/brief-12a-lexicon-entry-closure`
**Target:** `audit_brief_11.md` row `lexicon_entry: 9` (lowest-risk,
highest-count, cannot create wrong admissions without also passing
graph-completeness — per audit §"Highest-leverage backlog").

Deliverables (single PR):
- 9 lexicon entries added to `en_core_math_v1` with a manifest
  checksum bump and deterministic ordering.
- Pack test pinning the 9 new lemmas + their semantic categories.
- Reader rerun on `train_sample/v1` showing the 9 cases move
  from `unknown_word` either to admitted (preferred) or to a
  different refusal class (acceptable — surfaces the next gap).
- `wrong == 0` preserved.

Exit: `correct` rises by some amount ≥ 0, and the
`unknown_word` row in the audit taxonomy strictly decreases.
Refusal taxonomy may grow at other rows — that is real new work
becoming visible, not regression.

### Dependencies

- **Blocked on:** Brief 11B-step-2 (the two in-flight closure-fix
  branches) merging to main. The audit artifact and reader
  scaffolding must be the version 11D operates against.
- **Blocked on:** Brief 11C (capability snapshot) producing the
  post-closure baseline. The first 11D sub-PR's delta is
  measured against that baseline, not the pre-closure 3/47/0.
- **Independent of:** Workbench work (Candidate D), tool-use
  scoping (Candidate C), and any cross-domain reader prototype
  (Candidate B). Those remain backlog.

---

## Definition of "decided"

This document is a decision artifact, not a roadmap. The decision
recorded here:

> The next capability after GSM8K reader Phase 2 closure is
> continued GSM8K operator closure, starting with the
> `lexicon_entry` row of the Brief 11B audit. No new lanes. No
> cross-domain prototype. No tool-use scoping. No workbench
> promotion. Revisit candidates B/C/D after the math reader
> clears ADR-0163 Round-3 (`correct ≥ 35`, `wrong = 0`).

Reopening this decision requires either:
1. The first 11D sub-PR fails to register signal (audit
   `unknown_word` row does not shrink), indicating the
   lexicon-entry path is not the right next step, or
2. The math reader clears Round-3 ahead of expectation, retiring
   Candidate A and bringing B/C/D back into scope.

---

## Cross-references

- [ADR-0166](./ADR-0166-measurement-capability-sequencing.md) — the
  three-question test this document answers four times.
- [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) — the
  architecture this recommendation extends.
- [BRIEF-11](../handoff/BRIEF-11-phase-2-reader-closure-and-capability-snapshot.md)
  §"Failure modes to avoid §3" — eval surface inflation; this
  document declines to inflate it.
- `evals/gsm8k_math/train_sample/v1/audit_brief_11.md` — the
  bottleneck table the first sub-PR attacks.
- [SESSION-2026-05-27-tier3-sequencing](./SESSION-2026-05-27-tier3-sequencing.md)
  — the narrative grounding for "capability before measurement,
  measurement before expansion."
