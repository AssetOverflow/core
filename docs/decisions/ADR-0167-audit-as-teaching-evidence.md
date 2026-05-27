# ADR-0167 — Audit-as-Teaching-Evidence (Math Reader → Contemplation)

**Status:** Proposed (scoping ADR; no code in this PR)
**Date:** 2026-05-27
**Author:** Shay
**Parent thesis:** [[thesis-decoding-not-generating]]
**Parent brief:** [BRIEF-11D candidate E](./BRIEF-11D-next-capability-proposal.md)
**Related:** ADR-0150/0152/0155/0161 (HITL + contemplation), ADR-0164 (reader),
ADR-0166 (measurement-capability sequencing), ADR-0057 (teaching-chain proposal)

---

## Context

The Brief 11B audit infrastructure (`generate/comprehension/audit.py`,
`evals/gsm8k_math/train_sample/v1/audit_brief_11.json`) produces a labelled
refusal taxonomy per case: every `ReaderRefusal` is decorated with a
`missing_operator` label (`pre_frame_filler_sentence`,
`multi_quantity_composition`, `unit_binding`, `pronoun_resolution`, etc.) and a
typed `AuditRow` carrying `recognized_terms`, `skipped_frame`,
`refusal_reason`, and `refusal_detail`.

Today this evidence is **terminal**. A refusal labels the failure, the audit
artifact serialises it, the operator reads it. There is no path from a
labelled refusal back into the engine's learning loop.

CORE already has a learning loop: the contemplation/HITL teaching corridor
(ADR-0150/0152/0155/0161). Today it produces `DiscoveryCandidate`s from the
*cognition* lane via `teaching/contemplation.py`. Each candidate carries a
polarity, semantic domains, evidence, and sub-questions; ratified candidates
become `TeachingChainProposal`s (ADR-0057) that extend the active teaching
corpora.

The math reader does not feed this pipeline. Its refusals discard.

## Decision

Route math-reader audit rows into the contemplation candidates pipeline as a
new candidate source: **`MathReaderRefusalEvidence`**.

The integration is *evidence-only*: an audit row becomes a candidate the
operator may ratify into a teaching chain. The chain itself is what updates
the engine's behaviour. The audit row never directly mutates a pack, a
lexicon, the reader, or the solver.

This preserves the project thesis: the engine is not adding stored items
hoping to retrieve them; it is surfacing what it failed to find in a shape
the operator can teach against.

## Why this is not a refusal-class dispatch table

Tempting alternative: `missing_operator → specialised handler`. Reject:

1. It is library-of-handlers — the same anti-pattern regex sentence templates
   represented. ADR-0164 already retired that surface.
2. Every specialised handler is a new admission path, multiplying the
   `wrong=0` surface area. Brief 11 §"correct-count greed" applies.
3. Handlers ossify the taxonomy. The taxonomy should be input to operator
   judgement, not branch points in production code.

The dispatch table imagines the engine *resolving* the refusal in-flight.
This ADR insists the engine *records* the refusal and lets the operator
resolve it deliberately, via the existing teaching corridor.

## Why this requires an ADR before code

Cognition teaching chains encode *semantic-domain propositions*: e.g.
"`cognition.attention.is_a.cognition.faculty`". They are structurally simple:
subject, predicate, object, polarity.

Math-domain teaching chains would have to encode something different. The
audit taxonomy ranges over five distinct *kinds* of teachable claim:

1. **Lexical** — "this surface form belongs to category X"
   (`lexicon_entry`, `compound_numeric_literal`, `compound_time_literal`)
2. **Frame-classifying** — "this verb opens / does not open a frame of kind
   K" (`pre_frame_filler_sentence`)
3. **Structural** — "this sentence composes N possessions/operations of
   different kinds" (`multi_quantity_composition`)
4. **Reference-resolving** — "this pronoun in this context refers to entity
   E" (`pronoun_resolution`)
5. **Slot-completing** — "this question-target slot is filled by U"
   (`question_frame_slot`, `unit_binding`)

These are not all the same shape. A single uniform `MathTeachingChain` would
either flatten them lossily, or require five sub-types. The ADR must commit
to one of:

- **5 sub-types** with explicit type tags and per-type ratification rules
- **A graph schema** (closer to `PropositionGraph`) that subsumes all five
- **A subset-first scope** (lexical only, defer the other four)

Each choice has different replay/serialisation/manifest-checksum
consequences. None can be inferred from the cognition side.

## Proposed sub-type set (provisional, for review)

If the ADR adopts the sub-types path:

| Sub-type            | Maps from                      | Ratification primitive              |
|---------------------|--------------------------------|-------------------------------------|
| `LexicalClaim`      | `lexicon_entry`, compounds     | Pack entry add (lemma + category)   |
| `FrameClaim`        | `pre_frame_filler_sentence`    | Verb-category reclassification      |
| `CompositionClaim`  | `multi_quantity_composition`   | Frame-split rule                    |
| `ReferenceClaim`    | `pronoun_resolution`           | Anaphora-resolution entry           |
| `SlotClaim`         | `question_frame_slot`, `unit_binding` | Slot-completion table entry  |

`LexicalClaim` is the smallest, lowest-risk surface. Adopting it first
proves the wiring without committing the harder sub-types.

## Hard invariants this ADR must preserve

- **`wrong == 0`**. The audit row never directly admits a math fact. Only
  ratification through the existing HITL queue can change runtime behaviour.
- **Determinism**. Audit-derived candidates must be byte-identical across
  reruns (same case → same candidate → same hash). The current audit already
  satisfies this via frozen-dataclass state + canonical bytes.
- **Replay equivalence** (ADR-0057). A ratified math teaching chain must
  replay deterministically alongside cognition chains. The trace-hash
  contract extends to math chains.
- **Pack mutation proposal-only**. Ratification proposes pack additions;
  applying them is a separate, reviewed step (CLAUDE.md §"Teaching Safety").
- **No new eval lanes** (ADR-0166). This ADR builds a capability; the
  existing audit + cognition lanes validate it.

## Open questions (must be resolved in the implementation ADR)

1. **Granularity of de-duplication**. Two GSM8K cases produce the same
   `lexicon_entry` claim for `crayons`. Are they merged into one candidate
   with two evidence rows, or kept as two candidates? (Likely: merged, by
   normalised claim signature.)
2. **Provenance schema**. A `MathReaderRefusalEvidence` candidate must
   carry: case_id, sentence_index, token_index, refusal_reason, audit_row
   hash. Decide canonical-bytes layout before any serialisation lands.
3. **Cross-domain leakage**. Cognition chains and math chains share the
   contemplation queue. Must they be partitioned? (Likely: yes, with a
   `domain` discriminator on the candidate.)
4. **Ratification UX**. Workbench v1 (ADR-0160) does not render math
   candidates today. Out of scope for this ADR; cite as follow-up.
5. **Failure of ratification**. If the operator rejects a candidate, the
   audit row remains. Does the next refusal of the same shape re-queue it?
   (Likely: yes, with a "previously rejected" annotation; no silent
   suppression.)
6. **First-write target**. `LexicalClaim` ratification writes to
   `language_packs/data/en_core_math_v1/lexicon/*.jsonl`. Confirm the
   loader's per-category source-file path is the canonical mutation site,
   not the compiled `lexicon.jsonl`.

## Sequencing

Per ADR-0166's three-question test:

- **Q1 — Capability**: A new candidate source feeding the existing
  contemplation queue. Reader, audit, and contemplation already exist on
  main; this ADR specifies the wire between them.
- **Q2 — Lane**: The existing
  `evals/gsm8k_math/train_sample/v1/audit_brief_11.json` artifact is the
  capture surface. Existing cognition-lane teaching tests validate the
  ratification → replay path; the math wire reuses that contract.
- **Q3 — Invariant**: `wrong == 0` (no direct admission);
  determinism (frozen state + canonical bytes); replay equivalence
  (ADR-0057). All three are inherited from existing mechanisms.

Three-question test **passes for the ADR**. Implementation passes only
when the open questions above are answered with `LexicalClaim`-first scope.

## Relationship to Brief 11D

This is the speculative **Candidate E** that the 11D doc did not
enumerate. It does not displace Candidate A (continued GSM8K operator
closure). They are complementary:

- **Candidate A** ships the per-bottleneck closure fixes (the
  `lexicon_entry` PR #348 is the first sub-PR).
- **Candidate E** (this ADR) makes the closure fixes *operator-ratifiable
  from the audit* rather than hand-written PRs.

A reasonable ordering: A's first 1–2 PRs land manually (proves the
closure path is real); then E ships the ADR + `LexicalClaim` wiring so
the *third* and onward closure PRs are operator-driven through the
teaching corridor rather than hand-coded.

This is the moment the engine starts teaching itself in the domain — the
loop your thesis demands.

## Decision (pending operator ratification of this ADR)

> Math-reader refusals become teaching-corridor evidence via a new
> `MathReaderRefusalEvidence` candidate source. The audit taxonomy is the
> queue of teachable moments. The engine does not resolve refusals
> in-flight; it surfaces them in a shape the operator can ratify into a
> teaching chain that the existing pack/lexicon/contemplation machinery
> already knows how to absorb.
>
> Scope first to `LexicalClaim` (the lowest-risk, highest-count
> sub-type). Defer the four harder sub-types until the lexical wire is
> proven.

Reopening this decision requires either:
1. The cognition teaching corridor's invariants weaken (no longer a stable
   substrate for the math wire), or
2. A simpler design supersedes — e.g. a graph schema that subsumes all
   five sub-types without sub-typing cost.

---

## Cross-references

- [BRIEF-11D](./BRIEF-11D-next-capability-proposal.md) — strategic
  recommendation this ADR extends
- [ADR-0166](./ADR-0166-measurement-capability-sequencing.md) — gating
  rule answered above
- [ADR-0164](./ADR-0164-incremental-comprehension-reader.md) — the
  reader whose refusals feed this wire
- [ADR-0150 / 0152 / 0155 / 0161] — the teaching corridor this wire
  plugs into
- [ADR-0057](./ADR-0057-teaching-chain-proposal.md) — the
  replay-equivalence contract math chains must inherit
- `evals/gsm8k_math/train_sample/v1/audit_brief_11.json` — the data
  source the wire consumes
