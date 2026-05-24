# ADR-0137 — Retrospective Binding Layer

**Status:** Draft (design-only; depends on `audit/adr-0136-refusal-rescan-v2`)
**Date:** 2026-05-23
**Parent:** [ADR-0136](./ADR-0136-statement-layer-corridor.md)
**Supersedes (in part):** the S.x micro-extension treadmill — see Decision §3

---

## Context

ADR-0136's S.0 taxonomy pinned the architectural ceiling of statement-layer
parsing: of the 50-case GSM8K train sample, **23/50** primary barriers are
`context_filler` — narrative scene-setting sentences that legitimately carry
no numeric state on their own. ADR-0136 stated explicitly:

> The 23 context-filler cases will not be addressed by statement-layer work
> alone — they need semantic classification of scene-setting sentences,
> which is a separate architectural concern.

S.0 (context classifier) skipped them safely. S.1 (rate/event) and S.2
(conditional-op question) each unlocked one additional case (0014, 0042),
via **short-circuit paths in `parse_and_solve`** that bypass graph
construction entirely. Three case admissions on the train sample (0014,
0018, 0042), `wrong == 0`.

The short-circuits are correct as tactical bridges. They are wrong as a
long-term architecture: every future `S.x` adds another bespoke path,
forcing a "graph path or short-circuit?" choice with no principled
answer. That is the same micro-extension treadmill the G.x axis program
was retired from.

The deeper problem the short-circuits accidentally surfaced is that
the parser's *forward-only* topology cannot represent the most common
GSM8K shape: an earlier sentence whose meaning is only resolved by a
later sentence. Cases like:

- **gsm8k-0001** — "Tina makes \$18.00 an hour" is not load-bearing until
  the question fixes a work duration and an overtime rule.
- **gsm8k-0022** — "Erica…earning \$20 per kg of fish" is buried in a
  scene-setting paragraph; the rate only becomes a candidate once the
  question pulls it forward.
- **gsm8k-0050** — "every other day for 2 weeks" only solves when the
  question demands a frequency × duration binding.

The CORE-aligned response is a **bounded retrospective binding layer**:
the first pass emits *non-solving* typed candidates for sentences it
cannot fully ground; later sentences/questions may bind those candidates
only when the binding is unique, slot-complete, and verifier-replayable.

This is not "the solver re-reads prior sentences and resolves ambiguity"
(which would be best-effort semantic guessing — forbidden by CLAUDE.md).
It is a **refusal-first typed binding system**: no `BindingProof`, no
admission.

---

## Decision

### 1. Pipeline shape change

The current pipeline:

```
text → split sentences → per-sentence extractors → round-trip filter
     → Cartesian product → solve per branch → decision rule → answer | refuse
```

becomes:

```
text → split sentences
     → first pass: per-sentence extractors (existing) + deferred-candidate
       extractors (new) + context-frame classifier (new)
     → ContextFrame[]  +  DeferredCandidate[]  +  CandidateInitial[]  +
       CandidateOperation[]  +  CandidateUnknown[]
     → binding pass: for each DeferredCandidate, attempt to construct a
       BindingProof from later-sentence evidence
     → second pass (after binding): existing Cartesian product enumeration
       over the *bound* candidate set (deferred candidates that bound become
       ordinary CandidateInitial/CandidateOperation; unbound deferred
       candidates are dropped, not refused)
     → existing decision rule → answer | refuse
```

The binding pass is the only new control-flow stage. Everything downstream
of it (graph construction, solve, decision rule) is unchanged. This keeps
the existing `wrong == 0` guarantees in place.

### 2. Subsumption of S.1/S.2 short-circuits

**Directive.** Every current short-circuit admission must be re-derivable
as a `(DeferredCandidate, evidence, BindingProof)` triple. Short-circuits
are kept only as regression fixtures, not as a permanent admission route.

The three current admissions cleanly fit the binding shape:

- **0014** — capacity statement is a `DeferredCandidate.RateLike`
  awaiting a duration-binding from the question.
- **0018** — same shape, after the context classifier skips the opening
  filler sentence.
- **0042** — initial-state is admitted directly (no deferral needed);
  the conditional-op question is a `DeferredCandidate.MutationLike`
  awaiting a matching `(entity, unit)` from the initial-state set.

When the binding layer can re-admit all three, the short-circuit blocks
in `parse_and_solve` are deleted in the same PR that adds the binding
admission path. No parallel admission routes are retained.

### 3. The S.x micro-extension program is paused

S.3 (compound statements) and beyond are **not** the next implementation.
The 5 compound cases will instead serve as part of the ADR-0137 pressure
suite. S.x resumes only if the rescan ledger surfaces a clean,
homogeneous, *non-cross-sentence* cluster that the binding layer
provably cannot reach.

---

## Concrete type shapes

All shapes are frozen, slotted dataclasses; immutable per CLAUDE.md
"do not mutate" rule. All live under a new module
`generate/binding/` to keep the surface clean.

### `ContextFrame`

Emitted by a widened classifier (sibling to ADR-0136.S.0's
`classify_sentence`). Records non-numeric narrative as *typed* context —
no longer a black box. Allows later sentences to query "is there an
introduced-actor here named X?" without scanning raw text.

```python
@dataclass(frozen=True, slots=True)
class ContextFrame:
    sentence_index: int
    sentence_text: str
    introduced_actors: tuple[str, ...]      # proper-noun entities mentioned
    introduced_activities: tuple[str, ...]  # closed verb set (rents, plays, ...)
    has_numeric_token: bool                 # carried over from S.0
```

A `ContextFrame` never participates in graph construction. It is
read-only evidence consulted during binding.

### `DeferredCandidate`

A typed candidate that did **not** ground its full slot set during the
first pass, but whose grammar matched a recognized partial shape. Each
variant declares which slots are open and what shape of evidence can
close them.

```python
DeferredKind = Literal[
    "rate_like",         # subsumes S.1 capacity/earnings sentences
    "mutation_like",     # subsumes S.2 conditional-op question
    "partition_like",    # "She splits it up into 25-foot sections"
    "fractional_like",   # "his fish ate half of them"
    "anchor_like",       # "Rachel is 12 years old, and her grandfather is..."
]

@dataclass(frozen=True, slots=True)
class DeferredCandidate:
    deferred_id: str                    # sha256 of canonical shape
    kind: DeferredKind
    source_sentence_index: int
    source_span: str
    bound_slots: tuple[BoundSlot, ...]  # what *did* ground this pass
    open_slots: tuple[str, ...]         # slot names awaiting binding
    admissibility_template: str         # name of round-trip check to apply
                                        # once all open_slots are bound
```

Concrete kinds are defined per-shape in `generate/binding/kinds/*.py`,
each with its own open-slot vocabulary. A `rate_like` candidate's open
slots are typically `("duration_count", "duration_unit")`. A
`mutation_like` candidate's open slots are typically `("initial_value",)`
bound from the matching initial-state.

### `BoundSlot`

```python
@dataclass(frozen=True, slots=True)
class BoundSlot:
    name: str                # entity | unit | value | rate | duration |
                             # operation | actor | money_amount | …
    normalized_value: str    # canonical surface form
    source_sentence_index: int
    source_span: str
```

### `BindingProof`

The load-bearing object. Generated only when **all** of a deferred
candidate's open slots have been filled from later-sentence evidence
**and** the round-trip admissibility check passes.

```python
@dataclass(frozen=True, slots=True)
class BindingProof:
    deferred_candidate_id: str                # ties to DeferredCandidate
    deferred_sentence_index: int
    evidence_sentence_index: int              # the sentence that closed it
    evidence_span: str
    newly_bound_slots: tuple[BoundSlot, ...]  # slots closed by this binding
    admissibility_checks: tuple[str, ...]     # names of round-trip checks
                                              # that passed for this proof
    replay_digest: str                        # see below

    @property
    def is_unique(self) -> bool: ...
```

**`replay_digest` specification (non-negotiable):**

```
replay_digest = sha256(
    canonical(deferred_candidate_serialization) ||
    canonical(evidence_span_normalized) ||
    canonical(sorted(newly_bound_slots_by_name))
).hexdigest()
```

where `canonical(...)` is the same JSON-sort-keys serialization the
existing cognition eval uses for trace-hash stability. Two binding
proofs over the same evidence-binding therefore produce the same
digest. This makes the digest a dedup key, a regression hash, and a
replay assertion all at once.

### `BindingPass` result

```python
@dataclass(frozen=True, slots=True)
class BindingPassResult:
    proofs: tuple[BindingProof, ...]
    promoted_initials: tuple[CandidateInitial, ...]    # from bound rate_like
    promoted_operations: tuple[CandidateOperation, ...] # from bound mutation_like
    unbound_deferred: tuple[DeferredCandidate, ...]    # dropped, not refused
    rejected_bindings: tuple[BindingRejection, ...]    # for diagnostics
```

The pipeline consumes only `promoted_initials` + `promoted_operations`
downstream — the existing graph machinery does not need to know about
the binding layer. This is the entire isolation boundary.

---

## Non-negotiables

1. **No `BindingProof` → no admission.** A deferred candidate that
   cannot construct a complete proof from later evidence is dropped,
   not refused, not best-effort-solved. Refusal of the whole problem
   only happens through the existing decision rule, after promotion.

2. **No guessing.** A binding is admitted only when the open slots are
   uniquely closed by exactly one evidence sentence. Ambiguous
   bindings (multiple evidence sentences could close the same slot
   with different values) refuse the binding, not pick one.

3. **No hidden LLM fallback.** The binding layer is pure deterministic
   matching against closed slot vocabularies. No semantic embedding
   lookup, no fuzzy match, no model-aided disambiguation.

4. **No accepting `ContextFrame` as numeric state.** Context frames
   carry typed *names* and *activities* only, never quantities.
   ADR-0136's safety rail stands.

5. **`wrong == 0` remains a hard CI gate** — across the binding eval
   lane and the GSM8K probe.

6. **No solver/graph/verifier changes.** The binding layer feeds the
   existing graph machinery promoted candidates that are
   indistinguishable from first-pass candidates.

7. **Determinism.** All binding passes are pure functions over the
   first-pass candidate set + `ContextFrame[]`. Same input → same
   `BindingPassResult` bytes, same `replay_digest`s.

---

## Probe-set selection

The binding lane needs a probe set that is **honest about both directions**:
cases the binding layer must admit (including subsumed short-circuits),
and cases it must continue to refuse.

### Required admissions (subsumption + new unlocks)

| Case | Current path | Post-0137 path |
|---|---|---|
| 0014 | S.1 short-circuit | `rate_like` deferred + question evidence |
| 0018 | S.0 + S.1 short-circuit | same, after context-frame skip |
| 0042 | S.2 short-circuit | `mutation_like` deferred + initial-state evidence |
| 0001 | refused | `rate_like` (Tina) + question-duration binding (overtime rule deferred) |
| 0022 | refused | `rate_like` (Erica) bound from question evidence |
| 0050 | refused | `rate_like` + `anchor_like` ("every other day for 2 weeks") binding |

The exact admissibility of 0001, 0022, 0050 is conditional on the rescan
v2 ledger — if any of them turn out to have a non-binding-shaped barrier
(e.g. 0001's overtime requires conditional branching, which is deferred),
they enter as "binding-layer reaches the candidate but the second-stage
solver still refuses" cases. That is the right shape: the binding layer
moves the barrier *into* the solver, where it becomes a separately
addressable problem.

### Required continued refusals (negative probes)

The binding layer must **not** admit cases like:

- **gsm8k-0005** — "In one hour, Addison mountain's temperature will
  decrease to 3/4 of its temperature." The "of its temperature" is a
  self-reference; no later sentence can ground it without a fractional-
  mutation solver. Must refuse.
- **gsm8k-0039** — "everyone ate too much food and gained weight." No
  numeric token, no closed verb. Must refuse (context-frame only).
- Cases with multiple plausible bindings that resolve to different
  answers — must refuse via the uniqueness check.

The probe lane file (`evals/math_capability_axes/RB1_retrospective_binding/v1/cases.jsonl`)
is sized to ≥30 with at least 10 negative-probe cases.

### Pressure suite (cross-sentence comprehension)

The five `compound_statement` cases from ADR-0136 (0010, 0012, 0015, …)
enter as **pressure tests**, not as admission targets. Some may bind,
some won't. The honest outcome is recorded.

---

## Phased rollout

**One branch**, incremental. Four parallel branches were considered and
rejected — the 2026-05-23 worktree-race lesson stands.

| Phase | Deliverable | Branch |
|---|---|---|
| 0137.D | This ADR + post-rescan ledger inheritance | `docs/adr-0137-retrospective-binding` (this PR) |
| 0137.A | `generate/binding/{types,context_frame}.py` + tests for the type machinery alone | `feat/adr-0137-binding-types` |
| 0137.B | First kind (`rate_like`) + binding pass + 0014/0018 subsumption; short-circuit deleted in same PR | `feat/adr-0137-rate-like-subsume-s1` |
| 0137.C | Second kind (`mutation_like`) + 0042 subsumption; short-circuit deleted | `feat/adr-0137-mutation-like-subsume-s2` |
| 0137.E | Eval lane `RB1` + probe set | `feat/adr-0137-rb1-lane` |
| 0137.F | New unlock candidates (0001/0022/0050) — only if rescan ledger confirms binding-shaped | `feat/adr-0137-new-admissions` |

Each implementation phase is its own PR. Each must hold `wrong == 0` and
preserve the existing B3 lane. No phase merges until the lane test for
the previous phase is green on `main`.

---

## Open questions (deferred to implementation ADRs, not this one)

- **Multi-step binding chains.** Can a `DeferredCandidate` be bound by
  another `DeferredCandidate` that itself just got bound? Provisionally
  no (forbids transitive binding, keeps the binding pass single-step).
  Will revisit if rescan ledger shows the cost.
- **Per-pack binding vocabularies.** The slot vocabularies are currently
  module-internal closed sets. Whether they migrate into `language_packs/`
  (parallel to `en_units_v1` / `en_core_relations_v1`) is a question for
  0137.A.
- **Telemetry.** Whether `BindingProof.replay_digest` enters the
  TurnEvent telemetry sink (ADR-0040) on the cognition runtime, or stays
  local to the math eval lane. Probably the latter for now; cognition
  runtime is not consuming math problems on the hot path.

---

## Consequences

- The S.x corridor's micro-extension treadmill is paused. The G.x
  decision applies again: each unlock should advance the architecture,
  not the per-case admission count.
- The short-circuit paths in `parse_and_solve` are explicitly transient.
  Their existence is a debt that 0137.B and 0137.C pay down.
- The 23/50 context-filler cases gain a typed representation
  (`ContextFrame`) for the first time, even though they still don't
  admit. That representation is what later phases (S.4 coreference,
  ADR-0137.F new unlocks) require to ground references like "he", "the
  match", "her grandfather".
- The forward-only parser topology is preserved as a substrate; the
  binding pass is a single additional control-flow stage. This is the
  smallest possible change that converts a forward pipeline into a
  bounded retrospective one without violating CORE's refusal-first
  discipline.

---

## What this ADR is not

- Not a code change. No `generate/binding/` module exists at merge time.
- Not a license to add semantic guessing under another name. Every term
  in this document — `DeferredCandidate`, `BindingProof`, `ContextFrame`
  — has a closed slot vocabulary or a deterministic construction rule.
- Not a replacement for the verifier. The verifier still runs on the
  promoted-candidate graph; the binding layer feeds it, does not bypass
  it.
- Not in conflict with CLAUDE.md. The binding layer is exactly the
  shape of "comprehend → recall → think" the End Goal section names:
  hold partial structure, bind later evidence, solve deterministically,
  replay byte-equal.
