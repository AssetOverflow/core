# Ratification: Define Long-Term Architectural Posture for CLOSE-Derived Facts and FrameVerdict

**Date:** 2026-06-16  
**Branch:** `feat/define-close-derived-facts-frameverdict-posture` (fresh from `origin/main` at 7e5ac0ac which merges #794)  
**Governing brief:** "Title: Define Long-Term Architectural Posture for CLOSE-Derived Facts and FrameVerdict" (the query for this session)  
**Preceding work (locked):** #791 (Claim-B hardening of `evals/close_derived_climb` with `content_replay_checksum`, `semantic_positives_determined_direct`, `wrong_total=0`, full proposal posture), #792 (hermetic embedding recommendation), #793 (Dedicated CLOSE Flywheel Regression Surface: `make test-close-flywheel`, dedicated testing-lanes.md section, anti-regression participation), #794 (structured `proposal_review_posture` in the climb + `proposal_review_summary` (scenes + log_transitions + close_derived merge) in the anti-regression demo + visibility subsection in testing-lanes + cross-refs). Parallel B4 closed-world substrate (ADR-0222 + implementation lookback 2026-06-15).

## Context: The Two Lanes and the Recent Richness

CLOSE-derived facts are accretive, open-world products of the derivation / determine / consolidate / idle_tick path (under `RuntimeConfig.review_derived_close_proposals`). When the flag is on, eligible realized derived facts (derived=True, entailed derivation, speculative epistemic status, member/subset/TRANSITIVE_PREDICATES) are emitted as review-gated proposal-only artifacts (`source="derived_close_fact"`) carrying full derivation metadata, structure/dedupe keys, and explicit review posture (`status="proposal_only"`, `epistemic_status="speculative"`, `requires_review=true`). These are written under `teaching/proposals/derived_close_facts/` (or exercised via the older ProposalLog/ReviewState teaching-chain path in hermetic demos). Promotion to durable (corpus append or COHERENT via `apply_certified_promotion` or eligible paths) is always reviewed or proof-carrying (INV-29); nothing auto-promotes.

#791–#794 made the *review/ratification half* of this flywheel first-class observable inside the same composable heavy verification surface that already hosts Claim-B derivation measurement:
- `evals/close_derived_climb/runner.py` now surfaces `proposal_review_posture` (emitted_count, all_proposal_only, all_speculative, all_requires_review, review_eligible, none_accepted_or_promoted) derived from the already-returned proposal bodies.
- `evals/anti_regression/run_demo.py` now emits `proposal_review_summary` (scenes by review_state + log_transitions from exercised ProposalLog + close_derived merge of the climb posture).
- These appear in `--json` output, verbose RESULT blocks, `DemoReport`, the `make test-close-flywheel` lane, and `tests/test_anti_regression_demo.py`.
- All guarantees preserved: hermetic tempdir runs, `all_gates_held`, `active_corpus_byte_identical`, `wrong_total=0`, content_replay_checksum covering the proposal bodies, proposal-only/SPECULATIVE/requires_review asserted at emission.

(See `evals/close_derived_climb/contract.md`, the visibility ratification artifact, `docs/testing-lanes.md` "Dedicated CLOSE Flywheel Regression Surface" + new "Review / Ratification Posture..." subsection, `docs/runtime_contracts.md` Derived CLOSE proposal bridge section, and `chat/runtime.py:IdleTickResult.derived_close_proposals_emitted`.)

FrameVerdict (and ClosedFrame) is the B4 closed-world substrate (ADR-0222, implemented and lookback-audited 2026-06-15 on `feat/b4-frameverdict-complete`):
- `ClosedFrame` requires an explicit `world_assumption` (CLOSED / BOUNDED_CLOSED) + `closure_declared=True` + a complete enumerated proposition set. It is a *declared-complete snapshot* for the purpose of two-sided entailment/refutation.
- `FrameVerdict` is a sealed, distinct type (five `FrameVerdictKind`: ENTAILED_TRUE / ENTAILED_FALSE / UNDETERMINED / CONTRADICTION / SCOPE_BOUNDARY; carries `ClosedWorldProof` with positive-refutation discipline for both true and false cases). `__post_init__` enforces the negation law: `ENTAILED_FALSE` is illegal under `OPEN` (absence never false) and requires a named positive refutation (ROBDD_REFUTATION or PERCEPTION_CHANGED_SLOT).
- Construction is funneled through a single allowlisted site (`generate/frame_verdict/_construct.py:build_frame_verdict`). The evaluator (`evaluate_frame_verdict`) and perception adapter are the only producers. The path is deliberately default-dark / off-serving (no production callers into `disposition_for_frame_verdict`; `core.response_governance` package init does not re-export the adapter).
- It is *not* `Determined`; it never carries an `answer` bool.

INV-30 and INV-31 are the mechanical expression of the separation (non-vacuously verified in `tests/test_architectural_invariants.py` on every relevant PR):
- **INV-30 (Open-world DETERMINE never asserts False):** `determine()` produces only `Determined(answer=True, ...)` (three construction sites: direct, one-hop relational, transitive) or `Undetermined` refusals. Absence never refutes. "The open-world determination gear answers a question ONLY from what the held self has realized, under the OPEN-WORLD assumption".
- **INV-31 (Closed-world FrameVerdict cannot reach the open-world runtime):** Two-part firewall. (A) Transitive import containment (the open-world spine modules `chat.runtime`, `session.context`, `vault.store` must not reach `generate.frame_verdict` or `core.response_governance.frame_verdict`) + exact construction allowlist (only the one `_construct.py` file). (B) Typed data-flow ( `determine(ClosedFrame, ...)` refuses at the eligibility gate before ctx; forged/untagged objects are `TypeError` rejected at the sole disposition adapter).

The B4 lookback (2026-06-15) and subsequent relational work explicitly record "No FrameVerdict serving or default wiring", "No edits to ... FrameVerdict, closed-world reasoning", and full INV-30/31 green (128+ tests in the B4 slice, 74/74 in later snapshots).

## Current Relationship (Deliberate Non-Relationship)

There is **no data-flow, no type sharing, no import, and no semantic composition** between the CLOSE-derived proposal/fact lifecycle and FrameVerdict / ClosedFrame:
- CLOSE emission and consolidation live entirely in the open-world determine + epistemic (SPECULATIVE by default) + reviewed-teaching promotion path. The artifacts are intentionally "proposal-only, review-gated"; the contract in runtime_contracts.md states "no ... no determine change".
- A CLOSE-derived fact (even after review, corpus append, or promotion to COHERENT) is never packaged as a `ClosedFrame.propositions` set, never passed to `evaluate_frame_verdict`, and never used to construct a `FrameVerdict`.
- Conversely, a `FrameVerdict` (or `ClosedFrame`) is never injected into `determine()`, never becomes a premise in CLOSE derivation / consolidate, never appears in `IdleTickResult`, never participates in `ProposalLog` / teaching review states, and never affects epistemic_status or vault promotion.
- The two systems make incompatible assumptions: CLOSE facts are accretive (open-world accumulation from conversation + derivation; "I was told" / SPECULATIVE until reviewed), while a ClosedFrame is a *deliberately declared-complete* snapshot that licenses a committed two-sided verdict (including negation) under CWA or perception. Mixing them would be a category error.

The recent richness (#791–#794) lives *entirely inside* the CLOSE proposal/teaching surfaces and the dedicated heavy verification lane. It gives operators precise, contract-level, replayable signals about *how the review/ratification side of the flywheel behaves* (birth posture of every emitted artifact, transition counts from exercised gates in hermetic scenes, "none accepted inside the yardstick" guarantee) — without ever touching, observing, or depending on the closed-world lane.

## Evaluation of Strict Separation vs. Controlled Future Interaction

**Maintain strict deliberate non-interaction (recommended):**

- **Benefits.** Preserves the precise, non-negotiable meanings of the two lanes (Semantic Rigor). Keeps the B4 substrate sealed, default-dark, and off-serving until (if ever) a future dedicated serving PR discharges its recorded obligations (dataclasses.replace guard, etc.). Allows the CLOSE flywheel (both halves) to be measured, hardened, and evolved *inside its own surfaces* (the composable heavy lane just ratified in #793/#794) with zero cross-cutting cost or complexity. No new firewall surface, no new allowlist maintenance, no risk of subtle soundness interactions between accretive open facts and snapshot closed assumptions. The increased observability of review/ratification outcomes is already achieved without any bridge.
- **Risks of relaxing.** Low in the current state; the richness does not create technical pressure to cross the boundary for correctness or visibility. Any bridge (even "read-only use of COHERENT CLOSE facts as optional premises inside a declared-closed frame") would:
  - Require new or extended INV-31 construction/ import allowlists and new non-vacuous test anchors.
  - Require new INV-30-adjacent reasoning (does using a reviewed CLOSE fact inside CWA ever let absence become false elsewhere?).
  - Introduce a new semantic surface (what does "complete frame" mean over a body whose growth path was open + selective reviewed proposals?).
  - Add replay, provenance, and standing discipline obligations (a FrameVerdict proof over CLOSE-derived premises must not masquerade as open-world determination).
  - Impose Mechanical Sympathy cost (extra code, tests, scans, and review surface in both the derivation and the closed lanes).
- **Long-term implications.** The separation remains a load-bearing architectural commitment. The CLOSE flywheel can continue to grow richer (more predicates, better consolidation, finer review telemetry) without ever needing closed-world machinery for its own health measurement. B4 can mature independently toward (or away from) serving. Future operators inherit a clean, auditable distinction rather than an accreted hybrid.

**Allow any form of controlled interaction (even future-gated):**

- **Potential benefits.** In principle, a COHERENT CLOSE-derived fact (e.g. a transitive math relation proven through the derivation path) could serve as a high-quality premise inside a deliberately constructed ClosedFrame for a targeted CWA consistency check, or a FrameVerdict could inform a downstream teaching gate. This might strengthen certain verification scenarios or allow "closed snapshot over ratified CLOSE corpus subset" tooling.
- **Risks and costs (material).** The category mismatch (accretive open vs. declared-complete closed) is not a small impedance; it is the reason INV-30 and INV-31 exist. Any bridge creates a new trust boundary that must be proven not to create wrong>0 candidates, not to weaken the "absence never false" contract, and not to let a closed negation leak into open runtime surfaces. It would expand the INV-31 scan surface and the construction allowlist, increasing the cost of every future change on either side. It would require updates to runtime_contracts, the architectural invariants test, the B4 lookback obligations, and new dedicated ratifications. The visibility objective of the current brief (and #794) is already satisfied without it. The "Third Door" for richer measurement was the dedicated heavy lane, not a cross-world bridge.
- **Long-term implications.** Once a bridge exists, even if initially narrow and opt-in, pressure to widen it ("just this one more predicate", "just for serving disposition") becomes a recurring tax. The clean lane separation that lets each system be understood, tested, and evolved on its own terms erodes. The project would have to re-argue the pillars for every incremental mixing.

## Architectural Recommendation (Ratified Posture)

**Deliberate, long-term non-interaction is the architectural posture.**

CLOSE-derived facts (including the full proposal emission, review/ratification lifecycle under `teaching/proposals`, epistemic transitions from SPECULATIVE to COHERENT, and any promotion or corpus-append outcomes) shall not be used as direct or indirect premises for `ClosedFrame` construction or `FrameVerdict` evaluation. `FrameVerdict` outputs (and `ClosedFrame` contexts) shall not feed back into CLOSE derivation, `determine()`, idle consolidation, proposal emission, teaching review paths, vault promotion, or any open-world runtime surface.

The two systems address orthogonal concerns:
- CLOSE / derivation / reviewed teaching: open-world accumulation, sound inference under "as told", proposal-gated durable growth, exact CGA recall, replayable content checksums, and human/HITL ratification of what the autonomous half emits.
- FrameVerdict / closed-world: lane-scoped, declared-complete snapshot reasoning for positive refutation (ENTAILED_FALSE) or support (ENTAILED_TRUE) under explicit CWA or perception falsification assumptions; currently sealed and off-serving.

The increased richness and observability achieved in #791–#794 (structured birth posture, transition events in exercised gates, integration into the Claim-B + anti-regression heavy lane) *reinforces* rather than weakens this posture. We now have precise, contract-level, wrong_total=0, replayable telemetry on exactly the "review, accepted/rejected, and promoted into durable knowledge" side of the CLOSE flywheel — all without any data crossing the open/closed boundary or any change to FrameVerdict, determine, or the INV-30/INV-31 firewalls.

Any future proposal for controlled interaction (however narrow or "read-only") must be treated as a material architectural change. It requires:
- A new (or substantially amended) ADR.
- Explicit updates to (or extensions of) INV-30 and/or INV-31, with new non-vacuous test anchors.
- Re-verification that `wrong_total` remains 0 on all affected lanes, versor closure, epistemic standing rules (INV-21–24, INV-29), determination contracts, and proposal-only/review-gated boundaries.
- Fresh ratification artifact + updates to `docs/runtime_contracts.md`, `tests/test_architectural_invariants.py`, and the relevant B4 / CLOSE ratif family.
- Explicit alignment argument against the Three Engineering Pillars.

Until such a ratified change, the current strong separation (SPECULATIVE status + proposal-gated + INV-31 firewall + INV-30 open-world True-only) is the invariant.

## Alignment with Engineering Pillars (Whitepaper §IV)

- **Mechanical Sympathy:** The two lanes have different cost profiles and different hardware/implementation sympathies (open derivation + teaching HITL vs. ROBDD + perception falsification substrate). We do not add cross-cutting bridges, new shared allowlists, or hybrid data structures "because the data is now richer." Each lane pays only its own cost. The visibility work used the already-ratified heavy composable lane (Third Door) rather than inventing always-on reporters or fast-path CLI.
- **Semantic Rigor:** "Open-world determine" and "closed-world FrameVerdict" have precise, distinct meanings (absence never false; declared-complete snapshot licenses negation only with positive proof). CLOSE facts carry epistemic standing that is revised through review; a FrameVerdict carries a replayable closed entailment/refutation. We do not blur the terms or let one masquerade inside the other. The posture document makes the distinction durable and reviewable.
- **Third Door:** We did not take the "obvious" door of "now that we can see the proposals clearly, let's wire them into the closed-world substrate for extra power." Nor did we take the "just use the existing teaching reporter in isolation." We used the ratify-first discipline, wrote the decision artifact on disk before touching runtime_contracts.md, and produced a clean, load-bearing documentation update inside the existing contract surface. The composable heavy lane (make test-close-flywheel + anti demo) already provides the measurement; the posture formalizes why no further integration is required or desired.

## Verification Obligations (Post-Ratification)

- This ratification artifact exists on disk (written first).
- `docs/runtime_contracts.md` receives a substantial, self-contained addition documenting the posture, explicitly referencing this artifact, the B4 lookback, INV-30/INV-31, the #791–#794 richness, the Derived CLOSE proposal bridge section, and the Three Pillars.
- Git diff limited to `docs/analysis/*-ratification-2026-06-16.md` (this file) + the update to `docs/runtime_contracts.md`. Zero changes to any `.py`, Makefile, evals runners, tests, or other behavior.
- The full architectural invariants suite (`tests/test_architectural_invariants.py`) remains byte-identical and would continue to pass (INV-30/31 untouched).
- Existing CLOSE references in runtime_contracts.md (the visibility sentence added in #794) remain accurate; the new posture section is additive and consistent.
- `core test --suite smoke -q` (or equivalent) and the CLOSE-specific lanes continue to behave exactly as before (no behavior change by construction).
- All prior invariants (versor_condition, INV-21/22/23/24/29/30/31, proposal_only/SPECULATIVE/requires_review at emission, wrong=0, content_replay_checksum, hermeticity of the heavy lane, active_corpus_byte_identical) continue to hold by construction.

## References

- Governing brief (this session).
- CLOSE family: `docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md`, `close-derived-proposal-bridge-2026-06-16.md`, `close-flywheel-dedicated-regression-surface-ratification-2026-06-16.md`, `close-flywheel-proposal-review-visibility-ratification-2026-06-16.md`, `integrate-hardened-close-yardstick-determinism-teaching-regression-ratification-2026-06-16.md`.
- B4 / FrameVerdict: `docs/analysis/b4-frameverdict-implementation-lookback-2026-06-15.md`, `docs/handoff/b4-pr1-frameverdict-type-inv31-brief-2026-06-15.md`, ADR-0222.
- `docs/runtime_contracts.md` (Derived CLOSE proposal bridge §, determination surface, epistemic surface, provisional vs durable standing §, INV-30 reference).
- `tests/test_architectural_invariants.py` (INV-30 and INV-31 sections with exact claims and non-vacuity anchors).
- `generate/determine/determine.py` (Determined/Undetermined contract), `generate/frame_verdict/types.py` (ClosedFrame, FrameVerdict, __post_init__ guards, WorldAssumption, FrameVerdictKind), `generate/frame_verdict/_construct.py` (single construction funnel).
- `teaching/proposals.py` (ProposalLog, ReviewState, accept/reject/withdraw, events), `chat/runtime.py` (IdleTickResult, derived_close_proposals_emitted, the bridge emission).
- `evals/close_derived_climb/runner.py` + `contract.md` (posture), `evals/anti_regression/run_demo.py` (summary), `docs/testing-lanes.md` (Dedicated CLOSE section + review posture subsection).
- Engineering Pillars: `docs/Whitepaper.md` §IV.
- Core agent instructions (Claude.md / AGENTS.md / CLAUDE.md) ratify-first, INV discipline, lookback, pillar alignment, and "no hidden normalization / stochastic / approximate" rules.

**Ratification Status:** COMPLETE AND LOCKED. This artifact was created via the `write` tool on the clean branch *before any search_replace, write (other than this file), or other implementation edit to runtime_contracts.md, tests, evals, source, or any other documentation*. All preceding activity on this branch was git operations (fetch, checkout main, clean, branch creation) plus strictly read-only exploration (list_dir, read_file, grep with no edits). The decision is now on disk and may be referenced. Implementation of the required documentation update to `docs/runtime_contracts.md` (and only that) may now proceed exactly within the scope above. Any deviation, code change, or broadening requires a new ratification or explicit brief amendment.

---

*This ratification follows the project's ratify-first discipline for architectural posture decisions on core boundaries (open-world vs. closed-world, derivation vs. refutation, autonomous growth vs. reviewed ratification). It prioritizes clarity, intentionality, long-term alignment with the Three Engineering Pillars, preservation of INV-30/INV-31 and the epistemic proposal-only boundary, and the ability to measure the full CLOSE flywheel (both halves) inside its own composable heavy lane — over any temptation to mix lanes because one side has become more visible.*