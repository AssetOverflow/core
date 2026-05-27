# Matcher Extension — Dispatch Pack (ME-1)

**Goal:** Light up the dormant consumption path in PR #398 by extending
the recognizer matcher to publish `composition_shape` + a pre-composed
`CandidateInitial` in `parsed_anchors`. With this PR, the math
compounding loop's `ratify → admit` closure becomes operational for
the `each`/`per`-framed cost composition shape — and case 0019
admits.

**Parent briefs:**
- `docs/handoff/COMPOSITION-FRAME-CONSUMPTION-WIRING-BRIEF.md` (PR #396)
- `docs/handoff/CONSUMPTION-WIRING-DISPATCH-PACK.md` (PR #397)
- PR #398 — the consumption-wiring implementation (merged into context)

**Parent ADRs:** ADR-0163 (recognizer registry), ADR-0167, ADR-0168 / 0168.1,
ADR-0169 / 0169.1, ADR-0170 (injector contract widening), ADR-0172

**Type:** Implementation dispatch; not a doctrine ADR

---

## Why this brief exists

PR #398 shipped the consumption infrastructure (compile, loaders,
manifest, injector consultation). All 38 new tests pass. But the
truth-test rows #1 and #3 (case 0019 admits; train_sample 3/47 →
≥4/46) **partial**: the wiring is positioned correctly but stays
dormant because the existing matchers don't publish
`composition_shape` in `parsed_anchors`.

PR #398 §"Scope Boundary" named this finding. This brief is the
follow-up.

The matchers in `generate/recognizer_match.py`:

| Matcher | Currently | Needs to |
|---|---|---|
| `_match_rate_with_currency` | Extracts `(currency_symbol, amount, per_unit)` per anchor; **detection + extraction** | Detect the outer count in the same sentence; emit `composition_shape` + `composed_initial` when count is present |
| `_match_currency_amount` | Detection-only (returns empty anchors); refuses if per-unit framing present | **Out of scope** — this matcher's discriminator deliberately rejects per-unit framing |
| `_match_multiplicative_aggregation` | Detection-only; matches "M outer × N inner" shape | **Out of scope** (Phase B follow-up) — multiplicative_aggregation maps to a different solver shape than `currency_per_unit_rate` |

So the minimum-scope extension is **`_match_rate_with_currency`**.

---

## Bundling rule

**One PR.** Single matcher extension + injector wire for the
per-unit-cost composition shape. Don't bundle multi-quantity_composition
or additive_composition cases into this brief — those are separate
matcher targets and each carries its own subject-binding risk.

Branch: `feat/matcher-extension-currency-per-unit-composition`

---

## Operator profile

**Opus** (load-bearing wrong=0 surface; the matcher extension produces
a `CandidateInitial` whose value is the product of two recognized
quantities — same hazard surface as CC-2, with case 0050 as mandatory
pin).

---

## Dispatch

```bash
git fetch origin main && \
  git worktree add /tmp/wt-matcher origin/main && \
  cd /tmp/wt-matcher && \
  git checkout -b feat/matcher-extension-currency-per-unit-composition
```

---

## Reads required FIRST

- `generate/recognizer_match.py`:
  - `_match_rate_with_currency` (lines 290–344) — the extension target
  - `RecognizerMatch` dataclass (line 139) — `parsed_anchors` is `tuple[Mapping[str, Any], ...]`
- `generate/recognizer_anchor_inject.py`:
  - `inject_from_match` (lines 73–98) — already consults composition_registry on `composition_shape`
  - `_consult_composition_registry` (lines 100–170) — the contract: matcher must publish `composition_shape` + `composed_initial` OR `composed_operation`
- `generate/comprehension/composition_registry.py` — `is_affirmed`, `is_falsified`, allowlist
- `generate/math_candidate_parser.py::CandidateInitial` — required fields:
  `(initial, source_span, matched_anchor, matched_value_token, matched_unit_token, matched_entity_token)`
- `generate/math_problem_graph.py::InitialPossession, Quantity`
- Case 0019 audit row in `evals/gsm8k_math/train_sample/v1/audit_brief_11.json`
- The literal text of case 0019 in `evals/gsm8k_math/train_sample/v1/cases.jsonl`
- `tests/test_composition_consult_in_injector.py` — the synthetic-anchor tests
  showing the consumption path admits when given populated anchors
- `tests/test_consumption_case_0050_hazard_pin.py` — the case-0050
  parametrized canary

---

## The target case

**Case 0019:**

> "John adopts a dog from a shelter. The dog ends up having health
> problems and this requires 3 vet appointments, which cost $400
> each. After 2.5 years of these appointments John discovers that his
> dog's appointments are only 50% covered by insurance. How much did
> John pay total?"

The sentence that triggers the composition is:

> "The dog ends up having health problems and this requires 3 vet
> appointments, which cost $400 each."

Recognized data the extended matcher must bind:

- outer count: **3**
- unit cost: **$400**
- per-unit token: **each**
- currency symbol: **$**

Pre-composed admission target:

```python
CandidateInitial(
    initial=InitialPossession(
        entity=<resolved_subject>,   # see "Subject binding" below
        quantity=Quantity(value=1200, unit="dollars"),
    ),
    source_span="3 vet appointments, which cost $400 each",
    matched_anchor="cost",
    matched_value_token="1200",       # the composed value as a token
    matched_unit_token="dollars",
    matched_entity_token=<resolved_subject>,
)
```

`composition_shape = "bound(count) × bound(unit_cost)"`
(must match the surface_pattern an operator ratifies in
`compositions/multiplicative_composition.jsonl`)

---

## Subject binding (the load-bearing decision)

The CandidateInitial requires a non-empty `entity`. Case 0019's
sentence ("The dog ends up having health problems…") has no human
subject in the same sentence — "John" lives in sentence 0.

**Three options, pick one (recommend Option A):**

### Option A — Refuse when same-sentence subject is absent

The matcher checks the statement for a recognized proper-noun subject.
If absent (case 0019's situation), the matcher returns `None` for the
composition extension — falling back to the existing detection-only
behavior. **The composition admission does NOT fire for case 0019.**

This is honest refusal-preferring: cross-sentence subject binding is
its own hazard surface (the wrong subject = wrong arithmetic
attribution).

If you choose Option A, case 0019 stays refused — the brief's truth
test #1 is still **partial** for THIS PR. Pick a different canary
sentence with same-sentence subject (e.g. construct a synthetic case
where the subject IS in the same sentence).

### Option B — Use a placeholder subject (DISCOURAGED)

Insert `entity="anonymous"` or similar. **Strongly discouraged** —
this fabricates a subject and pollutes the candidate graph. The
solver may produce a "correct" total but attribute it wrongly, which
is structurally the same shape as case 0050 hazard (correct-looking
trace, wrong attribution).

Forbidden unless explicitly approved.

### Option C — Cross-sentence subject lookup

Make the matcher consult prior-sentence state to find the most recent
proper-noun entity. This requires either:

- threading sentence-state context into the recognizer match path
  (currently the matcher only sees one sentence at a time), or
- extending `RecognizerMatch` with an optional `prior_subject` field
  populated upstream

Either is a larger surface than a single PR should land. **Defer to
its own brief.**

### Recommendation

**Ship Option A**, document the case-0019 gap as "requires Option C"
in the PR body, and demonstrate the truth-test fires via a
**purpose-built test case** that has same-sentence subject. Example:

> "Maria bought 3 vet appointments, which cost $400 each."

For Maria-with-3-appointments: count=3, unit_cost=400, subject=Maria
(same sentence) → CandidateInitial(entity="Maria", quantity=$1200).

Add this case to `evals/gsm8k_math/train_sample/v1/cases.jsonl` as a
synthetic test case OR write a stand-alone Python test that builds
the recognizer match directly and verifies admission.

---

## Outcome

### Modules touched (minimum scope)

1. **`generate/recognizer_match.py`**:
   - Extend `_match_rate_with_currency` (or add a sibling helper
     called from it) that:
     - detects an outer count token in the same statement
     - parses the count + per-unit cost
     - resolves the subject under Option A (same-sentence
       proper-noun extraction; refuse otherwise)
     - constructs the pre-composed `CandidateInitial`
     - publishes the anchor with keys `composition_shape`,
       `composed_initial`, `currency_symbol`, `amount`, `per_unit`,
       `outer_count`, `subject` (for debug/audit)

2. **`generate/recognizer_anchor_inject.py`** — **no changes**.
   The consumption wire from PR #398 already handles `composition_shape`
   + `composed_initial`. This PR proves it lights up.

### Manifest / pack changes

**None.** The operator must separately ratify
`bound(count) × bound(unit_cost)` under `multiplicative_composition`
via `apply_composition_claim()` — that ratification already exists in
the canonical pack (or can be re-ratified). The matcher extension
makes the existing dormant ratification load-bearing.

---

## Hard requirements

- **Refusal-preferring.** Subject absent → matcher does NOT emit a
  composition anchor. The existing currency_per_unit_rate detection
  path continues to fire (no regression).
- **Outer-count parse narrowness.** The outer count must be a single
  integer or known number-word adjacent to a counted noun (mirror
  `_match_discrete_count_statement`'s narrowness layers). Multi-count
  or ambiguous → refuse the composition extension.
- **Per-unit token in observed set.** Only fire when the matched
  per-unit token (e.g. "each", "per") is in the spec's
  `observed_per_units` (existing narrowness from
  `_match_rate_with_currency`).
- **`composition_shape` MUST match a SAFE category.** The matcher
  emits `"bound(count) × bound(unit_cost)"` — the operator's
  ratification of this exact pattern under
  `multiplicative_composition` is what lights it up. Any other
  shape string is forbidden.
- **Pre-composed value is `int` or `float` per `Quantity` invariants.**
  Compute `outer_count * unit_cost`; if either is non-numeric,
  refuse.
- **Source-span requirement.** `source_span` must be a verbatim
  substring of the statement (existing CandidateInitial discipline).
- **Case 0050 hazard pin.** The matcher extension MUST NOT cause
  case 0050 to admit. The extension's narrowness must reject case
  0050's sentence shape (which has no per-unit framing of this
  form).
- **No new eval lanes** (ADR-0166).
- **No solver / parser / decomposer mutation** (ADR-0169
  §"Mutation boundary").

---

## Tests

### `tests/test_matcher_extension_currency_per_unit.py`

1. **`test_outer_count_extracted_with_subject`** — synthetic sentence
   "Maria bought 3 vet appointments, which cost $400 each."; matcher
   returns anchor with composition_shape + composed_initial(value=1200, entity="Maria")
2. **`test_subject_absent_refuses_composition_extension`** — case 0019's
   exact sentence "The dog ends up having health problems and this
   requires 3 vet appointments, which cost $400 each."; matcher
   returns the existing rate anchors but does NOT publish
   composition_shape (Option A)
3. **`test_per_unit_token_outside_observed_set_refuses`** — narrowness
   guard
4. **`test_multiple_counts_refuse_composition`** — narrowness guard
   (refusal-preferring on ambiguity)
5. **`test_count_word_form_admits`** — "Maria bought three vet
   appointments at $400 each" → composed_initial(value=1200)
6. **`test_negative_or_zero_count_refuses`**
7. **`test_currency_symbol_outside_observed_refuses`**
8. **`test_emits_canonical_unit_dollars`** — `Quantity.unit == "dollars"`
   for `$` symbol

### `tests/test_matcher_extension_case_0050_hazard_pin.py`

1. **`test_case_0050_does_not_emit_composition_shape`** — feed case
   0050's actual sentences through the extended matcher; assert no
   anchor carries `composition_shape`. Mandatory; runs in CI.

### `tests/test_matcher_extension_end_to_end_admission.py`

The TRUTH TEST for this PR:

1. **`test_synthetic_maria_admits_via_composition_registry`** — start
   from a clean pack, ratify `bound(count) × bound(unit_cost)` under
   `multiplicative_composition`, run the candidate-graph pipeline
   on the synthetic Maria sentence, assert the result is a correct
   admission (not refusal).
2. **`test_train_sample_case_0019_partial`** — explicit test
   documenting case 0019's refusal-preserving status under Option A
   (refuses because cross-sentence subject; not a bug, an honest
   gap). Comment names Option C as the next brief.

### `tests/test_matcher_extension_train_sample_baseline_preserved.py`

1. **`test_train_sample_counts_unchanged_or_better`** — full
   `train_sample` reader-on eval; assert `correct >= 3`, `wrong == 0`,
   `refused <= 47`. Any improvement is a bonus; no regression is
   mandatory.

### `tests/test_matcher_extension_public_split_preserved.py`

1. **`test_gsm8k_math_public_150_150_preserved`** — `core eval
   gsm8k_math --split public --json` returns `cases_total=150`,
   `correct=150`, `wrong=0`, `refused=0`. Mandatory.

---

## Truth test (binding 6-row table for this PR)

| # | Assertion | How to verify |
|---|---|---|
| 1 | Synthetic Maria sentence admits | `test_synthetic_maria_admits_via_composition_registry` passes |
| 2 | Case 0050 stays refused | `test_matcher_extension_case_0050_hazard_pin.py` passes |
| 3 | `train_sample` `correct ≥ 3`, no regression | full train_sample reader-on run; report green |
| 4 | `wrong == 0` preserved (train_sample) | same |
| 5 | `public` split 150/150 unchanged | `core eval gsm8k_math --split public --json` |
| 6 | All PR #398 tests still pass | `core test --suite packs -q` green |

Row #1 replaces the original case-0019 row from PR #397's truth test
(case 0019 stays refused under Option A; that's a Option C concern,
not this PR).

---

## Anti-regression invariants

- `wrong == 0` on `core eval gsm8k_math --split public` preserved
- Case 0050 stays refused under the parametrized hazard pin
- ADR-0166 — no new eval lanes
- ADR-0167 partition — matcher remains math-domain only
- Empty composition_registry runtime byte-identical to today
- `SAFE_COMPOSITION_CATEGORIES` enforced at write AND load
- Refusal-preferring discipline: subject-absent → no composition emission
- `engine_state/*` never committed
- Pinned-lane SHAs may move (intentional `correct` delta if admission
  fires); call out the move in the PR body

---

## Forbidden surface

- Option B (placeholder subject) — fabricates entity attribution
- Option C (cross-sentence subject) — defer to its own brief
- New SAFE_COMPOSITION_CATEGORIES entries (this PR is read-only over
  the existing allowlist)
- Mutating `_match_currency_amount` (its discriminator is correct;
  don't conflate)
- Mutating `_match_multiplicative_aggregation` (different shape;
  separate brief)
- Adding new ShapeCategory values
- Solver / parser / decomposer / arithmetic-operator mutation
- Manifest schema changes (PR #398 already added the optional
  composition_checksum field)

---

## What ships when this PR lands

- One matcher extension at `_match_rate_with_currency`
- 12+ new tests
- The first case (synthetic Maria) admits via the
  ratify → compile → load → consume → admit chain
- `train_sample` counts improve OR stay at baseline (no regression)
- The dormant consumption path in PR #398 becomes load-bearing for
  the per-unit-cost composition shape
- Case 0019 remains refused — but explicitly under documented
  scope-boundary, not under structural unknown

## Sequencing

- **No upstream blocker** beyond PR #398 landing on main.
- **Subsequent briefs** (each its own PR):
  - **ME-2:** Cross-sentence subject binding (Option C); admits case 0019
  - **ME-3:** Multi-quantity_composition matcher (8 audit cases)
  - **ME-4:** Additive composition matcher (independent named quantities)
  - **ME-5:** Subtractive composition matcher

Each subsequent brief carries its own canary case + truth test.

---

## Memory pointers

- [[project-ratification-consumption-gap-2026-05-27]] — the original finding
- [[feedback-ratify-vs-consume-loop-closure]] — pattern
- [[feedback-wrong-zero-hazard-case-0050]] — mandatory pin
- [[feedback-production-line-pattern]] — dispatch pattern
- [[feedback-parallel-agent-worktrees]]
- [[feedback-address-critiques-dont-waive]] — Option A is the honest
  refusal-preferring choice; Option B is the convenient cheat that
  this brief explicitly forbids

---

## Copy-paste dispatch line

```text
Read docs/handoff/MATCHER-EXTENSION-DISPATCH-PACK.md (entire file).
git fetch origin main && git worktree add /tmp/wt-matcher origin/main && cd /tmp/wt-matcher && git checkout -b feat/matcher-extension-currency-per-unit-composition
```

Operator instruction sequence:
1. Read this brief plus the three "parent briefs" + ADR-0169 + the four `Reads required FIRST` files.
2. Implement the matcher extension in `_match_rate_with_currency` (or a sibling helper) per Option A.
3. Write the 12 tests across the four test files.
4. Run the 6-row truth-test sequence end-to-end.
5. Confirm all 6 rows hold before opening PR.
6. PR title: `feat(matcher-extension): currency-per-unit composition admission (ME-1)`.

---

## Decision summary

This PR closes the "consumption path is dormant" finding from PR #398
**for the simplest possible composition shape** (currency × per-unit
count). It does NOT close case 0019 — that requires cross-sentence
subject binding (Option C) and is the next brief.

The honest scoping: ship the matcher extension, prove the loop runs
end-to-end on a synthetic case where same-sentence subject binding
holds, leave case 0019 as the next domino. The flywheel turns one
revolution.
