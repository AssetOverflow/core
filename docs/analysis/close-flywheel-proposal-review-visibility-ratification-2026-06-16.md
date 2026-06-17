# Ratification: Strengthen Visibility and Measurement of the Proposal Review / Ratification Side of the CLOSE Flywheel

**Date:** 2026-06-16  
**Branch:** `feat/strengthen-close-flywheel-proposal-review-visibility` (fresh from `origin/main` at 9736dcc0 which includes #793)  
**Governing brief:** "Title: Strengthen Visibility and Measurement of the Proposal Review / Ratification Side of the CLOSE Flywheel" (the query for this session)  
**Preceding work (locked):** #791 (Claim-B hardening of `evals/close_derived_climb`), #792 (integration recommendation + embedding), #793 (Dedicated CLOSE Flywheel Regression Surface via `make test-close-flywheel` + dedicated section in testing-lanes.md + hermetic anti-regression participation).

## Context and the Gap

The CLOSE flywheel (comprehend → realize_derived → determine → CLOSE consolidate / idle_tick → proposal emission under `review_derived_close_proposals`) now has strong, Claim-B measurement on the *derivation and autonomous growth* half:

- Lived `ChatRuntime.idle_tick()` + `IdleTickResult.derived_close_proposals_emitted`
- `proposal_flag` + `only_with_flag` guarantee (proposals emitted **only** when the flag is on; zero without)
- `content_replay_checksum` over canonical closures (structure_key + Derivation with premise_structure_keys) + proposal bodies
- `semantic_positives_determined_direct` via explicit post-fixed-point `determine(..., rule='direct')` asserts
- `wrong_total=0`, strict/monotone growth, proposal_only + SPECULATIVE + requires_review posture on every emitted artifact, hermetic fresh_ctx runs

(See `evals/close_derived_climb/runner.py`, `evals/close_derived_climb/contract.md`, `tests/test_derived_close_proposals.py`, `docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md`, the dedicated surface ratification, and the bridge ADR doc `close-derived-proposal-bridge-2026-06-16.md`.)

The **review / ratification half** (the operator/HITL-gated path that takes a `status=proposal_only / epistemic_status=speculative / requires_review=true` artifact and moves it to accepted → corpus append or coherent promotion) has been the weaker half for observability:

- Emission artifacts (in `teaching/proposals/derived_close_facts/*.json` for the bridge, or via `ProposalLog` events for the older chain path) carry explicit review posture fields, but these are not aggregated or asserted as first-class signals in the main reporting surfaces.
- `DemoReport` (anti-regression) already captures per-scene `review_state` ("pending", "auto_rejected_on_regression", "rejected_pre_replay", "pending_awaiting_operator") and replay_evidence for the *teaching chain proposal* path (ADR-0057). It now also embeds the full climb yardstick. No combined review-outcome aggregates or CLOSE-specific review posture summary.
- `IdleTickResult` surfaces the *emission count* (`derived_close_proposals_emitted`) but not review/ratification outcomes (by design — review is HITL, not autonomous).
- `ProposalLog` (teaching/proposals.py) is an append-only event log with `record_transition(to="accepted|rejected|withdrawn")` and `accepted_corpus_append` events. These events exist and are exercised by the anti-regression scenes (S2 produces a rejected transition via the regression gate inside propose), but are not surfaced as structured counts or "ratification signals" in `DemoReport` or `core demo anti-regression --json`.
- The derived CLOSE artifacts are intentionally *parallel* to (or consumable by) the existing read-only proposal review reporter pattern (see historical `docs/analysis/proposal-review-reporter-2026-06-07.md` for the comprehension-failures precedent). No structured "how many of these specific proposals reached accepted/rejected, with what notes, producing what append events" measurement is present in the heavy verification lane.
- Vault promotion (SPECULATIVE → COHERENT via `apply_certified_promotion` or eligible promotion paths) is separate from teaching corpus extension; CLOSE derived facts can flow either as proposals or as consolidated determinations, but the "proposal review / ratification side" named in the brief is the gated proposal path.

The brief explicitly requires **measurement and visibility only** — no changes to review logic, policy, `accept_proposal`/`reject_proposal`/`review_correction`, `FrameVerdict`, closed-world reasoning, `teaching/*` mutation paths, or `RuntimeConfig` semantics.

## Ratification Decision (Chosen Approach)

**Introduce additive, structured proposal-review visibility exclusively through the already-established Dedicated CLOSE Flywheel Regression Surface (the anti-regression demo + embedded Claim-B climb yardstick + `make test-close-flywheel` lane).**

Concretely (post-ratif):

1. **Extend `evals/close_derived_climb` output (additively, in runner + contract)**:
   - From the already-captured `proposal_flag.proposals` list (the full emitted bodies), derive and surface a `review_posture` (or `proposal_review_posture`) sub-object:
     - `emitted_count`
     - `all_proposal_only: bool`
     - `all_requires_review: bool`
     - `all_speculative: bool`
     - `review_eligible: int` (same as emitted; documents the "born review-gated" invariant)
     - `none_promoted_or_accepted: bool` (structural guarantee of the yardstick — no review path is exercised inside the climb itself)
   - Retain `content_replay_checksum` (already covers proposal bodies). This makes the *review posture at emission time* a first-class, checksum-protected, wrong_total=0 Claim-B signal.
   - Update `contract.md`, runner docstring, and `__init__.py` summary only (no behavior change to emission or any runtime path).

2. **Extend `evals/anti_regression/run_demo.py` + `DemoReport` (additively, hermetic, building directly on the #792 embedding)**:
   - Add an optional `proposal_review_summary: dict | None = None` (and/or `close_proposal_review`) field to `DemoReport`.
   - In `run_demo`, after the three scenes + the existing `close_derived_climb = run_close_derived_climb()` call:
     - Aggregate from the existing `SceneResult` objects (they already carry `review_state`, `operator_note`, `replay_evidence`): counts by terminal review state, any "accepted_corpus_append" style signals if present in the temp log events for the demo's `ProposalLog`.
     - Merge / surface the climb's new `review_posture` (or the raw emitted proposals' review flags) as a `close_derived` subsection.
     - Optionally, for the demo's own ProposalLog (tmpdir-isolated), read the event stream post-scenes and count `transition` events by "to" state and `accepted_corpus_append` events. This gives a deterministic "ratification events observed during exercised gates" signal without ever calling the public `accept_proposal` on a path that would write the live active corpus (the demo's S3 is deliberately pending-only; any transition counts come from S2's internal auto-reject path or explicit log inspection).
   - In the verbose RESULT block and `as_dict()`, include the new summary so `--json` output and `core demo anti-regression` carry the signals.
   - The `all_gates_held` and `active_corpus_byte_identical` invariants remain unchanged and are still the primary success criteria.

3. **Light doc updates only (no code behavior)**:
   - `docs/testing-lanes.md`: Extend the "Dedicated CLOSE Flywheel Regression Surface (Claim-B Level)" section (the one added in #793) with a new subsection "Review / Ratification Posture and Events (the previously weaker half)" describing the new signals, their purpose (visibility into acceptance/rejection rates, review outcomes, promotion-adjacent events for the CLOSE-derived proposals), expected characteristics (still heavy, hermetic, proposal-only/SPECULATIVE guarantees are *asserted*, not bypassed), and the ratif link.
   - `docs/evals/anti_regression_demo.md`: Note that the demo now also participates in review/ratification visibility for the embedded CLOSE surface.
   - `evals/close_derived_climb/contract.md`: Add the new posture signals to the "What the yardstick measures" list + ratif reference.
   - `docs/runtime_contracts.md`: One-sentence tightening (if needed) that the determination + proposal emission contracts now have corresponding review-posture observability in the dedicated lane.
   - Cross-reference the new ratif artifact and the prior dedicated-surface ratif.

4. **No other changes**:
   - No modifications to `teaching/review.py`, `teaching/proposals.py` (beyond any trivial additive helper if a pure read function proves useful — but prefer direct inspection of public `ProposalLog.events()` / `find()` and the climb's already-returned dicts), `vault/store.py`, `generate/determine/derived_close_proposals.py`, `chat/runtime.py`, `IdleTickResult`, `accept_proposal`/`reject_proposal`, or any ratification/promotion policy.
   - The anti-regression scenes continue to leave passing proposals in "pending_awaiting_operator"; any new summary merely observes states and events that the existing gate machinery already produces.
   - `make test-close-flywheel` and the pytest contract pair (`test_anti_regression_demo.py` etc.) will transitively cover the new signals.
   - All existing hermeticity (temp dirs, no_load_state, fresh corpora, byte-identical active checks, no engine_state writes in the lane) is preserved.

**Primary surface:** the Dedicated CLOSE Flywheel Regression Surface (Claim-B) via `make test-close-flywheel` (or direct `uv run python -m evals.close_derived_climb` + the anti demo). This is explicitly positioned for heavier determinism + teaching/anti-regression verification, not fast local or CI — exactly as ratified in #793.

## Why This Is the Only Correct Path (Alignment with Scope, Constraints, and Engineering Pillars)

**Mechanical Sympathy (Whitepaper §IV):** The review/ratification half is inherently heavier and more HITL-dependent than pure autonomous derivation. We do not hide cost or make it "free" by adding always-on reporters, new CLI commands, or inclusion in `core test --suite smoke/fast` or CI. We extend the *explicitly heavy, opt-in, documented* lane (`make test-close-flywheel`) that already hosts the Claim-B derivation yardstick. Operators who care about the full flywheel (including the review posture of what the autonomous half emits) pay the cost intentionally. No new infrastructure.

**Semantic Rigor (Whitepaper §IV):** We give the review side *precise, named, contract-level signals* (`review_posture.all_requires_review`, `proposal_review_summary.by_state`, transition counts from the event log, "none promoted inside the yardstick" guarantees) rather than ad-hoc prints or sidecar files. The signals are derived from the same artifacts the bridge and ProposalLog already emit (status, epistemic_status, requires_review, transition events). The yardstick continues to fail loudly (wrong_total, posture violations, checksum drift) if the review-gated contract is violated at emission time. Documentation in testing-lanes.md + contract.md makes the contract legible.

**Third Door (Whitepaper §IV + the composable verification style in testing-lanes.md and the #793 ratification):** We do not invent a new `core close review-stats` command, a new pytest marker, a new `_TEST_SUITES` entry, or a broad `teaching/` refactor. We use the *existing composable lane mechanism* (the dedicated make target + the anti-regression demo as the canonical teaching-gate verification harness + the embedded climb) that was just ratified and documented days ago. This is the "third door": a small, load-bearing, additive extension inside the already-approved heavy surface. It is hermetic, additive, and discoverable by anyone following `make test-close-flywheel` or reading the dedicated section.

**Strict scope adherence and invariant preservation:**
- Only measurement/visibility (structured dicts in existing report shapes).
- Zero changes to proposal review logic, acceptance policy, FrameVerdict, closed-world, or any mutation path.
- All new data is either (a) already returned by public hermetic runners (climb proposals list) or (b) already written by the exercised gate code into temp ProposalLogs (events()).
- proposal_only / SPECULATIVE / requires_review boundaries are *asserted more visibly*, never relaxed or bypassed.
- wrong_total=0, determinism, replayability, content-addressing, and the "active corpus byte identical" contract of the anti demo remain the success criteria.
- The ratification artifact itself is written *before* any search_replace/write on source, tests, or other docs.

Alternative paths considered and rejected (as part of ratif reasoning):
- Adding a standalone `core proposal-review-stats` or new module under `core/`: violates "no new CLI", "no heavy infra", "Third Door / composable", and Mechanical Sympathy (would look like a fast-path tool).
- Instrumenting inside `accept_proposal` / `reject_proposal` or `review_correction`: changes (or appears to change) the review logic; broad touch on teaching/; out of scope.
- Running real accepts inside the anti demo that mutate the live teaching corpus: breaks the demo's hermetic "never writes active" contract and the "active_corpus_byte_identical" gate.
- Broadly enhancing IdleTickResult with review outcome counts: review is not part of the autonomous tick (by design and by INV-29/30); would be misleading and would require runtime changes.
- Updating the old comprehension-failure reporter in isolation: the brief is specifically about the *CLOSE* flywheel's proposal review side (the bridge + derived_close_facts path now exercised by the Claim-B yardstick).

The chosen path is the minimal, precise, pillar-aligned, scope-respecting, hermetic extension that makes the previously weaker half first-class *inside the surface that was just created for exactly this class of heavier CLOSE verification*.

## Verification Obligations (Post-Impl)

- `make test-close-flywheel` (or the two commands) must pass with the new signals present in JSON output and verbose text.
- `core demo anti-regression --json` must include the review summary/posture blocks; `all_gates_held` and `active_corpus_byte_identical` must remain true.
- `tests/test_anti_regression_demo.py` (and the other contract tests) remain green; the new fields are additive so existing assertions are unaffected or lightly extended only for presence/shape.
- Manual spot-check: emitted CLOSE proposals in the climb output continue to show `status: "proposal_only"`, `epistemic_status: "speculative"`, `requires_review: true`; the new posture object affirms the same.
- No diff in any production proposal review or promotion code paths (git diff limited to reporting/demo/docs + this ratif).
- All prior invariants (versor_condition, INV-21/22/23/24/29/30, wrong=0, SPECULATIVE default, proposal-only for derived CLOSE, etc.) continue to hold by construction.

## References

- Brief for this work + Required Workflow / Scope / Success Criteria / Constraints (this session's query).
- Dedicated CLOSE Flywheel Regression Surface ratification: `docs/analysis/close-flywheel-dedicated-regression-surface-ratification-2026-06-16.md`
- Claim-B yardstick hardening + integrate ratifs (2026-06-16).
- Bridge: `docs/analysis/close-derived-proposal-bridge-2026-06-16.md` (and the earlier proposal-review-reporter-2026-06-07.md for precedent style).
- `docs/testing-lanes.md` (Dedicated section + "How the surface builds on prior work").
- `evals/close_derived_climb/contract.md`, `evals/anti_regression/run_demo.py`, `chat/runtime.py:IdleTickResult`, `teaching/proposals.py:ProposalLog + ReviewState + accept/reject`, `vault/store.py` (promotion boundaries).
- Engineering Pillars: `docs/Whitepaper.md` §IV.
- Runtime contracts: `docs/runtime_contracts.md` (determination + proposal emission sections).

**Ratification Status:** COMPLETE AND LOCKED. This artifact was created via the `write` tool on the clean branch *before any search_replace, write (other than this file), or other implementation edit to Makefile, source, tests, evals runners, or any other documentation*. All preceding activity was git operations (fetch, checkout main, ff, branch creation, clean of stray artifacts) plus strictly read-only exploration (list_dir, read_file, grep with no edits). Implementation may now proceed exactly within the scope above. Any deviation requires a new ratification or explicit brief amendment.

---
*This ratification follows the project's ratify-first discipline for architectural and cross-cutting measurement changes on core flywheels. It prioritizes clarity, intentionality, long-term alignment with the Three Engineering Pillars, hermetic composable lanes, and preservation of every listed invariant over expedience or automatic inclusion.*