# ADR-0016 — Capability Roadmap and Eval Methodology

**Status:** Accepted
**Date:** 2026-05-15
**Authors:** Joshua Shay
**Derived from:** `docs/sessions/SESSION-2026-05-15-capability-gates.md`

## Context

CORE needs a falsifiable framework for measuring progress toward its design
goals. Without one, "are we there yet" remains a subjective question and
progress drifts toward vibes-based evaluation.

The 2026-05-15 session deliberated on:

- What fluency means for the three foundational languages (English, Hebrew,
  Koine Greek) and when engineering ends and curriculum begins.
- What additional capability dimensions matter for an AGI-aspiring architecture.
- How CORE's structural properties compare to modern transformer architectures.
- How to build honest benchmarks that resist overfitting.

## Decision

Adopt the Verifiable Competence Benchmark framework defined in
`docs/capability_roadmap.md` as the governing plan for CORE's capability
development. The framework consists of:

1. **Benchmark Discipline (Part I)** — five rules that govern every eval lane:
   three-set splits, versioned difficulty escalation, adversarial regeneration
   on pass, frontier baseline tracking, and honest reporting.

2. **Six Phases (Part II):**
   - Phase 0: Methodology lock-in (eval infrastructure)
   - Phase 1: Foundational Triple (fluency, domain acquisition, identity)
   - Phase 2: Structural Wins (provenance, monotonic learning, calibration,
     symbolic logic, adversarial identity)
   - Phase 3: Reasoning Depth (compositionality, inference closure,
     introspection, multi-step reasoning, cross-domain transfer)
   - Phase 4: Scale and Efficiency (sample efficiency, vault cost curves,
     multi-agent composition)
   - Phase 5: Curriculum Era (open-ended domain acquisition)

3. **Eval contract template** — every lane lives in `evals/<lane>/` with:
   `contract.md`, `dev/`, `public/v1/`, `holdouts/`, `runner.py`, `baselines/`,
   `results/`.

4. **Open scope decisions** to be pinned before Phase 3:
   - Agency (responsive vs. goal-directed)
   - Tool use (typed deterministic operators)
   - Code generation (first-class articulation target)

## Consequences

- Every new eval lane must follow the convention or it does not merge.
- The existing `core eval cognition` is retrofitted as the first lane under the
  new convention (Phase 0 forcing function).
- Progress is tracked in `docs/PROGRESS.md` with evidence links.
- The roadmap itself is versioned; amendments are dated, never silently rewritten.

## References

- `docs/capability_roadmap.md` — full roadmap
- `docs/sessions/SESSION-2026-05-15-capability-gates.md` — deliberation log
- `docs/eval_methodology.md` — extracted Part I (benchmark discipline contract)
