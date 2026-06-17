# Ratification: Integrate Hardened CLOSE Yardstick into Determinism & Teaching Regression Surfaces

**Date:** 2026-06-16  
**Author:** Grok (following user brief)  
**Branch:** feat/integrate-hardened-close-yardstick-determinism-teaching (freshly created)  
**Base:** Clean fetched main @7a20356a (post #791 merge; working tree explicitly restored to clean before branch)  
**Brief reference:** "Title: Integrate Hardened CLOSE Yardstick into Determinism & Teaching Regression Surfaces" (High priority; strict "ratify first" workflow required)

**Context (verbatim from brief + prior state):**
PR #791 merged the hardening of `evals/close_derived_climb` to full Claim B level. It now exercises/measures via *lived* paths:
- `ChatRuntime.idle_tick()` + `IdleTickResult.derived_close_proposals_emitted` (real flag gating, not simulation)
- Explicit `determine()` calls asserting `Determined(True, rule='direct')` on positive probes post-materialization ("semantic_positives_determined_direct")
- `content_replay_checksum` over canonical closure sets (structure_key + Derivation + premise_structure_keys) + proposal bodies (in addition to aggregate replay_checksum)
- All original Claim A preserved (1→5→8 monotone/strict growth on is-a + relational-transitive, wrong_total=0, negatives/excluded preds refused, determinism, no serving/ratification mutation, SPECULATIVE/proposal_only only, INV-21/29/30/31 etc.)

The yardstick (`uv run python -m evals.close_derived_climb` or direct `from evals.close_derived_climb import run`) is currently manual-only. Its value as recurring protection for the CLOSE flywheel (autonomous derived-fact growth + gated proposal emission) is not realized in standard regression flows.

Immediate post-merge verification (on fresh main) already confirmed the Claim B behaviors live on main.

## Ratification Decision

**Before any implementation code was written, the chosen approach is:**

Execute a *minimal, hermetic, documentation-primary + demo-embedding integration* with exactly these targeted changes (and nothing broader):

1. **Determinism regression surfaces (docs + test config/scripts):**
   - Add a prominent "Recommended determinism / teaching regression invocation (post-Claim-B hardening of CLOSE yardstick)" section in `docs/testing-lanes.md` (the single auditable source of truth for lanes, determinism reruns, make targets, hermeticity rules, and "standard verification story").
   - Document the exact command `uv run python -m evals.close_derived_climb` (plus the contract pytest pair `tests/test_derived_close_proposals.py tests/test_architectural_invariants.py -q`) as a recurring step for determinism reruns, to be run alongside/after `core test --suite ...` or `make test-*` lanes.
   - Make a tiny, comment-only update in `Makefile` under the test-fast/test-slow/test-full targets (and the header) referencing the CLOSE Claim-B command so operators following the make lanes are pointed at the full verification story. No behavior change to targets.
   - Result: the hardened yardstick (with its content checksum + semantic + lived IdleTickResult) becomes part of the *recommended* determinism regression flows without any modification to `_TEST_SUITES` in core/cli.py, without new suite entries, without marker changes, and without CLI additions.

2. **Teaching / anti-regression demo flows (hermetic embedding of the yardstick):**
   - Edit `evals/anti_regression/run_demo.py` (the implementation behind `core demo anti-regression`, the explicit "teaching/anti-regression demonstration flow" referenced in README, docs/evals/, and cli epilog examples).
     - Import `run` from `evals.close_derived_climb` (already exposed via __init__).
     - Execute `climb_report = run()` inside the demo (the climb is fully hermetic: per-run fresh `ChatRuntime(no_load_state=True)`, internal temp only for the flag-proposal sink patch, zero writes to production teaching corpus / engine_state / shared proposal sinks).
     - Surface the critical Claim-B evidence additively in `DemoReport` / `run_demo` return / `as_dict()` under a new key `"close_derived_climb"` (or nested), including at minimum: `wrong_total`, `proposals_only_with_flag`, `content_replay_checksum`, `semantic_positives_determined_direct` aggregates, and growth numbers.
     - In the human RESULT section (when not --json), print a one-line summary of the CLOSE flywheel check (e.g. "CLOSE derived climb yardstick (Claim B): wrong_total=0, proposals gated by lived idle_tick+IdleTickResult, content_replay_checksum stable, semantic direct determines passed").
   - This *adds the yardstick (its execution + its key metrics)* directly into the anti-regression demo flow.
   - Minor supporting update in `tests/test_anti_regression_demo.py`: add 1-2 assertions on the new key (e.g. `assert "close_derived_climb" in report; assert report["close_derived_climb"]["aggregate"]["wrong_total"] == 0`) so the integration is pinned by the contract tests. Existing 5 tests' assertions remain untouched and will continue to pass.
   - Why here? The anti-regression demo is the load-bearing "anti-regression demos" surface for teaching-loop protection. CLOSE is the complementary autonomous-growth protection (derived close facts + gated speculative proposals). Embedding it here makes the demo a joint surface without conflating the concerns or touching `teaching/` review/ratification code.

3. **Update supporting documentation (with cross-references):**
   - `docs/testing-lanes.md` (as above; also ensure the new section references hermeticity rules, the prior Claim-B ratification, this ratification, contract.md, and the anti_regression_demo.md).
   - `evals/close_derived_climb/contract.md` (update the "Run:" line to the project-standard `uv run python -m ...`; add "Integrated into determinism lanes (testing-lanes.md) and anti-regression demo (see anti_regression_demo.md + this ratification)" + links).
   - `docs/evals/anti_regression_demo.md` (add a short "Complementary CLOSE flywheel protection" subsection noting that `core demo anti-regression` now also runs the hardened yardstick and surfaces its invariants; link to contract.md and the two ratifications).
   - (If natural: a one-sentence cross-ref in `docs/runtime_contracts.md` under the determination surface section noting that semantic answerability for realized derived facts is now exercised by the CLOSE yardstick's `determine(..., rule='direct')` asserts.)
   - This ratification artifact itself (placed in docs/analysis/ per project pattern for such decisions).
   - No other dependent references required updates (confirmed via tree-wide grep before ratification; only self + historical analysis ratif + source + git history mentioned the new metrics).

4. **Hermeticity + safety preservation (non-negotiable, verified at each step):**
   - Every change respects the hermeticity requirements documented in `docs/testing-lanes.md` (isolation of writers, temp dirs for proposals/logs, no races, byte-identity where claimed).
   - The CLOSE runner already satisfies this (explicit TemporaryDirectory + DEFAULT_SINK patch only for the one flag test; no persistent side effects).
   - The anti demo already wraps its ProposalLog in `with tempfile.TemporaryDirectory()`.
   - Embedding the call does not introduce new shared state or non-determinism.
   - **Zero** changes to: core engine, `chat/runtime.py`, `generate/*` (except the already-shipped derived_close), `teaching/`, `vault/`, proposal review/ratification, FrameVerdict, `RuntimeConfig` defaults, invariants, serving paths, or any mutation rules.
   - All existing behavior, `wrong_total=0` guarantee, content-level determinism, and replay checksums preserved.

**Why this is the *only* correct path (and must not be broadened):**

- It is the smallest set of changes that satisfies the Objective ("Integrate ... so it runs as part of the standard verification story") and every Success Criterion while obeying every Constraint and the "Required Workflow (Strict)" (ratify artifact *before writing any implementation code*; branch from clean main; stay in Scope's four areas; end with PR containing the mandated summary elements).
- It directly addresses the brief's "What’s Next (The Right Path)" recommendation from the immediate post-merge actions: promote into determinism regression runs + teaching/anti-regression demos + make the improved checksum/semantic checks "part of the default verification story".
- It makes the protection *recurring and automated* exactly where the project already runs verification (documented lanes + `core demo anti-regression` which is exercised in tests + by humans following the cli examples).
- Any broader or different approach would violate constraints:
  - Adding a new entry to `_TEST_SUITES` + updating cli.py + test_cli_test_suites.py would be a CLI addition (explicitly "Out of Scope") and broad config refactor.
  - New make targets or changes to lane mechanics would be infrastructure refactoring (out of scope).
  - Touching teaching/queue/review or core cognition paths would risk invariants and is out of scope.
  - Duplicating yardstick logic or creating a new harness would waste the already-hardened Claim-B implementation and add non-determinism risk.
- Ratifying this exact path *first* (this artifact) guarantees subsequent edits cannot drift; the PR will be auditable against this document.
- Highest leverage / lowest surface area: the yardstick code itself is left untouched (its hardening stands on its own); value is realized purely by wiring it into the *existing* surfaces via docs (primary, always-run recommendation) + one hermetic call site in the demo (actual execution during anti-regression verification).

**Success criteria this ratification guarantees will be true post-implementation (and will be re-verified before PR):**
- Hardened yardstick invocable as part of standard determinism regression flows (via updated lanes doc + Makefile comments + core test / make usage patterns).
- Referenced and executed inside teaching/anti-regression demonstration paths (`core demo anti-regression` now carries the CLOSE evidence).
- All existing tests + architectural invariants + `core test --suite teaching` etc. remain green.
- Hermeticity preserved (no new writers, no corpus/engine_state pollution, xdist-safe).
- Documentation (testing-lanes, contract, anti_regression_demo.md, this ratif) accurately reflects usage and cross-refs.
- The yardstick now provides recurring, automated, Claim-B-strength protection for the CLOSE flywheel inside the project's normal verification story.

**References (must be linked in PR description):**
- This ratification: `docs/analysis/integrate-hardened-close-yardstick-determinism-teaching-regression-ratification-2026-06-16.md`
- Prior Claim-B hardening ratification: `docs/analysis/close-derived-climb-yardstick-claim-b-ratification-2026-06-16.md`
- Yardstick contract + runner: `evals/close_derived_climb/contract.md` + `runner.py`
- Anti-regression demo surface: `evals/anti_regression/run_demo.py` + `tests/test_anti_regression_demo.py` + `docs/evals/anti_regression_demo.md`
- Lanes / hermeticity: `docs/testing-lanes.md` + `Makefile`
- Runtime contracts (determination surface): `docs/runtime_contracts.md`
- Post-merge verification commands (to be re-run): `uv run python -m evals.close_derived_climb` + `uv run python -m pytest tests/test_derived_close_proposals.py tests/test_architectural_invariants.py -q`

**Ratification Status:** COMPLETE. This artifact was written on the branch *before any search_replace, edit, or other implementation code touched source files, tests, scripts, or docs (other than creation of this file itself)*. All exploration was read-only (git, list_dir, read_file, grep). 

Implementation may now proceed, strictly limited to the four areas above, followed by thorough verification (re-running the post-merge commands + targeted core test / demo runs + full relevant pytest) and PR creation with the exact mandated description contents.

(End of ratification. The single correct path is now locked.)
