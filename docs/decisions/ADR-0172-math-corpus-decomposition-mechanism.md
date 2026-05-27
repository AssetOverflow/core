# ADR-0172 — Math-Domain Corpus-Decomposition Mechanism (Learning-Arc Analog)

**Status:** Proposed (scoping ADR; no runtime change in this PR)
**Date:** 2026-05-27
**Author:** Shay
**Parent:** ADR-0167 (audit-as-teaching-evidence)
**Related:** ADR-0055/0056/0057 (cognition contemplation/teaching-chain
proposal corridor), ADR-0168 (FrameClaim), ADR-0169 (CompositionClaim
— reserved), ADR-0170 (injector contract widening), Learning Arc
milestone 2026-05-25
**Gating rule:** [ADR-0166](./ADR-0166-measurement-capability-sequencing.md)

---

## Context

The cognition learning arc (`teaching/contemplation.py` +
`teaching/proposals.py`, completed 2026-05-25) closed this loop:

```text
refusal → audit row → contemplation decomposes corpus →
engine PROPOSES teaching chain → operator ratifies → corpus extends →
next session admits what was previously refused
```

The load-bearing word is **PROPOSES**. The engine reads its own
cognition corpus, decomposes it into discovery candidates with
polarity / domains / evidence / sub-questions, and emits
`TeachingChainProposal` records for HITL review. The operator's
cognitive load is *review*, not *invention*. That was the moment the
project shifted from "engine refuses + operator authors" to "engine
teaches itself through reviewed correction."

The math domain has the same shape of data:

- `evals/gsm8k_math/train_sample/v1/audit_brief_11.json` — 47 refusals
  grouped by `refusal_reason × missing_operator`
- Structural commonalities are visible in the taxonomy: 21 cases hit
  `discrete_count_statement` with similar narrowness-violation
  patterns; 9 hit `pre_frame_filler_sentence`; 8 hit
  `multi_quantity_composition`; etc.
- ADR-0167 wires refusal evidence into the existing contemplation
  corridor as `MathReaderRefusalEvidence`

What math does **not** have is the analog of cognition's
contemplation decomposition: a mechanism that reads the refusal corpus
and emits *structural proposals* (matcher extensions, injector
sub-shapes, possession-verb additions, narrowness-rule relaxations).

Today the operator does this work by hand: read `audit_brief_11.md`,
identify the structural commonality across N refusals, scope the
matcher/injector extension, file a focused PR. That works but it's
operator-as-decomposer, not engine-as-decomposer.

## Decision — two tiers

Specify a math-domain corpus-decomposition mechanism that operates at
**two distinct rungs** of engine-developed structural understanding.

### Tier 1 — Extensional contemplation (rule-proposal)

Produce **`MathReaderRefusalShapeProposal`** records from the audit
corpus. Each proposal:

- Names a structural commonality across ≥2 refusal cases
- Names the candidate mechanism change that would resolve the
  commonality (matcher extension, injector sub-shape, vocabulary
  addition)
- Carries the audit-row evidence pointers (case IDs, refusal reasons,
  parsed_anchors)
- Routes to HITL review through the existing
  `teaching/proposals.py` ratification flow
- Is evidence-only: never auto-applied; ratification requires explicit
  operator action

This is the math-domain analog of cognition's
`teaching/contemplation.py::contemplate()`. It does not duplicate the
cognition mechanism; it sits alongside it, partitioned by
`candidate.domain == "math"` (the discriminator W2-C shipped in #351).

Tier 1 emits *rules*: "extend possession_verbs to include `collected`",
"add `crayons` to observed_counted_nouns", "widen DCS clause-split
exception for trailing 'of'-clauses." Each proposal materializes as
discrete code/pack changes after HITL approval.

### Tier 2 — Intensional contemplation (inference)

Produce **`MathReaderInferenceProposal`** records that name a *learned
structural equivalence* across surface variations — not an explicit
rule, but a contemplated recognition that N sentences with surface
differences carry the same canonical proposition structure.

For example, Tier 2 would surface a proposal like:

```text
inference_id: math.inferential.acquisition_to_initial_state
structural_claim:
  "<ProperNoun> <verb-of-coming-to-possess> <count> <noun>"
  is canonically equivalent to
  "<ProperNoun> has <count> <noun>"
  for the purpose of initial-state extraction.
evidence_pointers: (5+ refusal cases across `collected`, `acquired`,
                    `received`, `bought` — verb varies, structure is
                    invariant)
ratification_effect:
  Add an *inferential bridge* in the reader/injector such that any
  sentence matching the structural claim canonicalizes to the
  reference form before extraction — without listing the specific
  verbs.
wrong_zero_assertion:
  Canonicalization preserves admissibility gates downstream; the
  bridge only changes what reaches the gate, not whether the gate
  fires. Multi-branch decision rule still refuses on disagreement
  between bridged and unbridged extraction.
```

Tier 2 is qualitatively different from Tier 1: it operates on
*structural equivalence classes* rather than on enumerable rules. It
is what makes capability scale — instead of authoring N FrameClaim
handlers for N verb categories, the engine recognizes the
verb-category dimension itself as a structural axis and proposes a
canonicalization bridge that handles the whole axis at once.

This is what the project thesis ("**decoding** ... capacity to find,
comprehend, and **rationalize**") asks for. Tier 2 IS rationalization:
recognizing canonical form within surface variation.

### Tier 2 test-and-learn loop — two-arm confirmation

Tier 2 does not emit raw inferential claims. It emits **claims paired
with empirical test evidence**, deterministically generated by the
engine before HITL review. The test has **two arms** — both must hold
for a proposal to surface to the operator:

**Arm 1 — Negative check (held-out wrong=0):** does the hypothesis
admit cases the engine has never seen *without* raising wrong>0?

**Arm 2 — Positive check (known-fact preservation):** does the
hypothesis change ANY currently-correct outcome?  Cases that admit
correctly today MUST continue to admit with the same answer under
the bridged extraction.  A hypothesis that would alter a known-good
outcome — even to a different-but-defensible value — is rejected.
The engine confirms against prior solutions, not just against unseen
data.

This is the mechanism that lets the engine *confirm against known
facts*.  ADR-0057's replay-equivalence contract is the inherited
substrate: the engine's inferential bridges must pass the same
replay-equivalence check ratified teaching chains pass.

For each proposed `MathReaderInferenceProposal`:

1. **Hypothesis emission.** The decomposer surfaces a structural
   equivalence class from the refusal corpus.
2. **Test-set partition.**
   - *Held-out subset* (e.g. 30% of the refusal corpus) — reserved
     from the evidence pointers that formed the hypothesis.  Drives
     Arm 1.
   - *Known-good set* — every case currently in the admitted-with-
     correct-answer state across the canonical lanes.  Drives Arm 2.
3. **Inferential application.** The hypothesis is applied to both
   sets: bridged extraction → existing admissibility gates
   (`_initial_admissible`, `roundtrip_admissible`, multi-branch
   decision rule) → solver → verifier.
4. **Two-arm outcome scoring.**
   - **Arm 1 (held-out):**
     - Bridge admits cases at the same answer as ground-truth →
       positive evidence
     - Bridge admits cases at a different answer than ground-truth →
       **REJECTED INTERNALLY** (would raise wrong>0)
     - Bridge produces no admissions → neutral evidence
   - **Arm 2 (known-good):**
     - Every currently-correct case still correct under the bridge →
       PASS
     - Any currently-correct case changes answer (even to a
       defensible value) → **REJECTED INTERNALLY** (would violate
       replay-equivalence)
   - **Both arms must PASS or be neutral.**  Either arm rejecting →
     proposal does not reach HITL.
5. **Proposal-with-evidence emission.** The proposal carries the
   structural claim AND both arms' test results AND the
   replay-equivalence hash AND the case-by-case verdict tables.  HITL
   review verifies an empirically-tested hypothesis, not a bare claim.

The two-arm structure is what makes Tier 2 thesis-coherent.  The
engine isn't generating a hypothesis and asking the operator to bless
it — it is decoding a structural pattern, **testing against both
unseen refusals and prior known-good outcomes**, and presenting the
operator with the test results as part of the proposal.  The operator
adjudicates the *tests* + the *interpretation*, not a bare claim.

This is also the wrong=0 safety net for Tier 2: any inferential bridge
that produces a wrong admission in either arm is **rejected internally**
before reaching HITL.  The operator only ever sees proposals whose
*both* arms confirm.  Wrong>0 hazards cannot leak through Tier 2; nor
can replay-equivalence violations of prior ratified work.

### Why both tiers, not just Tier 2

Tier 1 is concrete and tractable today. Tier 2 requires Tier 1's
infrastructure (evidence pipeline, HITL queue, ratification handlers)
to land first. Cognition followed this pattern: explicit teaching
chains shipped before the contemplation-decomposer that proposes
them. The mechanism needs somewhere to *land*; that has to be built
first.

Tier 1 also produces real lift along the way — each ratified
proposal lifts GSM8K cases. Tier 2's lift is harder to predict and
more architecturally ambitious. Shipping Tier 1 first means the
project always has visible progress even if Tier 2 takes longer to
design.

## Why this is not already what ADR-0167 ships

ADR-0167 LexicalClaim (shipped) handles **one-word ratifications**:
the operator sees a `lexicon_entry` refusal and approves a pack
addition. The engine doesn't propose the word; the operator picks it.

FrameClaim (ADR-0168, queued) and CompositionClaim (ADR-0169,
reserved) handle **structural pattern ratifications** but still
require the operator to choose which pattern from the audit data.

ADR-0172 is the rung above: **the engine reads the audit corpus,
recognizes a structural pattern across N refusals, and proposes the
pattern itself.** The operator's role shifts from "find the pattern,
choose the category, ratify the claim" to "review the engine's
proposed pattern, accept or reject."

This is exactly the rung the cognition learning arc occupied when it
graduated from per-claim ratification to corpus-decomposition
proposal.

## Why this matters for capability

Without ADR-0172, every math sub-shape PR costs:
- Operator time to read 21 refusal reasons and find the commonality
- Operator design judgment to scope the matcher/injector extension
- One focused PR per sub-shape, hand-authored

With ADR-0172, the engine surfaces candidate sub-shapes from the
audit data. The operator reviews ~5 proposals per session instead of
authoring ~5 sub-shape PRs. The proposals carry their own evidence,
so review is structural verification rather than data archaeology.

This compounds: as the corpus grows (each refused case is a data
point), the proposal mechanism gets more signal. Cognition saw this
empirically — the learning arc accelerated after the first few
ratifications because the corpus had more structural redundancy for
the decomposer to recognize.

## Provisional `MathReaderRefusalShapeProposal` shape

```text
MathReaderRefusalShapeProposal:
  proposal_id: str  # deterministic hash of evidence + proposed change
  domain: Literal["math"]  # ADR-0167 W2-C discriminator
  shape_category: ShapeCategory  # which recognizer / refusal class
  structural_commonality: str  # human-readable description
  evidence_pointers: tuple[MathReaderRefusalEvidence, ...]  # ≥2 cases
  proposed_change_kind: Literal[
    "matcher_extension",     # widen narrowness rule
    "injector_sub_shape",    # new emission pattern in injector
    "vocabulary_addition",   # lexicon/pack entry (subsumes LexicalClaim)
    "frame_reclassification" # verb category change (subsumes FrameClaim)
  ]
  proposed_change_payload: object  # type-discriminated by kind
  wrong_zero_assertion: str  # explicit reasoning for why the change preserves wrong=0
  replay_equivalence_hash: str  # ADR-0057 contract
```

Each `proposed_change_kind` maps to a downstream ratification handler
(the W2-D-shaped artifacts ADR-0167 et seq. produce). The proposal
itself is purely descriptive — it does not modify anything.

## Six open questions (must resolve in implementation ADR/PR)

1. **Decomposition algorithm**: how does the engine recognize
   structural commonality? Naive approach: group audit rows by
   `(refusal_reason, missing_operator)` and emit one proposal per
   group above a minimum-evidence threshold (e.g. ≥3 cases). Deeper
   approach: cluster on extracted-anchor shape (e.g. all "proper
   noun + acquisition verb + integer + observed_noun" cases form one
   group regardless of which case_id they belong to).

   *Recommendation:* start naive. The cognition decomposer started
   that way too. Deeper clustering can ship later if the naive
   proposals don't carry enough signal.

2. **Minimum evidence threshold**: how many refusals must share a
   pattern before a proposal is emitted? Cognition uses 2+; that's
   probably right here too. Lower threshold = more noise; higher =
   misses real patterns.

3. **De-duplication**: how does the mechanism avoid re-proposing a
   pattern the operator already rejected? Cognition tracks rejected
   proposals; the same record needs to exist for math. Likely
   parallel to ADR-0167 W2-B's `claim_signature` mechanism.

4. **Wrong=0 evidence in the proposal**: each proposal must carry
   an explicit `wrong_zero_assertion` — a written claim about why
   the proposed change preserves the invariant. This is the
   structural analog of cognition's "polarity + evidence" fields.
   The operator's review focuses on validating this assertion.

5. **Cross-domain partition**: per ADR-0167 W2-C, the contemplation
   queue is partitioned by domain. ADR-0172 emits only `math`-domain
   proposals; the cognition contemplation continues to emit only
   `cognition`-domain proposals. The wire is parallel, not unified.

6. **Frequency**: when does the decomposer run? On every audit
   regeneration? On operator command? On a CLI lane (`core eval
   math-contemplation`)? Cognition runs on-demand via CLI. That's
   the right starting pattern.

## ADR-0166 three-question test

- **Q1 — Capability**: A corpus-decomposition mechanism for the math
  domain, parallel to cognition's `teaching/contemplation.py`. The
  capability is mechanism, not measurement — it does not directly
  lift any GSM8K case but it changes who decomposes the corpus
  (operator → engine).
- **Q2 — Lane**: Existing `audit_brief_11.json` is the input data.
  No new canonical lanes (ADR-0166 still gates). A new test lane in
  `tests/test_math_contemplation_decomposition.py` would pin
  proposal-emission for known refusal shapes.
- **Q3 — Invariant**: `wrong == 0` preserved by construction —
  proposals are evidence-only. The wrong=0 surface is the
  *ratification handler* (W2-D-shaped artifacts already exist for
  LexicalClaim; FrameClaim/CompositionClaim queued). ADR-0172 does
  not introduce new admission paths.

## Sequencing — explicitly post-FrameClaim/CompositionClaim

ADR-0172 ships AFTER:

- **ADR-0170** (injector contract widening) — provides the substrate
  for sub-shape ratification handlers to emit `CandidateOperation`.
- **ADR-0168** (FrameClaim handler) — provides one of the
  ratification targets a math proposal can emit toward.
- **ADR-0169** (CompositionClaim handler — reserved) — second
  ratification target.

Without those substrates, ADR-0172 has nothing to *propose against*.
The decomposer can identify patterns but can't route them to a
ratification handler that knows how to materialize them. Sequencing
matters here precisely the same way it mattered for cognition: the
substrate (claim types, ratification handlers) had to land before the
decomposer could pay off.

## Implementation outline (subsequent PRs, not this one)

**Tier 1 wave**

- **W1** — Schema: `teaching/math_contemplation_proposal.py` with
  `MathReaderRefusalShapeProposal` dataclass + canonical-bytes
  serialization
- **W2** — Decomposer: `decompose_audit(audit_path) ->
  tuple[MathReaderRefusalShapeProposal, ...]` with naive grouping by
  `(refusal_reason, missing_operator)` and min-2 evidence threshold
- **W3** — CLI lane: `core eval math-contemplation` runs the
  decomposer and emits proposals to
  `teaching/math_proposals/proposals.jsonl`
- **W4** — Integration: workbench (ADR-0160) renders math proposals
  alongside cognition proposals; e2e test

**Tier 2 wave (sequenced after Tier 1)**

- **W5** — Schema: `MathReaderInferenceProposal` dataclass with
  evidence + held-out-test-result fields
- **W6** — Structural-equivalence-class recognizer: clusters refusal
  cases by parsed-anchor shape, surfaces candidate canonicalization
  bridges
- **W7** — Test-and-learn loop: held-out subset selection,
  bridged-extraction application, admissibility gate run,
  outcome-scoring (positive / negative / neutral)
- **W8** — HITL integration: proposals reach the workbench *only* if
  the held-out test preserves wrong=0; negative-evidence proposals
  are auto-rejected internally
- **W9** — Inferential-bridge application path: how a ratified bridge
  materializes in the reader/injector (likely a canonicalization
  pre-pass before extraction)

Each impl PR is small, focused, regression-tested. Cognition's parallel
machinery is the template for Tier 1; Tier 2 is genuinely novel and
will need its own design ADR before W5 ships.

## What ADR-0172 does NOT do

- It does not propose any non-deterministic mechanism (decomposition
  is rule-based grouping, not learned classification).
- It does not add new eval lanes (ADR-0166 still gates).
- It does not weaken wrong=0 — proposals are evidence-only, never
  auto-applied.
- It does not change cognition's contemplation behavior (parallel
  wire, partitioned by `domain` discriminator).
- It does not mandate that any specific proposal ship — operator
  retains full HITL authority.

## Relationship to the Learning Arc

The Learning Arc milestone (2026-05-25) closed the cognition loop:
refusal → audit → engine-decomposes → proposes → HITL → ratified
corpus → next session admits.

ADR-0167 LexicalClaim partially closes the math loop: refusal →
audit → engine-emits-evidence → operator-decomposes → operator-picks
→ HITL → ratified pack → next session admits.

ADR-0172 closes the gap: refusal → audit → **engine-decomposes** →
proposes → HITL → ratified mechanism → next session admits.

That is the math-domain Learning Arc. The thesis test
([[thesis-decoding-not-generating]]) holds: the engine is decoding
the structure of its own failures, not generating new content.

## Cross-references

- [ADR-0055](./ADR-0055-inter-session-memory.md) — four-tier
  inter-session memory (the substrate this proposal-mechanism extends)
- [ADR-0056](./ADR-0056-contemplation-loop.md) — cognition
  contemplation loop (the direct template)
- [ADR-0057](./ADR-0057-teaching-chain-proposal.md) —
  replay-equivalence contract math proposals must inherit
- [ADR-0167](./ADR-0167-audit-as-teaching-evidence.md) — the parent
  evidence-wire ADR
- [ADR-0167-FOLLOWUPS](../handoff/ADR-0167-FOLLOWUPS.md) §1 — the
  sub-type handlers ADR-0172 proposes against
- [ADR-0168](./ADR-0168-frameclaim-ratification.md) +
  [ADR-0168.1](./ADR-0168.1-math-frameclaim-proposal-adapter.md) —
  FrameClaim scoping (one of the ratification targets)
- [ADR-0170](./ADR-0170-injector-contract-widening.md) — the
  substrate widening that unblocks injector-extension proposals
- [Memory: Learning Arc Milestone 2026-05-25] — the moment the
  cognition learning arc closed; this ADR is the math-domain analog
- [Thesis: decoding, not generating] — the principle this mechanism
  preserves
