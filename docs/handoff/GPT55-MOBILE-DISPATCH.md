# GPT-5.5 Mobile/GitHub-Connector Dispatch — In-Flight Work

**Audience:** GPT-5.5 accessed via mobile + GitHub connector while Shay travels
**Mode:** Read-only execution surface (no test runs, no eval runs, no Python
interpreter). Output is markdown files committed via the connector and PRs
opened against `AssetOverflow/core`.
**Risk profile:** Zero — every task is docs-only, no code paths touched, no
pack mutations, no runtime change. `wrong=0` cannot be violated.
**Cadence:** Pick one task. Complete it fully (including the PR open). Move
to the next. Don't parallelize — mobile + connector tooling is single-thread.

---

## Shared constraints

- Open one PR per task. Each is a separate branch off `origin/main`.
- Branch naming: `docs/gpt55-task-N-<slug>` where `N` is the task number.
- File staging: explicit. **Never** `git add -A`. **Never** commit
  `engine_state/`.
- Markdown-only output (CLAUDE.md §Documentation Discipline — no standalone
  HTML, no dashboards). Mermaid + `<details>` collapsibles permitted.
- Honour CLAUDE.md's existing doctrine sections; specifically:
  - §"Schema-Defined Proof Obligations" — any new schema you propose must
    name an executing test that can meaningfully fail
  - §"Non-Negotiable Field Invariant" — never propose anything that
    weakens `wrong=0` or the field invariant
  - §"Validation Through CLI" — refer to CLI lanes rather than ad-hoc
    pytest invocations
- Cite filenames + line numbers (`path/file.py:LINE`) for every code
  reference. Verify each reference resolves before committing.
- If a task's deliverable requires a code change (not docs), **stop and
  flag it in the PR body** — do not attempt code edits via the connector.

---

## Task 1 — Draft ADR-0168 (FrameClaim scoping)

**Branch:** `docs/gpt55-task-1-adr-0168-frameclaim`
**Output:** `docs/decisions/ADR-0168-frameclaim-ratification.md`
**Priority:** Highest (this is the next gate after the LexicalClaim slice)

### Context to read first

- `docs/decisions/ADR-0167-audit-as-teaching-evidence.md` — the parent
  scoping ADR with the five sub-types proposed
- `docs/handoff/ADR-0167-FOLLOWUPS.md` §1 — the queued sub-type work,
  specifically the FrameClaim row
- `teaching/math_lexical_ratification.py` — the LexicalClaim handler
  template (what your ADR's analogous handler would look like)
- `teaching/math_evidence.py` — `SUB_TYPE_FOR_OPERATOR` table; FrameClaim
  maps from `pre_frame_filler_sentence` and `multi_subject_sentence`
- `evals/gsm8k_math/train_sample/v1/audit_brief_11.json` — the 9
  `pre_frame_filler_sentence` cases your ADR will eventually resolve
- `evals/gsm8k_math/train_sample/v1/audit_brief_11.md` §"design tension"
  — the rejected one-line fixes and why they fail wrong=0; FrameClaim is
  the structural answer
- `language_packs/data/en_core_math_v1/lexicon/` — pack mutation surface
  for verb-category reclassification

### Deliverable shape

ADR-0168 must answer for FrameClaim what ADR-0167 answered for the
overall wire:

1. **Scope.** FrameClaim ratifies a verb-category reclassification.
   Specifically: when the operator reviews a `pre_frame_filler_sentence`
   refusal, FrameClaim's handler reclassifies the unrecognised verb
   from `drain_token` (or its current category) to a frame-opener
   category (`accumulation_verb` / `depletion_verb` / `transfer_verb` /
   `possession_verb` / `capacity_verb`).
2. **Why this is not LexicalClaim.** Reclassification is structurally
   different from adding a new lemma: it changes the frame-opening
   behaviour of an EXISTING entry. The hazard is real — reclassifying
   `does` to `accumulation_verb` would re-introduce the case 0050
   hazard (W2-D pinned this in `SAFE_CATEGORIES`).
3. **Six open questions (analogous to ADR-0167's).** Answer each in
   the ADR draft, not in code:
   - (Q1) What sub-types of FrameClaim are needed? (E.g. distinct
     handlers per target category, or one parameterised handler?)
   - (Q2) What new SAFE_CATEGORIES allowlist applies?
   - (Q3) How does the ratification prevent the case 0050 hazard?
     Concrete answer required, not hand-waved.
   - (Q4) What evidence signature normalisation does FrameClaim need?
     (Token-only, or token+target-category?)
   - (Q5) How does graph completeness gate this category change at the
     downstream solver level?
   - (Q6) What ablation test would prove this handler doesn't admit
     a graph for a sentence whose verb the operator declined to
     reclassify?
4. **Three-question test (ADR-0166).** Answer Q1/Q2/Q3 of ADR-0166
   for FrameClaim explicitly. If any of the three doesn't pass cleanly,
   say so — the ADR can defer rather than pretend.
5. **Implementation outline.** A wave structure analogous to
   ADR-0167's: which W1/W2/W3 deliverables, what operator-to-brief
   matching, what's parallelisable.

### PR body must include

- Link to ADR-0167 and FOLLOWUPS §1
- Quote the case 0050 hazard text from
  `feedback-wrong-zero-hazard-case-0050` memory (Shay can paste it)
- Explicit "docs-only; no code change" callout
- The recommendation: ship or defer? Whichever, defend it.

### Out of scope for this task

- Implementing FrameClaim. ADR is scoping only.
- Touching `teaching/`, `language_packs/`, or any test file.
- New eval lanes (ADR-0166 still gates).

---

## Task 2 — `discrete_count_statement` injector specification audit

**Branch:** `docs/gpt55-task-2-dcs-injector-spec`
**Output:** `docs/handoff/discrete_count_statement-injector-spec.md`
**Priority:** Highest-leverage (21/47 GSM8K refusals are this one category)

### Context to read first

- `evals/gsm8k_math/train_sample/v1/report.json` — the post-eval
  refusal records; filter for
  `"category=discrete_count_statement"` (21 cases)
- `evals/gsm8k_math/train_sample/v1/cases.jsonl` — original problem
  text for each of those 21 cases
- `generate/recognizer_match.py` — the `match` function that's
  over-matching
- `generate/recognizer_anchor_inject.py` — the `inject_from_match`
  function; the empty-tuple return path is the bug surface
- `engine_state/recognizers.jsonl` (read-only — **never commit this**)
  — the ratified recognizer specs including the
  `discrete_count_statement` canonical pattern
- `docs/decisions/ADR-0163-gsm8k-path-to-mastery.md` — the roadmap
  that introduced this recognizer
- `docs/decisions/ADR-0163.D.2-discrete-count-statement.md` (if it
  exists — locate and read it)

### Deliverable shape

A specification document, not an implementation. The document must:

1. **Categorise the 21 cases.** Read each problem text; group by
   sub-structure. Common shapes likely include:
   - "X has N <noun>" pure initial-state
   - "X has N <noun> and M <other-noun>" multi-quantity initial
   - "There are N <noun>" subject-anonymous initial
   - "N <noun> are <attribute>" attribute-on-count
   - Comparatives ("N more <noun> than M <noun>")
   The grouping is the load-bearing part — exact buckets aren't pre-
   determined; let the data dictate.
2. **For each sub-shape**, propose:
   - What `parsed_anchors` shape an injector would have to produce
   - What `CandidateInitial` / `CandidateOperation` it maps to
   - What admissibility check would catch wrong>0 admissions
   - Which sub-shapes are LexicalClaim-resolvable (e.g. just a missing
     noun) and which need FrameClaim / CompositionClaim
3. **Identify the over-matching root cause.** The recognizer's
   canonical pattern matches any number+noun. Propose specific
   tightening conditions (e.g. require a frame-opener verb, require
   the noun to be in a count-noun whitelist).
4. **Quantify the lift potential.** Of the 21, how many would resolve
   under each sub-shape's hypothetical injector? Be honest about
   which ones still wouldn't resolve even with the injector (they
   have downstream barriers — pronoun, fraction, etc.).
5. **Sequencing recommendation.** Which sub-shape's injector should
   ship first? Lift-per-risk, not raw count.

### PR body must include

- Per-sub-shape lift estimate (table)
- A statement that NO injector implementation is being proposed —
  this PR is specification only
- Cross-reference to ADR-0167-FOLLOWUPS §1 (FrameClaim) and
  §"discrete_count_statement over-matching"

### Out of scope for this task

- Implementing any injector
- Modifying the recognizer canonical pattern
- Touching `language_packs/` or `teaching/`
- Running the eval (you can't anyway)

---

## Task 3 — Recognizer registry audit

**Branch:** `docs/gpt55-task-3-recognizer-audit`
**Output:** `docs/handoff/ratified-recognizer-registry-audit.md`
**Priority:** Medium (informs Task 2 and future injector work)

### Context to read first

- `engine_state/recognizers.jsonl` (read-only) — the 7 ratified
  recognizers from #315 onward
- `generate/recognizer_match.py` — match logic
- `generate/recognizer_anchor_inject.py` — injection logic, including
  which categories have injectors and which return `()`
- The eval report from Task 2 — refusal-class counts per recognizer
  category

### Deliverable shape

A table-driven survey:

| Recognizer category | Match logic precision | Injector present? | GSM8K refusal count | Lift potential | Risk class |
|---|---|---|---:|---|---|
| `discrete_count_statement` | over-broad | no | 21 | high | high (case 0050 class) |
| `currency_amount` | ? | ? | 4 | ? | ? |
| `rate_with_currency` | ? | ? | 3 | ? | ? |
| ... | ... | ... | ... | ... | ... |

For each row, write a one-paragraph commentary explaining:
- What the recognizer is supposed to catch
- What it actually catches (the over-broadness or precision)
- Whether the injector is feasible (lexical-only? structural? multi-pack?)
- The case 0050 hazard analogue for THIS category

### PR body must include

- A "promote injector / tighten match / retire recognizer" recommendation
  for each row
- An "if you fix one, fix this one first" prioritisation

### Out of scope for this task

- Implementing any recognizer change
- Retiring any recognizer (proposal-only)
- Touching `engine_state/` directly — read-only

---

## Task 4 — FOLLOWUPS §6 ablation test specification

**Branch:** `docs/gpt55-task-4-holonomy-ablation-spec`
**Output:** `docs/handoff/holonomy-ablation-test-spec.md`
**Priority:** Low-urgency, high-information

### Context to read first

- `docs/handoff/ADR-0167-FOLLOWUPS.md` §6 (when merged from PR #360)
- `language_packs/compiler.py:558` — `_apply_mounted_primary_domain_resonance`
  (the architectural-invariant comment names the gap)
- `tests/test_alignment_graph.py:73` —
  `test_holonomy_alignment_case_positive_closer_than_negative` (the
  existing proof)
- `language_packs/schema.py:181` — `HolonomyAlignmentCase` schema

### Deliverable shape

A specification (not an implementation) for an ablation test that
isolates *structurally-derived* convergence from *blend-induced*
convergence. The spec must:

1. **Name the ablation surface.** What part of
   `_apply_mounted_primary_domain_resonance` needs to be temporarily
   disabled or parameterised for the test?
2. **Name the test contract.** With ablation active (blend factor = 0),
   does the positive-closer-than-negative assertion still hold? If
   yes, structural derivation is real; if no, the test is gated by the
   blend.
3. **Name the predicted outcome.** Best guess: blend-gated. Document
   why (the 40% nudge is sizeable; without it, the morphology rotors
   alone may not produce enough convergence).
4. **Name the honest reframing path.** If the ablation fails, the
   `HolonomyAlignmentCase` contract should be reframed from "proves
   structural divergence with coherent convergence" to "proves
   endpoint similarity under the mount-time blend." Suggest the exact
   docstring/schema text.

### PR body must include

- Cross-reference to FOLLOWUPS §6 and CLAUDE.md §"Schema-Defined Proof
  Obligations"
- Explicit "spec only; no test implementation in this PR" callout

### Out of scope

- Implementing the ablation test
- Modifying the holonomy test or schema
- Modifying `_apply_mounted_primary_domain_resonance`

---

## Task 5 — Cognition contemplation partition fix specification

**Branch:** `docs/gpt55-task-5-contemplation-partition-spec`
**Output:** `docs/handoff/contemplation-pack-indexing-partition-spec.md`
**Priority:** Medium (this is FOLLOWUPS §5a)

### Context to read first

- `docs/handoff/ADR-0167-FOLLOWUPS.md` §5a
- `docs/handoff/ADR-0167-W2C-cross-domain-audit.md` — Gemini's W2-C
  audit; the specific partition risks
- `teaching/contemplation.py::contemplate()` — the function that uses
  hardcoded cognition pack/corpus indexes
- `teaching/discovery.py` — `DiscoveryCandidate` with the `domain`
  field added by W2-C
- `language_packs/data/en_core_math_v1/` — what a math pack looks like
  (for the alternate-domain branch)

### Deliverable shape

A surgical patch specification (not an implementation):

1. **Inventory.** Which exact lines in `teaching/contemplation.py`
   assume cognition?
2. **Patch surface.** Minimum change to make those lines respect
   `candidate.domain`.
3. **Test surface.** What test(s) would catch a regression where a
   math candidate silently fetches cognition pack data?
4. **Backwards compatibility.** Confirm the default (`domain="cognition"`)
   preserves current behaviour byte-identically.

### PR body must include

- Cross-reference to W2-C audit and FOLLOWUPS §5a
- "Spec only; implementation in a follow-up PR" callout

### Out of scope

- Implementing the patch
- Touching `teaching/contemplation.py`
- Running cognition regression tests (you can't anyway)

---

## Operational notes

- **Pace yourself.** Mobile + connector tooling has latency. One task per
  session is honourable; trying to finish all five in one go invites errors.
- **Cite line numbers.** Every code reference must include `path:LINE` and
  be verified to resolve. If you can't verify via the connector, drop the
  specific line number and reference the function name instead.
- **No code edits.** If a task starts feeling like it needs a code change,
  flag it in the PR body and stop. Do not attempt code edits via the
  connector — the test discipline can't be honoured from mobile.
- **Honest progress reports.** Each PR's body should report what you
  actually concluded — including any sub-shapes you couldn't categorise,
  any line numbers you couldn't verify, any open questions that need
  Shay's input.
- **If you finish all five.** Open a meta-PR adding a section to
  `docs/handoff/ADR-0167-FOLLOWUPS.md` linking to all five spec docs.

## What NOT to attempt from the connector

- Implementing FrameClaim, CompositionClaim, or any other handler
- Implementing any injector for `discrete_count_statement` or any other
  recognizer category
- Implementing the holonomy ablation test
- Implementing the contemplation partition fix
- Running `core test --suite *` or `core eval cognition` (mobile cannot)
- Mutating any pack file under `language_packs/data/`
- Committing anything under `engine_state/`
- Force-pushing or rewriting history on any branch

If in doubt, the rule is: **specs and audits, not implementation.**

---

## Cross-references (for context)

- `CLAUDE.md` — project doctrine
- `docs/decisions/ADR-0166-measurement-capability-sequencing.md` — the
  three-question test every spec must answer
- `docs/decisions/ADR-0167-audit-as-teaching-evidence.md` — the parent
  wire all five sub-types extend
- `docs/handoff/ADR-0167-FOLLOWUPS.md` — the canonical follow-up queue;
  Tasks 1, 2, 4, 5 all extend items already named there
- `docs/decisions/SESSION-2026-05-27-adr-0167-parallel-dispatch.md` —
  the wave narrative; reading this gives the full context for why each
  task is shaped the way it is
