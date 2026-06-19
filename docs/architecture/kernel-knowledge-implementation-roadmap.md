# Kernel Knowledge — Implementation Roadmap

This document outlines the step-by-step roadmap for implementing and integrating the target-state **Kernel Knowledge Layer** in CORE.

---

## Current Baseline Context (PR-0 Status)

As of PR-0, the baseline scoring metrics after #827 are:
- **`train_sample`:** 30 correct, 20 refused, 0 wrong (30/20/0)
- **`holdout_dev`:** 5 correct, 495 refused, 0 wrong (5/495/0)

> [!NOTE]
> This roadmap is documentation-only (PR-0). It introduces no code, changes no serving paths, and has **zero impact** on these baseline benchmark scores.

---

## PR 1: Kernel Knowledge Doctrine
- **Purpose:** Establish the architectural design, taxonomy, and rules for the Kernel Knowledge Layer.
- **Files Likely Touched:**
  - `docs/architecture/kernel-knowledge-layer-v1.md`
  - `docs/analysis/kernel-knowledge-inventory-2026-06-18.md`
  - `docs/architecture/kernel-knowledge-implementation-roadmap.md`
- **Tests Required:** None (documentation-only).
- **Explicit Non-Goals:** Modifying python source files or changing benchmarks.
- **Acceptance Criteria:** Code review approval from domain experts.
- **Risks:** Scope-creep in review.
- **Rollback Strategy:** Revert docs commits.

---

## PR 2: ScalarEquivalence Facade
- **Purpose:** Introduce the `ScalarEquivalence` facade layer querying over the existing [ADR-0128](../decisions/ADR-0128-numerics-pack.md) `en_numerics_v1` pack to map and canonicalize number words, fractions, and percentages, unless a later ADR proves a separate pack is necessary.
- **Files Likely Touched:**
  - `language_packs/scalar_equivalence.py` [NEW]
- **Tests Required:**
  - Unit tests validating mapping of `half`, `0.5`, `50%`, and unicode fraction symbols to their canonical scalar values.
- **Explicit Non-Goals:** Integrating this facade into any parser or serving code path.
- **Acceptance Criteria:** All unit tests pass; package build is successful.
- **Risks:** Unforeseen package import issues or dependency cycles.
- **Rollback Strategy:** Remove the new facade file.

---

## PR 3: Refactor Percent Partition Organ
- **Purpose:** Update the percent partition organ to resolve scalar equivalences through the new `ScalarEquivalence` facade.
- **Files Likely Touched:**
  - `generate/derivation/percent_partition.py`
  - `generate/derivation/extract.py`
- **Tests Required:**
  - Run the `smoke` and `cognition` suites to verify that `percent_partition` cases still pass.
- **Explicit Non-Goals:** Modifying other organs.
- **Acceptance Criteria:** Percent partition cases pass, and local regex matches for scalars are removed.
- **Risks:** Breaking edge cases in fraction parsing.
- **Rollback Strategy:** Revert `percent_partition.py` to its original state.

---

## PR 4: Units/Dimensions Kernel v1
- **Purpose:** Unify the units and numerics loaders to standardize dimension checks.
- **Files Likely Touched:**
  - `language_packs/loader.py`
  - `language_packs/numerics_loader.py`
- **Tests Required:**
  - Standard unit conversion tests.
- **Explicit Non-Goals:** Implementing new physical dimensions.
- **Acceptance Criteria:** Units and numerics packs load under a single unified API.
- **Risks:** Merge conflicts with concurrent PRs.
- **Rollback Strategy:** Revert loader refactoring.

---

## PR 5: ProcessFrame Kernel v1
- **Purpose:** Introduce declarative process frames (e.g., repeating work cycles, wages) exposing candidate relation schemas and role requirements.
- **Files Likely Touched:**
  - `generate/derivation/process_frame.py` [NEW]
- **Tests Required:**
  - Rate multiplier and labor hours computation schemas.
- **Explicit Non-Goals:** Modifying the solver engine or executing arithmetic solving.
- **Acceptance Criteria:** Process frames expose correct schemas and role mappings.
- **Risks:** Under-specifying the labor rate relations.
- **Rollback Strategy:** Remove `process_frame.py`.

---

## PR 6: ProblemFrame IR v0
- **Purpose:** Define the intermediate representation (IR) structure for parsed problems.
- **Files Likely Touched:**
  - `generate/problem_frame.py` [NEW]
- **Tests Required:**
  - Parsing unit and comparative structures into the IR.
- **Explicit Non-Goals:** Replacing the candidate graph parser or solving arithmetic.
- **Acceptance Criteria:** ProblemFrame holds structured quantities and dimensions.
- **Risks:** Performance overhead during parse phases.
- **Rollback Strategy:** Remove `problem_frame.py`.

---

## PR 7: Morphology Atlas v2 with Missing-Kernel Labels
- **Purpose:** Extend the experience flywheel to report missing kernel nodes.
- **Files Likely Touched:**
  - `scripts/gsm8k_experience_flywheel.py`
- **Tests Required:**
  - Running the flywheel on failed cases and verifying the presence of `missing-kernel` tags.
- **Explicit Non-Goals:** Automatic pack mutation.
- **Acceptance Criteria:** Flywheel reports correctly tag missing elements.
- **Risks:** Misclassifying parsing failures as missing nodes.
- **Rollback Strategy:** Revert flywheel changes.

---

## PR 8: First Contract-Backed ProblemFrame Organ
- **Purpose:** Implement a solver organ that consumes the ProblemFrame IR rather than raw text.
- **Files Likely Touched:**
  - `generate/derivation/first_ir_organ.py` [NEW]
- **Tests Required:**
  - Integration tests on GSM8K problems mapped to the new organ.
- **Explicit Non-Goals:** Overwriting all existing organs.
- **Acceptance Criteria:** The target organ passes all evaluation cases with zero errors.
- **Risks:** Performance degradation under multi-step parsing.
- **Rollback Strategy:** Disable or remove `first_ir_organ.py`.
