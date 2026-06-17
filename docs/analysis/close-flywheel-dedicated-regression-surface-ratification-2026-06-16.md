# Ratification: Create a Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)

**Date:** 2026-06-16  
**Author:** Grok (following user brief)  
**Branch:** feat/create-dedicated-close-flywheel-regression-surface (freshly created from clean main)  
**Base:** Clean fetched main @b2b4d79b (includes post-#792 merge of prior integration work; working tree clean)  
**Brief reference:** "Title: Create a Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)" (strict "ratify first" workflow; build on #792)

**Context:**
PR #791 hardened `evals/close_derived_climb` to full Claim B (lived `ChatRuntime.idle_tick()` + `IdleTickResult.derived_close_proposals_emitted`, `determine()` + `Determined(..., rule='direct')` semantic asserts on positives, `content_replay_checksum` over canonical closures with structure_key/Derivation/premise keys + proposal bodies; preserved 1/5/8 growth, wrong_total=0, determinism, SPECULATIVE/proposal_only, all invariants).

PR #792 (the immediate "Integrate..." follow-up) promoted the yardstick via docs recommendation in testing-lanes.md + Makefile comments + hermetic embedding into `evals/anti_regression/run_demo.py` (and its contract test) so `core demo anti-regression` now executes and reports the Claim-B signals. This made it "recurring" in documented determinism reruns and the anti-regression teaching demo flow.

This brief asks for the *next* step: elevate from "recommended invocation" to a **dedicated, clearly named, intentional regression surface** for the CLOSE flywheel at Claim-B level. It must be positioned for heavier determinism regressions and teaching/anti-regression verification (not fast local dev or CI), align with the project's Engineering Pillars (Mechanical Sympathy, Semantic Rigor, Third Door per Whitepaper.md), respect hermeticity/composable lanes, and stay strictly in scope.

The yardstick already exists and is proven (via `python -m evals.close_derived_climb`, the contract tests, and the #792 embedding). The task is naming, documenting, and surfacing it as a coherent target.

## Ratification Decision (chosen approach, justified before any implementation)

**Before any implementation code or edits to source/docs (other than creation of this artifact), the single correct path is:**

Introduce a **dedicated CLOSE Flywheel regression surface** via a minimal, composable, explicitly heavy "lane" construct that reifies the full Claim-B yardstick invocation as a first-class, intentional target. Concretely:

1. **Define the dedicated surface (clearly named invocation for heavier flows):**
   - Add a new explicit make target `test-close-flywheel` (plus .PHONY) in `Makefile`. The target runs the complete Claim-B yardstick:
     ```
     uv run python -m evals.close_derived_climb
     uv run python -m pytest tests/test_derived_close_proposals.py tests/test_architectural_invariants.py tests/test_anti_regression_demo.py -q
     ```
     (The inclusion of the anti test ensures the #792 hermetic embedding participates.)
   - Name it intentionally ("CLOSE Flywheel" / "test-close-flywheel"). Document in the target comment and help text its purpose as the high-signal Claim-B regression surface.
   - **Positioning:** Explicitly heavy / opt-in only. Do *not* wire it into `test-fast`, `test-slow`, `test-full`, any `-m` marker, `core test --suite`, CI workflows, or generic pytest collection. It lives alongside the existing lanes as a composable heavy-verification tool (for use after CLOSE-related changes in determinism reruns or teaching/anti-regression verification). This satisfies "not fast local or CI runs" and out-of-scope constraints while giving a "clearly named and documented way to invoke".

2. **Integrate into existing high-value flows (clean, hermetic, additive, building directly on #792):**
   - The #792 embedding of the yardstick execution inside `evals/anti_regression/run_demo.py` (the teaching anti-regression demo) + pinning in its test is the primary "high-value flow" integration point. It already pulls the full Claim-B (lived flag, semantic determine, content checksum) into the demo that exercises reviewed teaching gates.
   - Make small, purely additive, hermetic polish if needed to "cleanly embed" (e.g. enhance comments/labels in the embedding and RESULT output to explicitly reference "CLOSE Flywheel Regression Surface (Claim-B)" and the new make target; ensure the `close_derived_climb` report field and human output continue to surface the key signals; no behavior, dataclass, or logic changes).
   - Optionally add cross-references or a one-line hermetic mention in one related teaching verification path (e.g. a comment or docstring in `tests/test_reviewed_teaching_loop.py` or `docs/evals/anti_regression_demo.md` "How to reproduce" section) that operators running teaching anti-regression verification should also consider `make test-close-flywheel`. Keep strictly additive/hermetic — no new calls that could introduce side effects or non-determinism.
   - The surface "integrates" by *naming and elevating* the existing #792 embedding as part of the dedicated target (the anti test is part of what the make target runs).

3. **Update documentation (prominently and completely):**
   - In `docs/testing-lanes.md`: Elevate or replace the prior "# Recommended determinism / teaching regression invocation..." section with a new top-level or clearly headed section titled **"Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)"** (or equivalent). Include:
     - Purpose: high-signal, intentional regression target for the full lived CLOSE flywheel (autonomous derived-fact growth + gated proposal emission) at Claim-B strength.
     - Invocation: `make test-close-flywheel` (primary named surface) or the equivalent `uv run python -m ...` commands.
     - Claim-B capabilities: exact list (real idle_tick + IdleTickResult.derived_close_proposals_emitted for proposal flag; explicit determine() asserts with rule='direct' for semantic_positives_determined_direct; content_replay_checksum on canonical closures + proposal bodies; retained wrong_total=0, 1/5/8 growth, determinism, etc.).
     - Expected runtime characteristics: heavyweight (~60s+ on 10-core mac, driven by multiple real ChatRuntime turns + climbs to fixed point; comparable to other proof-scale inner-loop fixtures); explicitly for heavier determinism regressions and teaching/anti-regression verification flows.
     - Hermeticity guarantees: fresh per-run ChatRuntime (no_load_state), internal TemporaryDirectory only for proposal sink during flag test, zero writes to engine_state/ / active teaching corpus / shared proposal sinks / evals reports; preserves all invariants (wrong_total=0, replayability, SPECULATIVE-only, proposal-only boundaries, INV-21/29/30/31, versor_condition, etc.).
     - Alignment with Engineering Pillars (Whitepaper.md §IV): Mechanical Sympathy (respects cost model by keeping it out of fast paths and default CI; explicit opt-in for heavy work), Semantic Rigor (precise named surface with non-negotiable Claim-B contract and capabilities; no fuzzy or approximate inclusion), Third Door (neither pollutes existing generic suites/CI nor adds new CLI commands/heavy infra; instead a minimal composable make lane + docs reification built from first principles of the project's lane model).
     - References: this ratification artifact, the #791 Claim-B hardening ratification, the #792 integration ratification, `evals/close_derived_climb/contract.md`, `docs/evals/anti_regression_demo.md`, `docs/runtime_contracts.md`, prior analysis docs on CLOSE, the anti-regression test, and the make target.
   - Update `Makefile` comments (already partially present from #792) to reference the new dedicated target and surface name.
   - Update supporting docs for accuracy and refs: `docs/evals/anti_regression_demo.md` (how-to and falsifiable claims sections to note the surface/make target and that the demo participates in it), `evals/close_derived_climb/contract.md` (add "Dedicated surface" note + link to testing-lanes section + this ratif), and any cross-refs in `docs/runtime_contracts.md` if the determination surface mention needs tightening. Keep changes minimal and reference-focused.
   - The surface name and description make the "what/why/how/hermeticity" first-class and auditable.

4. **Preserve all invariants and boundaries (non-negotiable):**
   - The make target and any doc updates are pure invocation + description. They call only already-shipped hermetic entrypoints (`python -m evals...` which asserts internally, and the anti demo which already embeds without mutation).
   - No edits to core/ (chat/runtime.py, generate/*, session/*, vault/*, etc.), no changes to proposal review/teaching logic, FrameVerdict, RuntimeConfig, closed-world reasoning, or any serving/ratification paths.
   - All prior guarantees (wrong_total=0 across scenarios, content/replay checksum stability, lived flag isolation only when flag enabled, semantic direct rule, proposal bodies with status="proposal_only" + requires_review + epistemic="speculative", no corpus mutation, byte-identical active state in anti demo, etc.) remain enforced by the yardstick and #792 embedding.
   - Hermeticity per testing-lanes.md rules is upheld (and documented as a property of the surface).

**Why this is the only correct path (and must not be broadened):**

- It directly satisfies the Objective ("clear, intentional, and high-signal regression surface" that "properly exercises the hardened Claim-B yardstick") and every Success Criterion while obeying every Constraint, Out-of-Scope item, and the Engineering Pillars.
- **Mechanical Sympathy:** Explicitly treats the yardstick as heavyweight real-runtime work (multiple ChatRuntime + idle_tick to fixed point + climbs). Does not fight the cost model by sneaking it into fast lanes, generic suites, or CI.
- **Semantic Rigor:** Gives the Claim-B behaviors a *precise name and contract* ("Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)") with enumerated capabilities, runtime expectations, and hermeticity guarantees. No vague "also run this sometimes."
- **Third Door:** Rejects the two obvious doors (1. add to existing fast/full/slow or a generic "determinism" suite, which would violate positioning + out-of-scope + mechanical sympathy; 2. create new CLI command / heavy test infrastructure like a new core subcommand or pytest plugin or broad suite wiring). Instead: a minimal named make target (already the project's composable lane mechanism per testing-lanes + Makefile) + authoritative documentation. Composable, intentional, built from the project's own lane philosophy.
- Strictly inside Scope: defines the named surface (make target + docs section), integrates cleanly/additively into anti-regression (the high-value teaching path, building on #792 embedding), updates the required docs with all specified content (purpose, Claim-B list, runtime, hermeticity, pillar alignment, ratif/contract refs), preserves every invariant (no core/teaching/FrameVerdict changes).
- Avoids every Out-of-Scope item: no fast/generic suite inclusion, no "on every push/CI", no new CLI commands, no modification of proposal review/teaching logic/closed-world, no broad refactoring.
- Highest long-term value with lowest risk: the surface is discoverable and intentional exactly where heavy CLOSE flywheel verification belongs (post-change determinism reruns + teaching anti-regression flows). The #792 embedding already provides the "integrate into existing high-value flows"; this task names and elevates the whole thing.
- Any other path (new `core test --suite close-flywheel` entry in cli.py + test_cli_test_suites.py, adding the evals to an existing suite, creating a scripts/ wrapper as "heavy infra", modifying conftest markers, running inside test-full, or changes that touch teaching code) would either violate the "Creating new CLI commands or heavy test infrastructure", "not ... on every push/CI", "stay strictly within Scope", "Prioritize clarity... over maximal... inclusion", or "No changes to core... proposal review" constraints — or would dilute the intentionality that the brief demands.
- Ratifying this exact path first ensures implementation cannot drift; every edit will be traceable to "the dedicated surface is the make target + the named section in testing-lanes.md that exercises the full yardstick (including via the anti demo)".

**References (to be linked in PR):**
- This ratification: `docs/analysis/close-flywheel-dedicated-regression-surface-ratification-2026-06-16.md`
- #791 Claim-B hardening: `docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md`
- #792 integration: `docs/analysis/integrate-hardened-close-yardstick-determinism-teaching-regression-ratification-2026-06-16.md` + PR #792
- Yardstick: `evals/close_derived_climb/{contract.md, runner.py, __main__.py}`
- Lanes + hermeticity: `docs/testing-lanes.md` (will host the dedicated surface section) + `Makefile`
- Anti-regression (the integration flow): `evals/anti_regression/run_demo.py` + `tests/test_anti_regression_demo.py` + `docs/evals/anti_regression_demo.md`
- Pillars: `docs/Whitepaper.md` §"IV. The Three Engineering Pillars"
- Related: `docs/runtime_contracts.md`, inner-loop determinism discussion in testing-lanes.md, `tests/test_derived_close_proposals.py`, `tests/test_architectural_invariants.py`

**Ratification Status:** COMPLETE AND LOCKED. This artifact was written on the clean branch *before any search_replace, write (other than this ratif), or other implementation edit to Makefile, testing-lanes.md, anti_regression code/docs, contract.md, or any other file*. All prior steps were git + read-only exploration (list_dir, read_file, grep). 

Implementation will now proceed *strictly* to the four Scope bullets using exactly the approach above. After edits: full verification (re-run the yardstick, new make target, anti demo, derived contract tests, confirm green + invariants + hermeticity + pillar alignment), then PR with the mandated elements.

The surface will embody Mechanical Sympathy (heavy, explicit), Semantic Rigor (precisely named Claim-B contract), and Third Door (composable lane via existing mechanisms, not the obvious two paths).

(End of ratification. No implementation code has been written.)