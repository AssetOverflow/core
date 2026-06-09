# Stage 2 Disclosure Bus Implementation Map — session pivot to current slices

**Date:** 2026-06-09  
**Status:** implementation map / controlling checklist — docs only  

This document reconciles the June 8 session-design pivot with the implementation slices that have now landed. It is not a new architecture. It is the map that prevents the work from drifting into isolated feature patches.

## 0. Why this map exists

The recent implementation work touched ASK and VERIFIED serving foundations in small slices. That was correct, but the controlling plan is larger than any one PR:

- `docs/sessions/2026-06-08-practice-attempts-and-servability-blade.md`
- `docs/sessions/2026-06-08-epistemic-question-articulation-first-skill-of-contemplation.md`
- `docs/analysis/stage2-epistemic-disclosure-bus-verified-v1-scoping-2026-06-08.md`
- `docs/analysis/q1-epistemic-question-articulation-v1-scoping-2026-06-08.md`
- `docs/analysis/ask-serving-integration-scoping-2026-06-09.md`
- `docs/analysis/verified-serving-wiring-scoping-2026-06-09.md`

The governing pivot is:

```text
wrong=0 is not a binary answer/refuse command.
wrong=0 is no false presentation of epistemic status.
practice/contemplation may explore typed, isolated candidates.
serving must disclose only what is truthfully labelable.
```

Therefore the served surface should not grow by one-off feature branches. It should grow by activating tenants on the already-scoped Epistemic Disclosure Bus.

## 1. Controlling doctrine from the session docs

### 1.1 Practice versus serving

The practice/servability session separates two lanes:

| Lane | Purpose | License | Primary danger |
| --- | --- | --- | --- |
| practice / contemplation | explore, attempt, eliminate, learn | typed and isolated candidates may exist | getting stuck / never learning |
| serving | emit to a user/downstream surface | no false presentation of epistemic status | misrepresenting uncertainty as truth |

The practical consequence is that internal attempts, ASK artifacts, proposals, and verification proofs may exist off-serving without being user-visible. Serving requires an explicit governance decision.

### 1.2 The servability blade is not a new parallel system

The session document explicitly amends the initial sketch: the servability blade must reuse the already-shipped ADR-0206 response-governance seam (`ReachPolicy`, `govern_response`, `shape_surface`) rather than invent a new parallel object.

For Stage 2 work, every served-surface slice must therefore ask:

```text
Does this activate the existing governance seam, or is it bypassing it?
```

A bypass is architectural drift.

### 1.3 ASK is typed intake, not chat clarification

The question-articulation session defines a question as a typed request for missing state. The first contemplative move is not “ask a question”; it is:

```text
What is preventing resolution — and what KIND of limitation is it?
```

Only limitations of kind `missing_information` or `ambiguous_structure` may become ASK. Capability gaps propose. Hard boundaries refuse. Contradictions report. Input-shape cases step aside.

### 1.4 QUESTION_NEEDED and PROPOSAL_EMITTED are siblings

The session doc draws a hard line:

| Terminal | Meaning |
| --- | --- |
| `QUESTION_NEEDED` | the input is under-specified but the problem is potentially knowable after one missing datum is supplied |
| `PROPOSAL_EMITTED` | the input is sufficiently specified but CORE lacks the transform/capability |

This distinction must be preserved in artifacts, paths, tests, and served surfaces.

## 2. Stage 2 bus frame

The Stage 2 scoping doc reframes the frontier:

```text
What may CORE disclose through the served surface — and under what governed disposition?
```

The bus is the consolidating view:

```text
EpistemicState + LimitationAssessment + proof/license evidence
  -> ServedDisposition / disclosure decision
  -> shaped surface through the governance seam
```

VERIFIED is not the whole system. It is one tenant. ASK is another. Scope-boundary explanation, contradiction reporting, proposal-only, partial progress, multiple candidates, and provisional working answers are later tenants or modes on the same governance surface.

## 3. Current implementation state

### 3.1 ASK tenant — landed foundation

The following ASK foundation is now present:

```text
Q1-B typed ASK residue / MissingSlot / LimitationAssessment ask_question
Q1-C grounded-only renderer
Q1-D off-serving DeliveredQuestion / deliver_ask / teaching/questions sink
ask_serving_enabled helper, default-dark
RuntimeConfig.ask_serving_enabled = False
pass_manager off-serving ASK integration behind exercise_ask
ContemplationResult.question_path separated from proposal_path
```

Important preserved boundaries:

```text
no chat/runtime.py serving path
no served ASK surface
no Q1B_ASK_CARVE_OUT retirement
no proposal_allowed registry flip
no CLAIMS or benchmark movement
boundary-first remains before ASK
question_only sink remains distinct from proposal_only sink
```

### 3.2 ASK tenant — not yet done

The following are still open:

```text
served ASK / QUESTION_NEEDED through the governance bus
Q2 AnswerBinding and re-run through the owner organ
no-question/no-proposal dead-zone proof
Q1B_ASK_CARVE_OUT retirement proof
registry flip for missing_total_count / missing_weighted_total
broader ASK families beyond the current typed-residue subset
```

### 3.3 VERIFIED tenant — landed foundation

The following VERIFIED foundation is now present:

```text
P1-A VERIFIED contract
P1-B off-serving gold-setup-backed R2 producer
P1-C bound_slots_digest proof hardening
verified_serving_enabled helper, default-dark
RuntimeConfig.verified_serving_enabled = False
verified serving scoping / gold-free independence doc
```

Important preserved boundaries:

```text
no served VERIFIED surface
no verify.py consumption
no eval-gold-backed proof in serving
no CLAIMS or benchmark movement
no gold-free independent reader yet
```

### 3.4 VERIFIED tenant — not yet done

The following are still open:

```text
gold-free independent reader/proof source
poison fixture harness
holdout-gated verification harness
deterministic replay digest proof for served verification traces
verify.py consumption of contract verdict
served [verified] surface behind verified_serving_enabled
```

## 4. Recent PRs in plan terms

| PR | Plan role | Status |
| --- | --- | --- |
| #664 | Q1-B typed ASK residue + carve-out | merged |
| #666 | Q1-C grounded-only renderer | merged |
| #667 | Q1-D decision record | merged |
| #668 | Q1-D off-serving delivery | merged |
| #670 | ASK default-dark gate helper | merged |
| #671 | ASK serving / carve-out retirement scoping | merged |
| #672 | VERIFIED serving / gold-free independence scoping | merged |
| #673 | VERIFIED default-dark gate helper | merged |
| #674 | explicit ASK + VERIFIED config fields | merged |
| #675 | off-serving ASK pass_manager integration | merged |
| #676 | split question_path from proposal_path | merged |

This sequence was mostly faithful to the plan, but the controlling label should be:

```text
ASK tenant implementation on the Epistemic Disclosure Bus foundation
```

not merely:

```text
question feature / pass_manager feature
```

## 5. Correct next-slice ordering

### 5.1 ASK next code slice — bus activation, not runtime bypass

The next ASK code slice should not be described as “wire chat/runtime.” It should be:

```text
Activate ASK/clarify as a served tenant through the disclosure/governance bus.
```

Minimum requirements:

- use `ask_serving_enabled(config)` as a necessary gate;
- consume `ContemplationResult.question_path` / delivered question artifact;
- do not construct question prose in serving;
- do not serve unrenderable ASK;
- preserve `Q1B_ASK_CARVE_OUT`;
- preserve proposal signal when gate is disabled;
- do not flip `proposal_allowed`;
- do not bypass `govern_response` / `shape_surface` if that seam is applicable;
- if the current governance seam cannot carry ASK yet, stop and scope the exact missing adapter first.

Expected test names or equivalents:

```text
test_ask_serving_disabled_preserves_existing_proposal_signal
test_ask_serving_enabled_surfaces_question_needed_from_artifact
test_unrenderable_ask_never_serves_question_needed
test_question_only_not_proposal_only
test_served_ask_does_not_construct_question_prose
test_served_ask_uses_governance_bus_not_parallel_runtime_path
```

### 5.2 ASK following slice — no-dead-zone proof

After served ASK exists behind the gate, prove that the carve-out families cannot fall into a no-question/no-proposal dead zone.

Required proof shape:

```text
for missing_total_count / missing_weighted_total:
  gate disabled -> proposal signal preserved
  gate enabled + renderable -> QUESTION_NEEDED served safely
  gate enabled + unrenderable -> standing fallback, never contentless QUESTION_NEEDED
  no case yields neither proposal nor valid question
```

### 5.3 ASK later slice — Q1B_ASK_CARVE_OUT retirement

Only after the no-dead-zone proof passes may a later PR consider:

```text
proposal_allowed=False for missing_total_count / missing_weighted_total
remove/retire Q1B_ASK_CARVE_OUT
```

That PR must be explicit, separate, and guarded by tests.

### 5.4 VERIFIED next code slice — gold-free independent reader

The next VERIFIED code slice is not served VERIFIED. It is:

```text
Design/prototype a gold-free independent reader/proof source.
```

Requirements:

- no eval-gold setup in serving;
- no gold answer;
- no benchmark fixture;
- distinct primary/independent reader lineages;
- convergent canonical read digests;
- strict rejection of same-reader-twice;
- strict rejection of second-solver-over-one-read;
- off-serving only.

### 5.5 VERIFIED later slices

Only after gold-free independence exists:

```text
poison fixture harness
holdout-gated verification harness
verify.py consumption scoping
served [verified] behind verified_serving_enabled
```

## 6. Explicit anti-drift rules

The following are forbidden unless a future ADR/decision record explicitly reopens them:

```text
no standalone chat/runtime ASK patch that bypasses the bus
no served ASK without ask_serving_enabled
no served ASK that constructs prose instead of consuming DeliveredQuestion
no contentless QUESTION_NEEDED
no question artifact under proposal_path
no proposal artifact under question_path
no Q1B carve-out retirement before no-dead-zone proof
no served VERIFIED from eval-gold producer
no verify.py VERIFIED consumption before gold-free independent reader + poison/holdout harness
no direct EpistemicState.VERIFIED construction outside the contract route
no CLAIMS or benchmark movement from off-serving artifacts
```

## 7. Current status checkpoint

As of the `question_path` cleanup landing, the project is here:

```text
Stage 2 bus doctrine: scoped, not fully active
ASK tenant: off-serving foundation complete enough for served-bus scoping
VERIFIED tenant: contract/gate foundation complete, serving blocked on gold-free independence
Next ASK move: bus-governed served ASK, no carve-out retirement
Next VERIFIED move: gold-free independent reader, no served VERIFIED
```

Use this document as the checklist before issuing the next implementation brief.
