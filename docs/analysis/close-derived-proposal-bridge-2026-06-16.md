# PR-2: Derived CLOSE Facts → Review-Gated Proposal Bridge

**Date:** 2026-06-16  
**Branch:** `feat/close-derived-proposal-bridge`  
**Base:** `a1bdaa2c` (origin/main with PR #788 merged)  
**Governing sequence:** PR-1 (substrate — relational transitive CLOSE) → **PR-2 (this: proposal bridge)** → PR-3 (yardstick measurement)

## What PR-2 adds

A deterministic, default-off proposal emitter that surfaces proof-gated derived CLOSE facts as reviewable proposal artifacts.

Eligible derived facts (after consolidation):
- `derived is True`
- `derivation is not None` with `verdict == "entailed"`
- `epistemic_status == "speculative"`
- `relation_predicate` ∈ {"member", "subset"} ∪ TRANSITIVE_PREDICATES (the four strict-order predicates)

Ineligible (skipped safely, never emitted):
- Direct (non-derived) facts
- Missing or non-entailed derivation
- Non-speculative standing
- Unsupported predicates (e.g. parent_of, sibling_of, left_of)
- Malformed records

Artifacts are written as JSON to `teaching/proposals/derived_close_facts/<dedupe_key>.json` with explicit fields:

- source: "derived_close_fact"
- predicate, subject, object, relation_arguments
- derivation: {rule, verdict, premise_structure_keys}
- epistemic_status, structure_key, dedupe_key
- status: "proposal_only", requires_review: true, mounted: false

Dedupe is stable across ticks and runs (predicate + args + derivation provenance + structure_key).

## Why (the flywheel bridge)

PR-1 (CLOSE relational transitive) lets the lived loop derive and remember more sound conclusions as SESSION/SPECULATIVE facts. Without a proposal path, those facts stay trapped in session memory and never reach the reviewed learning path.

PR-2 completes the "comprehend → realize → determine → CLOSE consolidate → propose" half of the flywheel while preserving the hard boundary: only human-reviewed mutation (via the existing HITL proposal review) can produce durable (COHERENT/ratified) knowledge. Derived CLOSE proposals are **proposal-only**.

## Architecture & boundaries (strictly observed)

- **After consolidation, before (or alongside) existing proposal review.** Runs in idle_tick only when `config.review_derived_close_proposals` (default False).
- **Read/write separation.** The emitter writes artifacts. Review consumption re-uses or parallels the existing read-only `core.proposal_review` machinery (no mutation of the review contract in this PR).
- **No side effects on serving/determine.** Emission never alters user-facing surface, determine answers, or any runtime field.
- **No learning/ratification.** Artifacts stay SPECULATIVE/proposal_only. No pack writes, no corpus mutation, no COHERENT promotion, no mounting.
- **Safe failure.** Malformed records and I/O errors are counted/skipped; the tick continues. No did_work / engine checkpoint is set by proposal emission (proposals live outside engine_state).
- **Determinism.** Collection sorts by (predicate, subject, object). Dedupe key is a content hash of the provenance tuple. Repeated identical state → zero new emissions.

## Tests & gates

- Flag-off: no emission, no behavior change.
- Emission for member/subset derived and for relational-transitive derived (less_than, before_event, etc.).
- Stable dedupe on second run.
- Skips for direct facts, malformed, unsupported predicates.
- No status upgrade (remain speculative, proposal_only).
- Re-run of PR-1 tests + architectural invariants remain green.
- wrong_total == 0 on touched surfaces.

## Documentation

- `docs/runtime_contracts.md` — new subsection under idle passes documenting the bridge, eligibility, and contract.
- This note.
- Tiny pointer in root README (if a learning-loop section existed; kept high-level).

## Commit shape

1. test(proposals): cover derived CLOSE proposal bridge (flag-off, emit for both is-a and relational, dedupe, skips, no mutation).
2. feat(proposals): emit review-gated proposals from derived CLOSE facts (emitter + idle_tick wiring behind the flag).
3. docs(proposals): document the bridge in contracts + this analysis note.

## Non-goals (explicit)

- No PR-3 yardstick / capability index lane.
- No FrameVerdict serving or default wiring.
- No determine() answer=False or semantic broadening.
- No corpus/pack mutation.
- No auto-ratify, no COHERENT, no mounting.
- No broad hygiene or unrelated test fixes.
- No change to existing comprehension-failure proposal review contract (additive only).

PR-2 is the minimal bridge that makes the richer derived facts from PR-1 visible to the review path without violating any red line or the SESSION vs. reviewed learning boundary.

Next (after merge): PR-3 yardstick to measure the autonomous CLOSE climb (answerable-set growth with wrong_total=0).

---

*This note + the contracts update close the documentation obligation for the design/capability change.*