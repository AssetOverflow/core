# ADR-0224: Foundational Subject Substrate Readiness and Cross-Domain Affordance Map

**Status:** Proposed (docs-only until ratified; implementation slices require separate evidence-backed PRs)  
**Date:** 2026-06-20  
**Extends:** ADR-0223 (Semantic Substrate Affordance Audit — Proposed 2026-06-19)  
**Related:** ADR-0144 (Epistemic Carrier), ADR-0207 (typed adapters / no universal IR), ADR-0218 (proof-carrying promotion), ADR-0222 (FrameVerdict closed-world), PRs #829–#831 (ProblemFrame operationalization, bindings, contract_runnable_count readiness diagnostics), wrong-zero serving discipline.  
**Unlocks:** Ratifiable constitutional map structure + family specification gate; safe selection of high-leverage cross-domain families for first implementation slices after ratification.

## Context

ADR-0223 established the canonical design rule for the semantic substrate:

> closeness proposes; bindings ground; contracts determine.

It requires a deep affordance audit before broad substrate expansion and positions the proportional-decrease contracts and proposal-trace slices (#835–#837) as proving slices of that doctrine. It also reinforces preservation of graph boundaries (ADR-0144), typed adapters (ADR-0207), proof-carrying promotion (ADR-0218), and wrong-zero discipline.

The current trajectory of incremental math-affordance-family acquisition has delivered useful mechanics (assessment-backed proposal traces, role obligations, ProblemFrame relation binding, and ContractAssessment readiness measurement via contract_runnable_count from #831). However, continuing exclusively in this mode without an explicit cross-domain map risks producing a math-shaped substrate rather than the general elementary/middle-school cognition substrate required for reusable problem solving.

GSM8K remains a valuable diagnostic pressure lane (exercising quantity, state change, part/whole, rate, comparison, target binding, etc.). It must never define the substrate.

This ADR-0224 extends ADR-0223 by defining the K–8 Foundational Substrate Readiness Map — the required structure, subjects, initial high-leverage family list, readiness definition, and implementation sequence — while establishing a clear gate: full per-family specifications are required before any family receives implementation slices.

## Decision

Adopt the three-layer constitutional structure and ratify ADR-0224 as the authoritative definition of the **K–8 Foundational Substrate Readiness Map structure and requirements**.

**Core principle (extending ADR-0223):**  
No benchmark, including GSM8K, may define the substrate. Benchmarks and eval lanes are diagnostic pressure tests only. The substrate is defined by minimal reusable constructional affordances that appear across elementary and middle-school problem solving.

### Current State vs Target State (Honest Assessment)

- **Current state (post #831 + #835–#837 work):** Assessment-backed proposal traces exist. Role obligations, span-grounded bindings, and organ-specific ContractAssessment + contract_runnable_count readiness diagnostics are operational for selected math constructions. #831 introduced contract_runnable_count readiness diagnostics; #835–#837 delivered the concrete proportional-decrease closure, catalog skeleton, and proposal trace. Readiness is measured via contract_runnable_count and related diagnostics.
- **Target state:** Proposal-first construction routing through the full ADR-0223 canonical flow for all foundational families, with cross-domain reuse evidenced by ContractAssessment results.

### Required Map Structure (Ratification Scope)

ADR-0224 ratification requires acceptance of:

1. The list of foundational subjects (minimum scope).
2. The initial high-leverage constructional affordance families.
3. The required specification fields every family must eventually carry.
4. The readiness definition for this stage.
5. The post-ratification implementation sequence and family-spec gate.
6. The explicit invariants below.

Full populated specifications for each family are **not** required for ADR-0224 ratification. They are required before any implementation slice for that family is authorized.

### Initial High-Leverage Constructional Affordance Families

- reference / coreference
- part / whole
- state change
- comparison
- sequence / time
- classification
- cause / effect
- quantity / entity binding

These families are prioritized because they demonstrably appear across multiple foundational subjects and offer early cross-domain leverage.

### Required Specification Fields per Family (Future Family Spec Appendix Format)

Before any family receives an implementation slice, it must have a complete specification containing at minimum:

**Family:**  
**Domains:** (at least two non-math examples required)  
**Surface / chunk patterns:**  
**Semantic neighborhood:**  
**Construction signatures:**  
**Required roles:**  
**Optional roles:**  
**Hazards / confusers:** (must include explicit rejection rules for ContractAssessment)  
**ProblemFrame / domain-frame representation:** (typed relations and bindings)  
**ContractAssessment readiness criteria:** (candidate → contract-runnable → verified; includes independent verification path and wrong=0 preservation)  
**Verification style:**  
**Refusal conditions:** (precise blockers that produce typed refusal)  
**Cross-domain evidence:** (concrete examples + ContractAssessment results demonstrating reuse)  
**Serving status:** (current readiness / blockers)

### Foundational Subjects (Minimum Scope)

The substrate must support recognition and binding of constructional affordances appearing in at least these domains (examples are illustrative, not exhaustive):

1. Arithmetic / quantitative reasoning  
2. Physical science basics (state change, force/change, temperature, mass/comparison, material property, cause/effect)  
3. Life science basics (organism classification, needs/depends-on, food chain, life cycle, part/function, environment relation)  
4. Earth / space / geography basics (location, direction, cycle, spatial containment, map-symbol reference, cause/effect weather)  
5. Language arts / reading comprehension (actor/action/object, event sequence, claim/evidence, main idea/detail, reference/coreference, meaning from context)  
6. Social studies / civics basics (role/authority, exchange, resource use, chronology, place/event/person, cause/effect)  
7. Procedural reasoning (ordered steps, conditional action, loop/repetition, classification rule, goal/subgoal)  
8. Charts, tables, diagrams (data point, axis/value binding, comparison, trend, category/count, visual evidence grounding)

"Elementary/middle-school" in this context means **minimal reusable constructional affordances**, not broad encyclopedic knowledge ingestion or generic language understanding.

### Readiness Definition (This Stage)

Robust enough means: given a simple elementary/middle-school problem, CORE can:
- Identify the relevant constructional affordance family (or families) via the ADR-0223 flow (closeness proposes → bindings ground → contracts determine).
- Bind core roles through span-grounded bindings and proposal trace.
- Produce an explicit ContractAssessment result stating what is missing or why it is not runnable.
- Refuse honestly with typed refusal when current contracts cannot support a committed answer.

Broad solving and committed answers across the full map are explicitly out of scope until recognition + honest blocking + cross-domain evidence is stable for the initial families.

This definition preserves zero-confabulation, reviewed claims, closed-world FrameVerdict (ADR-0222), and wrong-zero discipline.

### Post-Ratification Implementation Sequence

1. Ratify ADR-0224 (structure + requirements + family-spec gate).
2. Create substrate-family registry shape (typed structures extending current ContractAssessment and readiness machinery).
3. Produce complete family specification appendices for the initial high-leverage set (one controlled PR or set of appendices per family or logical group).
4. Route one existing math construction through the full proposal-first seam using its completed family spec as the source of truth (validates integration).
5. Add the first non-math foundational family (chosen for maximum demonstrated cross-domain leverage) as a controlled test of generality.
6. Measure and evidence cross-domain reuse via ContractAssessment results + replay determinism.
7. Only after positive evidence expand the family set or move toward broader serving.

## Invariants (Non-Negotiable)

- No benchmark (including GSM8K) may define the substrate. Benchmarks are diagnostic pressure lanes only.
- All work extends ADR-0223’s canonical rule: closeness proposes; bindings ground; contracts determine.
- No new universal IR. All families are expressed as typed relations and bindings inside ProblemFrame / domain frames, connected by ADR-0207-style adapters where needed.
- Every family specification must include explicit hazards/confusers and refusal conditions that ContractAssessment can enforce.
- Cross-domain reuse must be evidenced by actual ContractAssessment + replay results, not assumed.
- Implementation slices require separate evidence-backed PRs with typed contract tests, exact span tests, metamorphic/confuser suites, replay determinism, and wrong=0 preservation.
- Assessment-backed proposal traces exist today; proposal-first routing is the target state.

## Consequences

**Positive alignment:**
- Directly extends ADR-0223’s doctrine and audit mandate.
- Provides the missing constitutional map layer that prevents math-shaped overfitting while keeping every family inside existing contract and readiness machinery (#831 diagnostics, ContractAssessment, wrong-zero).
- Creates a clean gate so ADR-0224 can be ratified without becoming an unmanageably large document.
- Supplies explicit input to future learning arenas and epistemic provenance work.

**Integration points (extension, not replacement):**
- Proposal trace and role obligations (current assessment-backed state from recent kernel work).
- ProblemFrame relation binding and domain-frame representation.
- ContractAssessment readiness criteria and organ-specific blockers (including contract_runnable_count diagnostics).
- EpistemicGraph / epistemic standing (ADR-0144) for cross-domain provenance where needed.
- Existing domain contract, promotion, and serving machinery (no parallel paths).

## What This ADR Does NOT Commit To

- Immediate broad solving or committed answers across K–8.
- Any specific numeric thresholds or benchmark targets (those belong in versioned evidence profiles).
- Changes to derivation organs, serving path, or legacy parsers without separate review and evidence.
- Session-persistent graphs, full verifier implementation, or vault cross-references (post-ADR-0144 / ADR-0223 scope).
- Physical actuation or irreversible actions.
- Any relaxation of exact spans, typed roles, confuser rejection, independent verification, or wrong=0 preservation.

## Acceptance Criteria (for ADR-0224 Ratification)

ADR-0224 is ratified when the following are accepted:

- The map structure, foundational subjects, initial high-leverage family list, required specification fields, readiness definition, implementation sequence, and family-spec gate.
- The explicit invariants (especially “no benchmark-shaped substrate” and extension of ADR-0223’s canonical rule).
- The distinction between current state (assessment-backed proposal traces) and target state (proposal-first routing).
- That full per-family specifications are required before any family receives implementation slices (not before ADR-0224 ratification itself).

## Validation Steps (Post-Ratification, Pre-Implementation)

1. Round-trip review of this ADR against ADR-0223 (full content), recent ProblemFrame binding + contract_runnable_count code, ContractAssessment diagnostics, ADR-0144, ADR-0207, ADR-0218, ADR-0222, and truth-seeking/claims ledger.
2. Confirm the substrate-family registry shape can be implemented as typed extensions of existing readiness and ContractAssessment machinery without new IR.
3. For the first post-ratification implementation slice: Trace all current callers of proposal trace, ProblemFrame relation binding, and ContractAssessment (starting from #831 / proportional-decrease work) before any code change. Extend only.
4. Ensure every family spec produced after ratification includes the required template fields and at least two non-math domain examples with cross-domain evidence.

This ADR provides the constitutional map layer that was missing. It keeps the architecture bounded, executable, and aligned with the doctrine already established in ADR-0223 while preventing the next treadmill of unbounded family addition. Ratification of the structure and gate first allows controlled, evidenced expansion.

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
