# L9 brief — ADR-0131.G.1 — Capability axis: state-introducing verb classes

**Worktree setup (do this first, non-negotiable):**

```bash
git worktree add ../core-adr-0131-g1-verb-classes -b feat/adr-0131-g1-verb-classes origin/main
cd ../core-adr-0131-g1-verb-classes
```

**Scope.** First capability-axis iteration on top of ADR-0131.G's coverage probe. Extends the **initial-possession candidate emitter** to recognize a closed set of *state-introducing* verbs beyond the current `has/have/is/are/was/were`. Target verbs (drawn directly from the baseline `refused_reasons_top` clusters in `train_sample_coverage_report.json`): `bought / buys`, `sells`, `collected`, `saved (up)`, `started (with)`, `had`, `makes` *(rate-introducing — only the initial-state reading, not the rate reading; that's L11/G.3's axis)*.

The architectural claim: each of these verbs introduces a quantity into the same `InitialPossession` shape `<Entity> <verb> <N> <unit>` — semantically equivalent to `has`, syntactically distinct. The candidate emitter widens; the binding graph and solver are untouched.

**Reference docs (read these, only these):**
1. `docs/decisions/ADR-0131.G-gsm8k-coverage-probe.md` — the iteration discipline; every G.<n> must do all 4 items in its "Every subsequent ADR-0131.G.<n> must" section.
2. `generate/math_candidate_parser.py` — extend `_INITIAL_HAS_RE` / `CandidateInitial` (do not branch into a new module; this is the same shape with a wider anchor alternation).

**What to ship:**
- **Parser extension** in `generate/math_candidate_parser.py`: widen `CandidateInitial.matched_anchor` validation set and `_INITIAL_HAS_RE` anchor alternation to include the listed verbs. Past-tense forms (`bought`, `collected`, `saved`, `had`, `started`) are first-class. Round-trip filter stays the firewall — wider grammar, same wrong-rate-zero.
- **Curated coverage cases** at `evals/math_capability_axes/G1_verb_classes/v1/cases.jsonl` (~20 cases, split by verb): each is `<Entity> <verb> <N> <unit>.` followed by a question the existing pipeline can answer. These exercise the new capability **independently of GSM8K**.
- **Runner** at `evals/math_capability_axes/G1_verb_classes/v1/runner.py` (pure adapter over `evals.gsm8k_math.runner` infrastructure or `chat/runtime` end-to-end; deterministic `report.json`).
- **Tests** at `tests/test_adr_0131_G1_verb_classes.py` (~10): safety rail (`wrong == 0`) on the new axis; per-verb at-least-one passing case; closed outcome vocab; replay byte-equality; **GSM8K probe re-runs and `admission_rate` strictly increases** vs the baseline `0.0`; B3 lane unchanged.
- **ADR** `docs/decisions/ADR-0131.G.1-verb-classes-initial-state.md`. Cite ADR-0131.G parent; document the closed verb set as a scope statement; declare what is *not* added (no rate verbs, no comparatives, no acquisition-with-cost semantics — those are sibling axes).
- **Refresh** `evals/gsm8k_math/train_sample/v1/train_sample_coverage_report.json` (the diff-able number). PR title must include the new admission_rate.

**Hard constraints:**
- **Closed verb set.** Every added anchor is enumerated in the ADR and in code. No paraphrase tolerance, no synonym expansion.
- **`wrong == 0`** preserved on both the new axis lane and the GSM8K probe. If round-trip would let a wrong answer through on any new verb, **shrink the verb set**, do not weaken the filter.
- **Initial-state reading only.** `makes` in "Tina makes $18.00 an hour" is rate-introducing — that case must continue to refuse (or route to L11). Verify with an explicit adversarial probe case.
- **No new modules under `algebra/`, `chat/`, `core/`.** No changes to the binding graph, solver, or verifier.
- **Determinism.** Report byte-equal across runs.
- **Smell test (ADR-0131.G):** if admission moves on GSM8K but the new axis cases don't all pass, the change is a template in disguise — reject.

**Out of scope:** rate verbs (L11/G.3), comparatives (L10/G.2), conjoined subjects (L12/G.4), commerce-with-price semantics, multi-statement coreference.

**Target branch.** PR against `main`. Title: `feat(ADR-0131.G.1): state-introducing verb classes — admission N/50 (Δ+N from baseline)`. Body: new admission_rate, refused_reason delta vs baseline, per-verb case counts, link to ADR.

**Exit criterion.** CI green; new axis runner exits 0 with `wrong == 0`; GSM8K probe `admission_rate` strictly increases; B3 lane unchanged; refreshed coverage report committed.

**Do not stack on another agent's branch.** Target main directly.
