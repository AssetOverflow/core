# ADR-0137 — Retrospective Binding Layer (Subsumption Scope)

**Status:** Draft (design-only)
**Date:** 2026-05-23
**Parent:** [ADR-0136](./ADR-0136-statement-layer-corridor.md)
**Depends on:** [ADR-0136.S.2-post-rescan](./ADR-0136.S2-post-rescan.md)

> **Scope note.** This ADR's earlier draft framed retrospective binding
> as the next unlock vehicle for GSM8K admissions, justified by the
> v1 taxonomy's 23/50 `context_filler` dominance. The post-S.2 rescan
> (`refusal_taxonomy_v2.json`) collapsed that count to **3/50**: S.1/S.2's
> statement-layer regex extensions resolved 18 context-filler cases as
> collateral, exposing the next structural barrier in each.
>
> The new top barriers (`compound_statement: 6`, `novel_initial_form: 5`,
> `novel_initial_verb: 4`, `compound_comparative: 3`, `fraction_operand:
> 3`) are statement-layer parser problems, not cross-sentence binding
> problems. The S.x corridor — not retrospective binding — is the right
> vehicle for new admissions.
>
> **This ADR is therefore narrowed to subsumption-only.** It exists to
> pay down the architectural debt of the S.1/S.2 short-circuit paths,
> not to claim new admissions.

---

## Context

S.1 and S.2 introduced short-circuit paths in `parse_and_solve` that
bypass graph construction for two closed shapes: capacity/earnings
rates (S.1) and conditional-op questions (S.2). They were correct as
tactical bridges and delivered three current admissions (`0014`, `0018`,
`0042`), `wrong == 0`. They are wrong as a long-term architecture: each
future `S.x` faces a "graph path or short-circuit?" choice with no
principled answer, and the runner integration (canonical
`evals/gsm8k_math/runner.py` asserts `selected_graph is not None` on
admission and currently cannot score short-circuit admissions) already
shows the rot starting.

The honest justification for this ADR is **architectural cleanup, not
case-count leverage**:

- Parallel admission paths multiply. Each adds a place future readers
  must check when reasoning about correctness.
- Short-circuits skip the verifier and the trace machinery, leaving
  admitted answers without the same provenance as graph-path
  admissions.
- The rescan v2 report.json staleness is a concrete symptom: the
  canonical runner can no longer faithfully measure the system because
  the short-circuits are invisible to it.

Subsuming both short-circuits into a single deterministic binding pass
re-unifies the admission topology and restores the canonical runner's
ability to score what it sees.

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
       extractors (new) for the two short-circuit shapes only
     → CandidateInitial[]  +  CandidateOperation[]  +  CandidateUnknown[]
       +  DeferredCandidate[]
     → binding pass: each DeferredCandidate becomes a promoted
       (CandidateInitial | CandidateOperation) if and only if a
       BindingProof can be constructed from later-sentence evidence
     → second pass (after binding): existing Cartesian product enumeration
       over the *unified* candidate set
     → existing decision rule → answer | refuse
```

The binding pass is the only new control-flow stage. Everything downstream
(graph construction, solve, decision rule, verifier) is unchanged.
Promoted candidates are byte-indistinguishable from first-pass candidates.

### 2. Subsumption of S.1/S.2 short-circuits (the entire ADR)

**Directive.** Every current short-circuit admission must be re-derivable
as a `(DeferredCandidate, evidence, BindingProof)` triple. Short-circuits
are kept only as regression fixtures during the transition phase, and
**deleted** in the same PR that lands the corresponding deferred-kind.

The three current admissions map cleanly:

- **0014** (S.1 capacity) — `DeferredCandidate.RateLike` from the
  capacity-rate statement, bound by the question's duration evidence.
- **0018** (S.1 capacity, post-S.0 classifier) — same shape, after the
  context-filler classifier already drops the opening sentence.
- **0042** (S.2 conditional-op) — `DeferredCandidate.MutationLike` from
  the conditional question, bound by the matching `(entity, unit)`
  initial-state evidence.

No third kind is introduced by this ADR. `partition_like`,
`fractional_like`, `anchor_like` and the rest of the rescan-v2 barrier
vocabulary stay in S.x territory.

### 3. S.x is the actual unlock path (and we say so plainly)

The post-rescan ledger makes the cost/benefit explicit. S.1 and S.2 each
shipped ~150 lines of regex + one short-circuit and produced one direct
admission plus ~9 collateral context-filler resolutions. That return
profile beats anything retrospective binding would produce against the
v2 ledger — there are not enough cross-sentence-binding-shaped problems
remaining to justify it as the unlock vehicle.

S.3 (`feat/adr-0136-s3-compound-initial-mutation`) ships in parallel
with the implementation phases of this ADR. They do not block each
other. S.3 produces new admissions; this ADR cleans up architecture.

---

## Concrete type shapes

All shapes are frozen, slotted dataclasses; immutable per CLAUDE.md.
All live under a new module `generate/binding/` to keep the surface
clean.

### `DeferredCandidate`

A typed candidate whose grammar matched a recognized partial shape but
which did **not** ground its full slot set during the first pass.

```python
DeferredKind = Literal[
    "rate_like",       # subsumes S.1 capacity/earnings statement+question
    "mutation_like",   # subsumes S.2 conditional-op question
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

Two kinds only. Adding a third kind requires a follow-up ADR.

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

### `BindingPassResult`

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
the binding layer.

---

## Non-negotiables

1. **No `BindingProof` → no promotion.** A deferred candidate that
   cannot construct a complete proof from later evidence is dropped,
   not refused, not best-effort-solved. Refusal of the whole problem
   only happens through the existing decision rule.

2. **No guessing.** A binding is admitted only when the open slots are
   uniquely closed by exactly one evidence sentence. Ambiguous
   bindings refuse the binding, not pick one.

3. **No hidden LLM fallback.** The binding layer is pure deterministic
   matching against closed slot vocabularies.

4. **`wrong == 0` remains a hard CI gate** — across the binding eval
   lane and the GSM8K probe.

5. **No solver/graph/verifier changes.** The binding layer feeds the
   existing graph machinery promoted candidates indistinguishable from
   first-pass candidates.

6. **Determinism.** All binding passes are pure functions over the
   first-pass candidate set. Same input → same `BindingPassResult`
   bytes, same `replay_digest`s.

7. **Subsumption is the only admission claim.** This ADR does not
   claim any new GSM8K admissions. Admission counts are unchanged
   pre/post implementation: `{0014, 0018, 0042}`.

---

## Probe set

The probe set is **subsumption-only**:

| Case | Current path | Post-0137 path |
|---|---|---|
| 0014 | S.1 short-circuit | `rate_like` deferred + question evidence |
| 0018 | S.0 + S.1 short-circuit | same, after context-frame skip |
| 0042 | S.2 short-circuit | `mutation_like` deferred + initial-state evidence |

Plus two **negative probes** to confirm the binding layer doesn't
over-admit:

- **gsm8k-0005** — "decrease to 3/4 of its temperature." Self-reference;
  no later sentence can close a `rate_like` binding. Must continue to
  refuse.
- **gsm8k-0039** — "everyone ate too much food and gained weight." No
  numeric token. Must continue to refuse (context-filler unchanged).

Cases from earlier drafts (0034, 0021, 0003, 0029, 0001, 0022, 0050)
are dropped. They are statement-layer parser gaps and belong in S.x —
not in retrospective binding.

The probe lane file (`evals/math_capability_axes/RB1_subsumption/v1/cases.jsonl`)
is sized to ≥10 (3 subsumption + 2 negative + ≥5 axis cases for each
deferred-kind to exercise the slot vocabularies without inheriting from
GSM8K).

---

## Phased rollout

**One branch per phase**, sequential. The 2026-05-23 worktree-race
lesson stands.

| Phase | Deliverable | Branch |
|---|---|---|
| 0137.D | This ADR | `docs/adr-0137-retrospective-binding` (this PR) |
| 0137.A | `generate/binding/{types,context_frame}.py` + tests for the type machinery alone | `feat/adr-0137-binding-types` |
| 0137.B | `rate_like` kind + binding pass + 0014/0018 subsumption; S.1 short-circuit deleted in same PR | `feat/adr-0137-rate-like-subsume-s1` |
| 0137.C | `mutation_like` kind + 0042 subsumption; S.2 short-circuit deleted in same PR | `feat/adr-0137-mutation-like-subsume-s2` |
| 0137.E | Eval lane `RB1_subsumption` + probe set | `feat/adr-0137-rb1-lane` |

The previous draft listed a phase F for new admissions. It is
**removed**. Adding a third deferred-kind beyond `rate_like` and
`mutation_like` requires a follow-up ADR, not a phase of this one.

Each phase is its own PR. Each must hold `wrong == 0`, preserve the
existing B3 lane, and not change the GSM8K admission set
(`{0014, 0018, 0042}` exactly, pre and post).

---

## Consequences

- The short-circuit paths in `parse_and_solve` are explicitly transient.
  Their existence is a debt paid down by 0137.B and 0137.C.
- The canonical `evals/gsm8k_math/runner.py` regains its ability to score
  every admission (promoted candidates build real graphs that pass the
  `selected_graph is not None` check). The stale `report.json` problem
  goes away.
- The forward-only parser topology is preserved as a substrate; the
  binding pass is a single additional control-flow stage.
- `DeferredCandidate` / `BindingProof` are seeded with two kinds. Future
  ADRs may add kinds (`partition_like`, `fractional_like`, `anchor_like`,
  …), but only when a corresponding S.x cluster proves it needs deferred
  evidence rather than a richer first-pass extractor.
- S.x continues as the actual unlock vehicle. ADR-0137 and S.3+ are
  parallel, not competing.

---

## What this ADR is not

- Not a code change. No `generate/binding/` module exists at merge time.
- Not a license to add semantic guessing under another name.
- Not a replacement for the verifier.
- **Not a new-admissions vehicle.** Any PR that claims a new GSM8K
  admission under an ADR-0137 phase number is misclassified — it
  belongs under S.x.
- Not in conflict with CLAUDE.md. The binding layer is the shape of
  "comprehend → recall → think" the End Goal section names: hold
  partial structure, bind later evidence, solve deterministically,
  replay byte-equal.
