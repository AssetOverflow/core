# ADR-0167 — Follow-ups Queue

**Date opened:** 2026-05-27 (end of Wave 3)
**Parent:** [ADR-0167](../decisions/ADR-0167-audit-as-teaching-evidence.md)
**Companion:** [SESSION-2026-05-27](../decisions/SESSION-2026-05-27-adr-0167-parallel-dispatch.md)

The LexicalClaim slice landed clean (W1-A → W2-A/B/C/D → W3-A merged
2026-05-27). This file captures the named follow-ups that surfaced
during the wave and were deliberately deferred so the slice could
converge. The next operator picking up ADR-0167 work should walk this
queue top-down and decide which item the project's current capability
gate actually needs.

Each item: scope, why deferred, where the breadcrumbs live, and the
acceptance criterion that would close it.

---

## 1. Frame-opener sub-types (FrameClaim / CompositionClaim / ReferenceClaim / SlotClaim)

**Scope.** Four additional ratification handlers, one per remaining
sub-type in `SUB_TYPE_FOR_OPERATOR`:

| Sub-type | Maps from | Ratification primitive |
|---|---|---|
| `FrameClaim` | `pre_frame_filler_sentence`, `multi_subject_sentence` | Verb-category reclassification |
| `CompositionClaim` | `multi_quantity_composition`, `quantity_extraction` | Frame-split rule |
| `ReferenceClaim` | `pronoun_resolution` | Anaphora-resolution entry |
| `SlotClaim` | `question_frame_slot`, `unit_binding`, `question_target_slot`, `descriptive_frame_question` | Slot-completion table entry |

**Why deferred.** ADR-0167 §"Proposed sub-type set" explicitly chose
LexicalClaim-first because it is the lowest-risk surface (drain_token
additions cannot create wrong admissions without also passing graph
completeness). The other four touch frame-opener decisions, anaphora,
or slot bindings — each is a new admission path multiplying the
`wrong=0` surface area, and each needs its own scoping ADR with the
six open questions from ADR-0167 §"Open questions" answered for that
sub-type's mechanics.

**Where breadcrumbs live.**
- `teaching/math_evidence.py::SUB_TYPE_FOR_OPERATOR` — already maps
  the operator labels; no schema change needed
- `teaching/math_lexical_ratification.py` — the template for what a
  sub-type handler looks like (preconditions, receipt, idempotency,
  hazard pins)
- `tests/test_math_lexical_ratification.py::test_rejects_non_lexical_sub_type`
  — pins that non-lexical claims currently raise `WrongClaimSubType`;
  each new handler retires its corresponding rejection

**Acceptance.** Each new sub-type ships as an ADR (likely ADR-0168,
ADR-0169, ...) followed by a wave of PRs analogous to ADR-0167's W2-D.
Each handler must:
- declare its own `SAFE_CATEGORIES` allowlist analogous to W2-D's
  `{"drain_token"}`
- preserve the case 0050 hazard pin
- carry the same idempotency / evidence-tampering / unknown-category
  guards W2-D established
- pass an e2e ratification → row-movement test analogous to
  `test_lexical_ratification_advances_unknown_word_row`

**Priority hint.** FrameClaim is the highest-leverage next sub-type
(9 cases in the current taxonomy under `pre_frame_filler_sentence`),
but also the riskiest — frame-opener miscategorisation is exactly the
case 0050 hazard. CompositionClaim (8+11 cases) is the next-highest
count, also high-risk. ReferenceClaim (3 cases) and SlotClaim (smaller
buckets) are lower-leverage but structurally simpler.

---

## 2. Partition test architectural fix

**Status.** Closed by `fix/adr-0167-partition-test-invariant`.

The original `git status --porcelain` runtime assertion was retired.
Partition invariants are now expressed behaviorally through:

- serialization discrimination (`domain` omitted for cognition,
  explicit for math)
- deterministic canonical-byte divergence between cognition and math
  candidates
- existing cognition regression suites already exercised in CI

This removes the structurally brittle requirement that every future
ADR-0167 PR edit a filename allowlist merely to add a new evidence test.
The partition guarantee now lives at the protocol surface instead of
repository working-tree state.

---

## 3. Pre-existing main test failures (unrelated to ADR-0167)

**Status update.** The two failures originally flagged during W3-A were
later traced to a real wrong=0 hazard and fixed in #359 rather than
being treated as unrelated noise.

The relevant fix path:
- recognized-but-uninjectable statements now refuse instead of silently
  admitting partial graphs
- audit taxonomy updated accordingly
- regression coverage added for recognizer skip-only fallback behavior

Retain this section as historical context only; do not reopen unless a
fresh regression appears.

---

## 4. Workbench v1 — math candidate rendering

**Scope.** Make the read-only operator UI (ADR-0160/0162) render
`MathReaderRefusalEvidence` candidates alongside cognition
`DiscoveryCandidate` records.

**Why deferred.** ADR-0167 §"Open questions Q4" explicitly out-of-scope.
The LexicalClaim slice ships the ratification handler but no UI to
trigger ratification through — today, an operator would call
`apply_lexical_claim()` from a Python REPL.

**Where breadcrumbs live.**
- ADR-0160 (Core Workbench v1)
- ADR-0162 (Workbench Design System)
- W-029 (proposal queue) — closest existing surface
- W-031 (replay theater) — replay primitive that math evidence
  records inherit through ADR-0057

**Acceptance.** A workbench panel that lists pending
`MathReaderRefusalEvidence` candidates with sub-type, claim signature,
recognized terms, refusal context, and a ratify-action that calls
`apply_lexical_claim()` (or its sub-type-specific successor) with an
operator-supplied reviewer tag and category.

---

## 5. Cross-domain partition risks (from Gemini's W2-C audit)

Two specific code paths Gemini flagged in
`docs/handoff/ADR-0167-W2C-cross-domain-audit.md` as needing partition
discrimination:

### 5a. Contemplation pack indexing

**Scope.** `teaching/contemplation.py::contemplate()` uses hardcoded
cognition pack and corpus indexes (`_pack_index` and `_corpus_index`).
Future math-domain candidates would silently get cognition-domain
lookups.

**Acceptance.** Pack and corpus indexes parameterised by
`candidate.domain` — cognition candidates look up cognition packs,
math candidates look up math packs (currently `en_core_math_v1`).
Tests must exercise both paths.

### 5b. Replay gate default

**Scope.** `teaching/proposals.py` defaults its replay gate to
cognition's. Proposing math/admissibility candidates requires passing
`run_admissibility_replay_gate` explicitly to prevent false rejections.

**Acceptance.** Either the replay gate is selected by
`proposal.domain`, or the cognition default is made explicit and math
proposals are required to declare their gate. Decision goes in
ADR-0168 (or wherever the first non-lexical sub-type ADR lands —
that handler will be the first real exerciser of the proposals path
for math).

---

## 6. HolonomyAlignmentCase — structural-vs-blend convergence isolation

**Scope.** Determine whether the existing
`tests/test_alignment_graph.py::test_holonomy_alignment_case_positive_closer_than_negative`
proves *structurally-derived* cross-language convergence or only proves
*endpoint similarity under the mount-time blend*.

**Why deferred.** The proof obligation is executed today — the test
asserts that an aligned Logos clause produces nearer holonomies across
English/Hebrew/Greek than a misaligned negative triple. That clears the
schema's nominal claim. But the test does not distinguish two possible
explanations for the convergence:

1. **Structural.** The Hebrew tri-consonantal root rotors and Greek
   case-last orientation rotations produce versors that genuinely
   land in the same regions of the manifold because the morphology
   operators encode equivalent semantic structure.
2. **Blend-induced.** `_apply_mounted_primary_domain_resonance`
   (`language_packs/compiler.py:558`) nudges Hebrew/Greek versors
   toward an English prototype at 40% blend, and the test passes
   because both packs have been pulled close to the English anchor
   regardless of structural derivation.

If (2) is doing the work, the three-language architecture is a *claim*
that English-anchored geometric averaging produces the right endpoints,
not a *proof* that the depth packs are structurally independent
operators converging coherently with the articulation surface.

**Where breadcrumbs live.**
- `language_packs/compiler.py::_apply_mounted_primary_domain_resonance`
  — the architectural-invariant comment names this gap explicitly and
  references this section
- `tests/test_alignment_graph.py:73` — the existing positive-closer-
  than-negative assertion
- `language_packs/schema.py::HolonomyAlignmentCase` — the schema type
  whose nominal contract is "proves structural divergence with
  coherent convergence"

**Acceptance.** One of:
- **(a) Ablation test.** A test that runs the holonomy proof with
  `_apply_mounted_primary_domain_resonance` disabled (or with the
  blend factor set to 0.0) and asserts that the positive-closer-than-
  negative relation still holds. This would prove (1) and retire the
  concern.
- **(b) Reframe the claim.** If the ablation fails, document
  explicitly that cross-language convergence depends on the
  mount-time blend, and update `HolonomyAlignmentCase`'s contract to
  reflect what it actually proves (endpoint similarity under blend,
  not structural-derivation equivalence). Honest documentation of a
  weaker property beats a stronger claim that the test can't support.

**Priority.** Low-urgency, high-information. Not blocking any current
capability gate. Worth picking up whenever someone next touches the
language-pack architecture — the comment at the convergence-decision
site is the trip-wire.

Per CLAUDE.md §"Schema-Defined Proof Obligations" — this is the
prototypical example of a schema-defined obligation that is executed
but where the test may not meaningfully fail under the violation it is
written to catch.

---

## Sequencing recommendation

For the operator picking this up next:

1. **First**, decide which of the four frame-opener sub-types (§1) the
   next capability gate actually demands. ADR-0166 still gates this —
   the three-question test must pass for whichever sub-type is chosen.
2. **Next**, parameterise contemplation pack indexing and replay-gate
   selection by `candidate.domain` before the second sub-type lands.
3. **Then**, begin ADR-0168 (likely FrameClaim-first) with explicit
   wrong=0 hazard pins carried forward from case 0050.
4. **Finally**, workbench rendering can follow once a second sub-type
   actually exists.

No timelines. Order is by leverage, not calendar.
