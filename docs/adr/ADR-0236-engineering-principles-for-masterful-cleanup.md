# ADR-0236: Engineering Principles for Masterful Cleanup

**Status:** Proposed

**Date:** 2026-06-25

**Scope:** Whole codebase; refactors, capability PRs, diagnostics, Workbench, runtime/kernel boundaries, eval/reporting surfaces

**Depends on:**

- ADR-0223 Semantic Substrate Affordance Audit and Foundation Alignment
- ADR-0224 Quantity-Entity foundational seam
- ADR-0228 GeometricSearchRun envelope
- ADR-0229 Contract/Proof Replay Adapter boundary
- ADR-0230 Sealed Practice Trace boundary
- ADR-0231 First Candidate Operator boundary
- ADR-0232 CandidateAttempt Run-Binding boundary
- ADR-0233 Bound Practice Episode Sealing
- ADR-0234 Second Candidate Operator Selection
- ADR-0235 Apple Silicon UMA acceleration lanes
- INV-30 open-world determination never asserts False
- Existing wrong-zero, replay, provenance, and proposal-first discipline

## 1. Summary

CORE is now large enough that ordinary cleanup is not sufficient. Refactors must
serve the architecture rather than only reduce file size, silence lint, or make
code look conventional.

This ADR establishes the engineering principles that future cleanup and
implementation PRs must cite when changing boundaries, splitting modules,
retiring legacy seams, adding diagnostics, or promoting new capability paths.

The principles are intentionally ordinary software engineering principles, but
interpreted through CORE's load-bearing requirements:

```text
Deterministic cognition
Exact provenance
Proposal-first construction
Authority separation
Wrong-zero serving discipline
Replay equivalence
Fail-closed behavior
No hidden normalization
No approximate recall
No downstream phase manufacturing upstream evidence
```

The short form:

```text
extractors observe
proposers hypothesize
binders ground
contracts assess
proof/verifiers admit or refuse
renderers disclose
Workbench observes unless explicitly allowlisted
serving remains separately authorized
```

## 2. Problem

As CORE adds ProblemFrame construction, contract residuals, candidate operators,
sealed practice, Workbench evidence surfaces, and native acceleration lanes, some
modules can accumulate too many responsibilities.

The immediate motivating example is `generate/problem_frame_builder.py`. It has
historically acted as all of the following:

```text
scalar extraction
unit extraction
hazard extraction
process-frame detection
construction proposal generation
mention extraction
mention binding
quantity-kind disposition
bound relation construction
question-target binding
ProblemFrame assembly
post-build contract/assessment coordination
```

That mixture weakens auditability even when behavior is currently correct. A
future change can accidentally move evidence across phase boundaries, give a
proposal assessment authority, treat absence as proof, or make a diagnostic path
look like a serving path.

CORE therefore needs a repeatedly citeable engineering canon for cleanup.

## 3. Decision

Future cleanup and implementation PRs SHOULD be organized around the principles
below. A PR that intentionally violates one of these principles MUST explain the
violation, identify the bounded exception, and add a test or ADR-scoped non-goal
that prevents the exception from becoming doctrine drift.

### 3.1 Single Responsibility / One Reason to Change

A module, object, or function should have one conceptual job and one primary
reason to change.

For CORE, responsibility boundaries are semantic, not merely syntactic:

```text
extractors observe raw/evidenced surface facts
proposers create diagnostic hypotheses
binders attach exact spans and roles
contracts assess existing evidence
proof/verifiers admit or refuse
renderers disclose state without deciding it
Workbench reads evidence unless an action is explicitly allowlisted
```

A file is suspect when it changes for unrelated reasons such as extraction,
proposal timing, binding topology, assessment authority, and rendering policy.

Required cleanup posture:

```text
When a file changes because of multiple independent concepts, split by pipeline
phase before adding more capability.
```

### 3.2 Authority Boundary Principle

Only one layer may have authority to make a given class of decision.

Examples:

```text
ConstructionProposal may propose only.
ContractAssessment may declare runnable/refused diagnostic readiness.
determine() may determine open-world True, never open-world False.
FrameVerdict may handle closed-world local verdicts under its own firewall.
Renderer may disclose; it may not decide.
Workbench may observe unless an action is explicitly allowlisted.
```

Forbidden drift:

```text
proposal object carrying runnable/refused state
builder manufacturing proposals from assessment output
renderer deciding epistemic state
UI route mutating runtime truth state without an allowlisted action
heuristic parser silently becoming a serving fact producer
```

Required cleanup posture:

```text
Every object/function should have a documented authority level. If the authority
is unclear, rename, split, or remove the path.
```

### 3.3 Phase Separation Principle

CORE pipelines must preserve phase order.

Canonical construction sequence:

```text
surface evidence
-> ConstructionProposal
-> exact mentions and bindings
-> ContractAssessment
-> proof/derivation or refusal
-> independent verification
-> admission/refusal
-> disclosure/rendering
```

Downstream phases MUST NOT manufacture upstream evidence. A
`ContractAssessment` may inspect proposals and bound evidence, but it must not
create the proposal that supposedly justified the assessment.

Required cleanup posture:

```text
No downstream phase may create, repair, or backfill upstream evidence unless a
separate ADR explicitly defines a replayable repair phase with its own evidence
and authority boundary.
```

### 3.4 Explicit Evidence Over Implicit Defaults

Absence is not proof.

Forbidden patterns:

```text
no unit found -> count
no contradiction found -> true
no error raised -> safe
no reviewer present -> accepted
no evidence span -> synthetic placeholder treated as provenance
```

CORE posture:

```text
absence of evidence -> unresolved or refused
positive evidence -> candidate
contract/proof/verifier -> admitted within scope
```

Required cleanup posture:

```text
Remove silent defaults that create semantic state. Replace them with explicit
unresolved, refused, or no-disposition outcomes.
```

### 3.5 Dependency Direction / No Backward Imports

Import direction must follow pipeline direction.

Preferred shape:

```text
builder imports extractors/proposers/binders
proposers import construction catalog/factory only
binders import frame/kernel facts only
contracts import ProblemFrame/read evidence and catalog metadata
renderers import disclosure/read models only
Workbench imports read APIs and explicit action APIs
```

Suspicious shape:

```text
extractor imports contract
proposal factory imports assessment
contract creates proposal
builder imports serving dispatcher
UI imports mutable runtime internals
```

Required cleanup posture:

```text
If import direction contradicts pipeline direction, stop and refactor before
adding capability.
```

### 3.6 Invariants as Code, Not Comments

An architectural rule is not durable until it is machine-pinned.

Acceptable pins include:

```text
unit test
property test
AST/source-boundary test
import-boundary test
replay test
schema validator
lane SHA
gold/holdout eval
contract assertion
```

Examples of rules that should be pinned:

```text
ConstructionProposal.status == "proposed" only
ContractAssessment never creates ConstructionProposal
open-world determine() never emits answer=False
no hidden normalization inside propagation
no diagnostic-only module imported by serving dispatch
replay-stable canonical ordering for emitted artifacts
```

Required cleanup posture:

```text
Every important architectural sentence should eventually become a test, a lane,
or an explicit ADR-scoped non-goal.
```

### 3.7 Fail-Closed / Refusal-First

Unknown or ambiguous states must not become authority by default.

Forbidden patterns:

```text
except: return answer
missing pack: continue
ambiguous relation: choose first
failed verification: use candidate anyway
unknown unit: assume count
```

Required cleanup posture:

```text
Any fallback must prove that it cannot increase authority. If it cannot prove
that, it must fail closed, refuse, or emit an unresolved diagnostic state.
```

### 3.8 Determinism / Replay Equivalence

Same inputs must produce the same semantic trace unless a declared nondeterminism
boundary exists.

Required properties:

```text
canonical ordering
stable IDs
content-addressed or claim-addressed keys where appropriate
no set/dict-order leakage in emitted artifacts
no time/random/environment dependence in reasoning
same input -> same frame/proposals/contracts/disclosure
```

Required cleanup posture:

```text
Any emitted artifact must have deterministic ordering and replay-stable identity.
```

### 3.9 Diagnostic Is Not Serving

Diagnostic artifacts may aid humans, tests, Workbench, and future candidate
operators. They do not grant serving authority.

Diagnostic examples:

```text
ProblemFrame
ConstructionProposal
ContractAssessment
ContractResidual
CandidateOperatorResult
CandidateAttemptRunBinding
SealedPracticeTrace
Workbench trace panels
eval/readiness reports
```

Forbidden drift:

```text
diagnostic_only=True object imported by serving dispatcher
eval readiness metric changing runtime behavior
candidate score admitted without proof or verifier
Workbench evidence card mutating truth state
```

Required cleanup posture:

```text
Diagnostic artifacts may inform review and practice; they may not serve unless a
separate reviewed PR grants serving authority and adds proof/replay gates.
```

### 3.10 Locality and Exact Provenance

Semantic claims must be tied to exact source evidence.

Required properties:

```text
exact SourceSpan
stable mention ID
explicit binding edge
explicit role
explicit evidence_spans
span text matches source text
no synthetic spans masquerading as observed provenance
```

Required cleanup posture:

```text
No semantic object without provenance. No provenance without exact span integrity.
```

### 3.11 No Clever Abstractions Before Repeated Proof

CORE should prefer duplicated clarity over premature generalization until shared
structure is proven by multiple real families and tests.

Suspicious abstractions:

```text
generic universal graph
generic semantic parser
generic all-constructions engine
generic proposal status machine
generic contract runner that hides family-specific obligations
```

Required cleanup posture:

```text
Keep narrow family-specific logic until at least two or three real use cases
prove the abstraction and its invariants.
```

### 3.12 Small Load-Bearing PRs

A cleanup PR should strengthen one named invariant.

Preferred PR names:

```text
refactor(kernel): split ProblemFrame proposal extraction
fix(kernel): remove assessment-backed proposal fallback
fix(kernel): require positive quantity-kind grounding
test(algebra): pin raw-vs-closed versor boundaries
docs(workbench): separate diagnostic and teaching proposal vocabulary
```

Forbidden PR shape:

```text
refactor everything in ProblemFrame and improve contracts and update Workbench
```

Required cleanup posture:

```text
One PR = one primary invariant strengthened.
```

## 4. Cleanup Review Checklist

Every cleanup or capability PR SHOULD answer these questions in its description
or tests when relevant:

```text
Responsibility:
- Does each touched module have one clear reason to change?

Authority:
- Did any object/function gain decision authority it should not have?

Phase order:
- Did any downstream phase create upstream evidence?

Evidence:
- Are all semantic claims tied to exact spans/provenance?

Failure:
- Do unknown/ambiguous cases refuse or remain unresolved?

Determinism:
- Is output order/id generation canonical and replay-stable?

Serving boundary:
- Did diagnostic-only code remain non-serving?

Tests:
- Is the architectural rule pinned by a test, lane, schema, or explicit non-goal?

Scope:
- Is this PR strengthening one primary invariant rather than many unrelated ones?
```

## 5. Immediate Application to ProblemFrame Cleanup

This ADR authorizes using the above principles to guide a sequence of bounded
ProblemFrame cleanup PRs. It does not itself implement those changes.

Recommended order:

```text
1. Pin proposal-first assessment boundary with regression tests.
2. Remove assessment-backed proposal synthesis and retire make_proposal().
3. Split problem_frame_builder.py by pipeline phase while preserving behavior.
4. Add import/source-boundary tests for proposal creation authority.
5. Fix quantity-kind grounding so absence of a unit does not imply count.
6. Add raw-vs-closed versor boundary tests for Python/Rust runtime use.
7. Apply the same authority/read-only discipline to Workbench read models.
```

Suggested module split, if and when performed:

```text
generate/problem_frame_builder.py
    public facade and orchestration only

generate/problem_frame_extractors.py
    scalar, unit, hazard, process-frame extraction

generate/problem_frame_proposals.py
    construction proposal detection only

generate/problem_frame_mentions.py
    mention and MentionBinding extraction

generate/problem_frame_bound_relations.py
    quantity-kind dispositions, bound relations, bound question target
```

The split should be behavior-preserving. Semantic hardening should happen in
separate PRs unless the existing behavior is already violating a pinned invariant
and the PR scope explicitly names that invariant.

## 6. Non-Goals

This ADR does not:

- implement any refactor;
- alter runtime behavior;
- change serving admission;
- mutate packs, reports, sealed traces, or eval artifacts;
- authorize broad rewrites;
- introduce a universal intermediate representation;
- promote diagnostic artifacts to serving authority;
- relax wrong-zero, replay, evidence, or proof gates.

## 7. Consequences

Positive consequences:

- Refactors become strategically organized rather than aesthetic.
- PRs can cite a common engineering doctrine.
- Authority leaks become easier to detect and reject.
- Workbench and diagnostics can grow without silently becoming serving paths.
- ProblemFrame and candidate-operator work can remain coherent as capability
  expands.

Costs:

- Some cleanup will take more PRs.
- Files may remain temporarily large while invariants are pinned first.
- Contributors must justify dependency direction and authority boundaries.
- Premature abstraction is deliberately slowed.

This cost is accepted because CORE values truthfulness, replayability,
mechanical auditability, and wrong-zero discipline over short-term refactor
speed.
