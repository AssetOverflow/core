# Ratification: Workstream A Scope — GSM8K Derivation / Reader + Recognizer Lift (First Increment)

**Date:** 2026-06-17  
**Branch:** `feat/gsm8k-derivation-reader-recognizer-lift-workstream-a` (fresh from main post the strategic deep-dive kickoff ratification)  
**Governing brief / plan:** The approved "Strategic Deep-Dive Plan for Serious Lift in Problem-Solving Capability (System-of-Systems Analysis and Workstream Initiation)" (the plan ratified in `docs/analysis/problem-solving-lift-strategic-deep-dive-ratification-2026-06-16.md`, especially its §5 Workstream A and §7 "References & Artifacts"; see also the implementation lookback in this PR). This is the required "new or delta ratif" before any code for the first increment of Workstream A.  
**Governing kickoff ratification (this delta references and extends):** `docs/analysis/problem-solving-lift-strategic-deep-dive-ratification-2026-06-16.md` (the overall plan ratified as governing; Workstream A initiated with the explicit first bullet "Ratify scope (new or delta ratif referencing gsm8k-lift-program-strategy-2026-06-04.md, ADR-0163/017x family, derivation model, this ratification, and the governing plan)").  
**Preceding work (locked):** The 2026-06-17 kickoff ratification above + the full 2026-06-16 family (especially posture, visibility, dedicated CLOSE surface, climb yardstick, integrate, bridge). `gsm8k-lift-program-strategy-2026-06-04.md` (the ADR-0114/0119/0163 arc and Streams 0/A/B/C... plan). ADR-0163/017x family + `docs/admissibility-exemplars.md` (Phase B hand-authored exemplars feeding Phase C synthesis). `docs/handoff/` math corridor briefs (the reader/recognizer synthesis corridor that produced the baseline lift). `evals/gsm8k_math/train_sample/v1/report.json` (current sealed-proxy baseline on disk). `generate/derivation/` (extract/clauses/compose/accumulate/goal_residual/multistep/search/verify + state/). `teaching/admissibility_exemplars/`, `recognition/`, `evals/gsm8k_math/practice/` + `propose_runner.py` (the contemplation/harvest/synthesis loop). `core/reliability_gate/`, `generate/cue_precision/`. `docs/runtime_contracts.md` (determination + CLOSE bridge + posture sections), `docs/testing-lanes.md` (CLOSE dedicated surface), CLAIMS.md + `scripts/verify_lane_shas.py` (sealed SHAs + auditor discipline), CLAUDE.md (ratify-first, lookback, sealed-math protection, "wrong=0 hazard surface"), Whitepaper §IV (pillars).

## Context: Baseline and the Mandate for This Increment of Workstream A

The governing kickoff ratification (2026-06-16) locked the overall plan as the authoritative document for the "serious lift in problem-solving capability" arc and initiated Workstream A (highest immediate leverage on the derivation/problem-solving compiler) with the explicit first required action: ratify scope via new/delta ratif before any code.

Current sealed-proxy baseline (on-disk `evals/gsm8k_math/train_sample/v1/report.json`, the unsealed 50-case development proxy used for the ADR-0163 corridor; real sealed 1,319-case GSM8K test remains the ultimate bar per the lift strategy):
- 4 correct / 46 refused / 0 wrong (wrong=0 gate held).
- Dominant refusal patterns in the per-case data: many "candidate_graph: recognizer matched but produced no injection" for shapes including `discrete_count_statement`, `rate_with_currency`, plus temporal/aggregation and descriptive_setup cases. The recognizer synthesis (Phase C from Phase B exemplars) is reaching the statements but the downstream injection / production bridge is not firing for a large fraction of the high-frequency refusal categories.

The `gsm8k-lift-program-strategy-2026-06-04.md` (the detailed Stream plan) identifies:
- Stream 0 (sealed baseline prerequisite — already satisfied for the proxy; real sealed measurement is the loud bar).
- Stream A (the force multiplier: general composition-promotion consumer / serving bridge that collapses per-shape hand-built promotion tax).
- Stream B (harvest at scale: industrialized exemplars + contemplation/propose loop on high-frequency shapes from the real corpus, feeding the recognizer synthesis).
- The current 4/46/0 state is the post-R4 (goal-residual) baseline on the proxy. The high-frequency refusals (R1 derived-symbol, R5 multi-step, plus the discrete/rate shapes visible in the report) are exactly the targets for the next reader + recognizer + synthesis increment.

This delta ratifies the **scope of the first concrete increment of Workstream A**:
- Targeted expansion of the reader (extract/clauses/compose/accumulate/goal_residual/multistep/search) for the refusal categories dominating the current proxy report.
- Growth + refinement of the Phase B admissibility exemplars (hand-authored canonical seeds for the visible high-frequency shapes: discrete_count_statement, rate_with_currency, temporal_aggregation, descriptive_setup_no_quantity, etc.).
- Tuning / extension of the Phase C synthesis + recognizer_registry / recognition paths so that more of the "recognizer matched but no injection" cases produce admissible, self-verifying frames that survive the verify gate (grounding ∧ cue ∧ unit ∧ completeness ∧ uniqueness) and the divergence firewall.
- Safe, read-only integration points for CLOSE-derived relations (from the now-visible proposal posture in the heavy lane) as additional premises where they can help cue or goal-residual production — explicitly **without** crossing into FrameVerdict / closed-world (per the posture ratification and INV-30/INV-31).
- All work stays inside the existing sealed-harness discipline (train_sample proxy for development, wrong=0 as non-negotiable, SHAs/auditor for any material substrate change, re-baseline of oracles after the increment, lookback before any N+1 or stacked PRs on the surface).

This increment is deliberately scoped to the **proxy** (train_sample) with the explicit obligation to re-run the full gsm8k runner + verify + invariants + (if CLOSE touched) the heavy CLOSE surface (`make test-close-flywheel`) and confirm still 0 wrong + measurable correct lift on the proxy before any claim of progress toward the real sealed bar. The real 1,319 sealed measurement remains the load-bearing oracle per the lift strategy (Stream 0 discipline).

No code changes of any kind until this delta ratification is on disk and the governing kickoff ratification + this delta are treated as the prerequisite scope lock.

## Evaluation of Scope for This Increment

The approved plan (governing kickoff ratif) already performed the exhaustive system-of-systems inventory and gap analysis. The dominant current gap for "serious lift" on the math/problem-solving substrate is exactly the derivation compiler's coverage on the high-frequency refusal shapes visible in the proxy report, combined with the per-shape promotion tax (the reason Stream A exists as the force multiplier).

This delta ratifies a **minimal, high-leverage first slice** of Workstream A:
- Reader + exemplar + synthesis improvements targeting the shapes that are already "recognizer matched but no injection" (the cheapest wins on the current proxy).
- Explicit safe CLOSE-derived premise usage (read-only, provenance-tracked, under the existing verify gate + divergence firewall; never auto-promoted, never injected into closed-world).
- No changes to the sealed "7/43/0 → 4/46/0" numbers themselves or the SHAs until the re-baseline step after the changes (per sealed discipline).
- No sensorium integration yet (that is Workstream C, later).
- No broad new serving bridge code yet (Stream A general consumer is the larger force-multiplier step; this increment harvests more fuel for the existing bridge while the general consumer is prepared).
- Heavy-lane verification only (gsm8k train_sample runner + verify is the primary oracle for this proxy increment; CLOSE heavy surface only if CLOSE proposals are consulted; invariants always).

Alternative (rejected): jumping straight to a full general promotion consumer without first harvesting more high-frequency exemplars on the current proxy would be lower-leverage and higher-risk of overfitting the proxy without moving the real bar. The lift strategy document is explicit that per-shape cost collapse (Stream A) is the multiplier, but you still need the fuel (Stream B exemplars) and the sealed measurement discipline.

This scoped increment is the "only correct path" for the first concrete step after the overall kickoff ratification: it directly attacks the visible refusal categories on the development proxy, feeds the existing synthesis/recognizer machinery (the mechanism that already produced the prior lift), keeps every invariant and sealed gate loud, and produces a measurable, re-baselined proxy result that can be audited before any further arc work.

## Recommendation and Ratified Scope for This Workstream A Increment

The scope described above is hereby ratified as the first concrete increment of Workstream A under the governing plan and kickoff ratification.

Explicit obligations before any code:
- This delta ratification artifact must be on disk and referenced in any subsequent PR description for the changes.
- All changes must be additive or semantics-preserving with respect to the verify gate (wrong=0), the sealed SHAs discipline, the proposal_only/SPECULATIVE birth posture for any CLOSE-derived facts consulted, and the INV-30/INV-31 boundaries.
- After the changes: full re-run of the gsm8k train_sample runner + verify (expect correct count to rise while wrong remains 0), architectural invariants suite, and (if any CLOSE proposal paths are exercised) the heavy CLOSE surface. The proxy numbers may move; the "0 wrong" and replay-determinism contracts must not.
- Lookback (per CLAUDE.md) before any N+1 increment on this arc or before any stacked PR sequence on the derivation/recognizer surface: audit the substrate produced by this increment for drift vs. the ratif, untested predicate paths in the verify gate, wrong=0 hazard surfaces, cross-consistency with the posture ratification, and trace/event stability.

Subsequent increments (further reader hygiene, full Stream A general bridge, larger harvest on the real train set, sensorium visual grounding for diagram problems, etc.) require their own delta ratifs or explicit amendments to this one, with the same "ratify scope before code" and re-baseline obligations.

## Alignment with Engineering Pillars (Whitepaper §IV) and Governing Plan

**Mechanical Sympathy:** All heavy work (synthesis runs, full gsm8k proxy re-baselines, any CLOSE heavy surface runs) stays inside the existing explicit opt-in dedicated lanes (`make test-close-flywheel`, the gsm8k sealed practice/confusers/train_sample harness, anti-regression demo if teaching paths are exercised). Ratify-first itself is the low-cost documentation gate before expensive implementation. No new always-on reporters or fast-path CLIs.

**Semantic Rigor:** The derivation facts remain open-world, replay-deterministic, SPECULATIVE at birth when they cross the teaching boundary, and subject to the verify gate (schema-defined proof obligation). Any CLOSE-derived premises consulted are explicitly read-only, provenance-tracked, under the existing gate, and never allowed to masquerade as closed-world or to relax the wrong=0 contract. The "serious lift" definition from the governing plan is preserved verbatim in spirit: measurable, replay-deterministic, wrong=0-preserving improvement on the proxy (and eventually the real sealed bar), with honest refusal calibration.

**Third Door:** We are not taking the obvious door of "just add more hand-authored exemplars forever" or "just widen the proxy without re-baselining the oracles." We are also not taking the corner of "touch the sealed numbers or SHAs without the auditor discipline." We are using the ratify-first + existing heavy composable harness mechanism (the same one used for the prior 2026-06-16 CLOSE visibility and posture work) as the verification surface, and we are doing the ratify-scope step before any code, exactly as the governing plan and kickoff ratification require.

## Verification Obligations (Post-This-Ratification, Pre- and Post-Code)

Before any code lands for this increment:
- This delta ratification artifact exists on disk and is the referenced scope lock (together with the governing 2026-06-16 kickoff ratification and the plan).

After the code for this increment:
- Re-run `python -m evals.gsm8k_math` (or the equivalent runner on the train_sample) + the verify gate: expect correct count to rise on the proxy while wrong remains 0 and the depth curve / adversarial properties do not regress.
- Full `tests/test_architectural_invariants.py` (INV-30/31 and related) must remain green (or the specific new paths must be covered by the existing non-vacuous anchors).
- If any CLOSE proposal paths are consulted during the synthesis or reader work: `make test-close-flywheel` (or the two-command equivalent) must pass with the new signals (posture, summary, checksums) present and consistent with the pre-increment baseline.
- Content replay checksums and trace stability for the affected derivation paths must be byte-identical or explicitly re-pinned with auditor approval (per sealed discipline).
- Git diff for the logical change set must be limited to the derivation/reader/synthesis/exemplars paths + this ratification + any mandated light doc updates (runtime_contracts / testing-lanes / PROGRESS / CLAIMS) in the same sequence. No other sealed surfaces may move except via the ratified auditor process.
- Lookback audit (CLAUDE.md) of the substrate produced by this increment must be performed before any N+1 increment or before any stacked PR sequence on the derivation/recognizer surface.

All oracles must be re-baselined and the results recorded (train_sample report, any updated SHAs if material substrate changed, etc.). "0 wrong" and replay-determinism are non-negotiable; correct count movement on the proxy is the measurable signal of lift for this increment.

## References

- Governing kickoff ratification: `docs/analysis/problem-solving-lift-strategic-deep-dive-ratification-2026-06-16.md` (and the plan it ratified).
- Detailed lift strategy: `docs/analysis/gsm8k-lift-program-strategy-2026-06-04.md` (Streams 0/A/B, leverage equation, sealed bar).
- Prior corridor work: ADR-0163/017x family, `docs/admissibility-exemplars.md`, `docs/handoff/` math corridor briefs (Phase B/C/D/E reader/recognizer synthesis).
- Current proxy baseline: `evals/gsm8k_math/train_sample/v1/report.json` (and the runner + verify.py that produced it).
- Derivation substrate: `generate/derivation/` (extract.py with EX-1/4/5/6 + hygiene, clauses.py, compose.py, accumulate.py, goal_residual.py, multistep.py/search.py, verify.py, state/).
- Harvest/synthesis loop: `evals/gsm8k_math/practice/`, `propose_runner.py`, `teaching/admissibility_exemplars/`, `recognition/`, `generate/recognizer_registry.py` + related.
- Heavy verification surfaces: `Makefile` (test-close-flywheel), `docs/testing-lanes.md` (CLOSE dedicated + review posture), `evals/anti_regression/run_demo.py` + `tests/test_anti_regression_demo.py`, gsm8k sealed harness, `tests/test_architectural_invariants.py`.
- Invariants / posture: `docs/runtime_contracts.md` (posture + CLOSE bridge), the 2026-06-16 posture ratification, CLAUDE.md (ratify-first, lookback, sealed-math, wrong=0 hazard surfaces), Whitepaper §IV.
- Sealed discipline: CLAIMS.md, `scripts/verify_lane_shas.py`.

**Ratification Status:** COMPLETE AND LOCKED. This delta ratification artifact was created (via the write tool) after the governing kickoff ratification and the approved plan, and before any code changes for this Workstream A increment. All preceding activity on this logical step was read-only exploration of the plan, the kickoff ratif, the lift-strategy doc, the current proxy report, the derivation/admissibility/synthesis code, and the heavy verification surfaces. The scope is now locked. No implementation code for the reader/recognizer lift, exemplar growth, synthesis tuning, or safe CLOSE-derived premise usage may be written until this artifact (plus the governing kickoff ratification) is treated as the prerequisite scope document. Any deviation, broadening, or code before explicit user approval of this scope requires a new (or delta) ratification.

---

*This ratification follows the project's ratify-first discipline for each concrete increment of a strategic workstream. It prioritizes clarity, intentionality, long-term alignment with the Three Engineering Pillars, preservation of every listed invariant (versor_condition at sanctioned sites only, exact CGA recall, wrong=0, INV-30/31, proposal-only/SPECULATIVE boundaries, replay determinism), Mechanical Sympathy (heavy work only in the existing dedicated lanes), Semantic Rigor (precise open-world derivation facts vs. closed-world, honest epistemic standing), and Third Door (ratify-scope artifact + extension of the existing heavy composable harness and synthesis loop, rather than broad new infrastructure or isolated tweaks) over expedience. The governing plan and kickoff ratification remain the load-bearing references; this artifact locks the scope for the first increment of Workstream A.*