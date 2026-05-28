# Verb-Coverage Expansion — Dispatch Pack

**Goal:** Widen the narrowness boundary that gates `discrete_count_statement`
admission so the held-hypothesis substrate landed in ADR-0174 Phase 3a
has cases to act on. Concretely: review the 11 verbs surfacing in
`evals/gsm8k_math/train_sample/v1` empty-anchor refusals and decide,
per verb, whether to add to `_ACQUISITION_VERBS` / `_POSSESSION_VERBS`,
add to a new depletion-verb class, or refuse and route to a different
recognizer category.

**Parent ADRs:** ADR-0163 (path to GSM8K mastery), ADR-0150/0152/0155/0161
(contemplation → proposal → HITL → ratification corridor), ADR-0167
(audit-as-teaching-evidence), ADR-0174 (held-hypothesis comprehension)

**Parent briefs:**
- `docs/handoff/PHASE-3.1-FOLLOWUP-RECOGNIZER-EXPANSION.md` — analysis
  identifying the verb-coverage bottleneck.

**Type:** Implementation dispatch + operator decision pack; not a
doctrine ADR. Touches a hardcoded narrowness boundary so every
acceptance is operator-reviewed and individually justified against the
`wrong = 0` invariant.

---

## Why this brief exists

ADR-0174 Phase 3a (PR #423) shipped the lookback substrate
(`reevaluate`, `PronounResolution`, held-hypothesis emission). The
substrate is correct and tested but **does not fire on any
train_sample case** because all 21 empty-anchor
`discrete_count_statement` refusals fail at the verb-whitelist layer
**before** reaching the pronoun-resolution check.

The whitelist lives in `generate/recognizer_match.py`:

```python
_POSSESSION_VERBS: Final[frozenset[str]] = frozenset({
    "has", "have", "had",
})

_ACQUISITION_VERBS: Final[frozenset[str]] = frozenset({
    "collected", "collects", "collect",
    "received", "receives", "receive",
    "bought", "buys", "buy",
    "got", "gets", "get",
})
```

This is a deliberate narrowness boundary, not registry-derived data.
Widening it is a code change with operator review (not a pack
mutation through the HITL corridor). The brief below produces the
evidence the operator needs to decide each verb.

---

## Bundling rule

**Multiple PRs, one per verb class (not one per verb).** Each PR
ships:

1. The narrowness expansion in `generate/recognizer_match.py`
2. A test in `tests/test_adr_0174_phase3_lookback.py` (or sibling)
   asserting the widened class admits cases the held-hypothesis
   substrate now handles
3. A `wrong = 0` proof against `train_sample/v1` AND case 0050 (the
   canary).

Three suggested PRs, each independently mergeable:

- **VE-A — Acquisition widening** (`feat/verb-expansion-acquisition`)
  Adds reviewed acquisition verbs to `_ACQUISITION_VERBS`.
- **VE-B — Depletion class introduction** (`feat/verb-expansion-depletion`)
  Adds a new `_DEPLETION_VERBS: Final[frozenset[str]]` and routes
  it to `CandidateOperation(kind="subtract")`. Includes its own
  `anchor_kind="depletion"` branch in
  `inject_discrete_count_statement`.
- **VE-C — Refusal-typed evidence** (`feat/verb-expansion-non-arithmetic`)
  For verbs that should NOT widen any whitelist (the verb does not
  grammatically denote possession / acquisition / depletion), emit a
  structured refusal-evidence record so the contemplation lane can
  decide whether a new recognizer category is needed (e.g.
  `capacity_statement`, `descriptive_action_frame`). No production
  whitelist changes; just better trace.

VE-A and VE-B are independent. VE-C requires nothing in the others.
All three can be in flight in parallel.

---

## Operator profile

- **Opus** for VE-A (load-bearing wrong=0 surface — widening the
  acquisition class touches every train_sample case via the recognizer
  pipeline). Case 0050 hazard pin is mandatory.
- **Opus** for VE-B (adds an entirely new operation-kind path; same
  wrong=0 hazard surface). Includes the depletion-class case-0050 hazard
  check (a depletion-verb addition must not flip case 0050 from refused
  to wrong).
- **Sonnet** for VE-C (instrumentation-only; no production behavior
  change). Tight scope, no architectural risk.

---

## The 11 verbs — recommended classification

Each row is the operator's input for the dispatch. Final
classification is the operator's call after reviewing the contemplation
evidence; this column is a recommendation only.

| Verb (lemma) | Surface forms in evidence | Recommended | Why |
|---|---|---|---|
| `gain` | gained, gains, gain | **Acquisition** (VE-A) | Grammatically gains quantity to actor: "Orlando gained 5 pounds" → +5. Hazard: `gained` can be delta-of-attribute (weight, age) — the existing `_ACQUISITION_VERBS` comment explicitly excludes it for this reason. Operator must confirm. |
| `earn` | earned, earns, earn | **Acquisition** (VE-A) | Same shape as `gained`; safer because monetary/discrete-count semantics are more uniform. |
| `save` | saved, saves, save | **Acquisition** (VE-A) | Ambiguous per existing comment ("saved time" vs "saved money"). Refusal-preferring approach: require the noun class (time vs money) to gate admission. |
| `accumulate` | accumulated, accumulates, accumulate | **Acquisition** (VE-A) | Unambiguous. |
| `acquire` | acquired, acquires, acquire | **Acquisition** (VE-A) | Unambiguous. |
| `donate` | donated, donates, donate | **Depletion** (VE-B) | Grammatically removes quantity from actor: "The bookstore donated 48 boxes" → -48. Subject is the giver. |
| `give` | gave, gives, give | **Depletion** (VE-B) | Same shape as `donate`. Existing `TRANSFER_VERBS` handles `give to X` — depletion is the no-target form. |
| `lose` | lost, loses, lose | **Depletion** (VE-B) | "She lost 3 marbles" → -3. Hazard: `lost` can semantically invert direction in comparisons ("Alice lost 3 more than Bob"). Existing comparison code excludes `lost` for this reason. Depletion-class addition must preserve that exclusion in comparison contexts. |
| `spend` | spent, spends, spend | **Depletion** (VE-B) | Money-class depletion; safer than `lose` because monetary context constrains semantics. |
| `eat` | eats, ate, eat | **Depletion** (VE-B) | "The guests eat 1 pan" → -1. Constrained to food-noun classes for safety. |
| `bench presses` / `splits` / `runs` / `bakes` / `invests` / `is` / `wants` | — | **Non-arithmetic** (VE-C) | These verbs do NOT carry possession/acquisition/depletion semantics. Routing them through the discrete_count_statement recognizer is the wrong intent. They want a separate recognizer category (e.g. `rate_statement`, `capacity_statement`, `descriptive_frame`) that is out of scope for this brief. |

### Hazard pinning — non-negotiable

Every VE-A / VE-B PR MUST include a test that asserts case 0050
remains refused after the widening:

```python
def test_case_0050_remains_refused_after_verb_widening(self) -> None:
    """gsm8k-train-sample-v1-0050 is the wrong=0 canary. The verb
    widening must NOT flip it from refused to wrong."""
    from generate.math_candidate_graph import parse_and_solve
    text = (
        "Mark does a gig every other day for 2 weeks. "
        "He gets paid $50 per gig. He then gets a 50% raise. "
        "How much money does he make per week?"
    )
    r = parse_and_solve(text)
    assert r.answer is None, (
        f"case 0050 wrong=0 hazard violated: verb widening admitted "
        f"answer {r.answer!r}; must remain refused"
    )
```

Reference: memory `feedback-wrong-zero-hazard-case-0050`.

---

## Per-PR workflow

### VE-A — Acquisition widening

```bash
git fetch origin main && \
  git worktree add /tmp/wt-ve-a origin/main && \
  cd /tmp/wt-ve-a && \
  git checkout -b feat/verb-expansion-acquisition
```

Touchpoints:
- `generate/recognizer_match.py:835` — add reviewed lemmas to
  `_ACQUISITION_VERBS` frozenset. Each addition has an inline comment
  citing the hazard review (e.g. `# Reviewed 2026-MM-DD: 'gained'
  grounds as monetary/discrete-count delta; refuses on
  delta-of-attribute via unit-noun class check upstream.`).
- `generate/math_roundtrip.py:60` — ensure each added lemma is also
  in `ADD_VERBS` so `roundtrip_admissible.verb_registered` passes.
- New tests in
  `tests/test_adr_0174_phase3_lookback.py::TestVerbExpansionAcquisition`
  covering: (1) each added verb admits a synthetic
  pronoun-subject sentence through the held-hypothesis path,
  (2) case 0050 remains refused, (3) at least one real train_sample
  case lifts from refused to correct.

Acceptance:
- ≥ 1 case lift on train_sample/v1 (verify via `uv run python -m
  evals.gsm8k_math.train_sample.v1.runner`)
- wrong=0 preserved across train_sample AND case 0050
- smoke 67/67, packs 141+/141+, lanes 8/8
- All Phase 1–3a tests still pass (113 baseline)

### VE-B — Depletion class introduction

```bash
git fetch origin main && \
  git worktree add /tmp/wt-ve-b origin/main && \
  cd /tmp/wt-ve-b && \
  git checkout -b feat/verb-expansion-depletion
```

Touchpoints:
- `generate/recognizer_match.py` — add
  `_DEPLETION_VERBS: Final[frozenset[str]]` near
  `_ACQUISITION_VERBS`. Extend `_try_extract_discrete_count_anchor`'s
  verb dispatch to include `elif verb in _DEPLETION_VERBS: anchor_kind
  = "depletion"`.
- `generate/recognizer_anchor_inject.py` — add
  `anchor_kind == "depletion"` branch in
  `inject_discrete_count_statement`; emits
  `CandidateOperation(kind="subtract")` via a new
  `_build_operation_from_discrete_count_depletion` helper that
  mirrors the existing acquisition helper but with `kind="subtract"`.
- `generate/math_roundtrip.py` — ensure each depletion lemma is in
  `SUBTRACT_VERBS`.

Acceptance:
- Synthetic depletion test passes (e.g. "Sam has 10 apples. He gave 3
  apples to a friend. How many apples does Sam have?")
- ≥ 1 case lift on train_sample/v1 from the depletion class
- wrong=0 preserved across train_sample AND case 0050
- Comparison-context hazard: "Alice lost 3 more than Bob" must not
  parse as depletion (already excluded from comparison verbs).

### VE-C — Non-arithmetic refusal evidence

```bash
git fetch origin main && \
  git worktree add /tmp/wt-ve-c origin/main && \
  cd /tmp/wt-ve-c && \
  git checkout -b feat/verb-expansion-non-arithmetic
```

Touchpoints (no production behavior change):
- `generate/recognizer_match.py` — in
  `_try_extract_discrete_count_anchor`, when the verb is not in any
  whitelist, augment the existing `return None` with a marker on the
  anchor (something like
  `_DISCARDED_VERB_TRACE: dict[str, list[str]] = {}` that captures
  the verb + sentence for downstream inspection). DO NOT emit
  candidates; the production path remains a clean refusal.
- New CLI surface: `core teaching unrecognized-verbs --since <case-id>`
  that surfaces the captured verbs as candidate evidence for a future
  ADR-0163.D.x recognizer-category proposal.

Acceptance:
- All 7 non-arithmetic verbs surface in the new CLI output when run
  against train_sample/v1.
- No score change; no admission behavior change.
- Refusal trace events gain a `verb_class_unknown` outcome with the
  verb lemma.

---

## Truth tests

Before any VE-A/B/C PR merges, verify:

1. **wrong=0 invariant.** `uv run python scripts/verify_lane_shas.py`
   passes. `train_sample/v1` report counts have `wrong: 0`.
2. **Case 0050 canary.** Explicit test that 0050 remains refused.
3. **Lift evidence.** For VE-A and VE-B, at least one train_sample
   case moves from `refused` to `correct`. If zero lift, the PR is
   premature — the verb widening exposed no real case, indicating the
   hazard isn't justified. Refuse to ship and re-scope.
4. **Phase 3a substrate fires.** For VE-A and VE-B, the lifted case
   must show a `lookback` trace event with
   `outcome: "admitted"` — proving the held-hypothesis path was on
   the critical path, not bypassed by the regex parser.

---

## Out of scope

- Comparison-verb additions (`compare_additive` / `compare_multiplicative`).
  ADR-0123 owns that surface.
- Rate-verb additions. ADR-0122 / ADR-0163.D.2.2 own that surface.
- Transfer-verb additions (`give to X`, `send to X`). Already covered
  by `TRANSFER_VERBS`; widening that is a separate brief.
- Verb-class proposals that would change the **structure** of
  `_try_extract_discrete_count_anchor`'s narrowness chain (e.g.
  registry-loadable verb sets). That is its own ADR; this brief
  preserves the hardcoded boundary because that boundary is the
  wrong=0 safety surface.
- ADR-0174 Phase 3b (compound-clause held hypotheses). Wait until
  VE-A or VE-B lands so the compound-clause logic has cases to admit.

---

## Sequencing recommendation

```
VE-C (instrumentation)
  ↓
VE-A (acquisition widening) ─┐
                              ├─→ measure: does Phase 3a lookback fire?
VE-B (depletion class)       ─┘    if yes: ADR-0174 Phase 3b
                                   if no:  re-scope non-firing cause
```

VE-C is independent and can land first to give us better evidence on
which Phase 3b targets are worth pursuing. VE-A and VE-B can land in
parallel; their case-0050 tests are independent.

---

## Reads required FIRST (for the operator running each VE-x)

- `generate/recognizer_match.py:812-840` — current verb-set
  definitions and the design comments justifying each exclusion.
- `generate/recognizer_match.py:912-1010` — the discrete-count
  anchor extractor (the narrowness chain).
- `generate/math_roundtrip.py:60-150` — `KIND_TO_VERBS`,
  `ADD_VERBS`, `SUBTRACT_VERBS` (must add lemmas here too for
  `roundtrip_admissible` parity).
- `generate/recognizer_anchor_inject.py:186-300` — injector dispatch;
  depletion needs its own builder.
- `docs/handoff/PHASE-3.1-FOLLOWUP-RECOGNIZER-EXPANSION.md` —
  empirical analysis this brief operationalises.
- Memory: `feedback-wrong-zero-hazard-case-0050` (case 0050 hazard
  is mandatory pinning for every PR).
- Memory: `thesis-decoding-not-generating` (each verb decision is
  "does this teach the engine to find better?" — non-arithmetic
  verbs route to VE-C precisely because widening for them would be
  "storing another found thing").

---

## Decision needed before dispatch

- **Authorise VE-A acquisition widening?** Specifically: which of
  `gain`, `earn`, `save`, `accumulate`, `acquire` (and their
  inflections) are in scope. Each adds a `wrong=0` hazard surface.
- **Authorise VE-B depletion class introduction?** Specifically:
  which of `donate`, `give`, `lose`, `spend`, `eat`. The depletion
  class is a new operation-kind path; whether to introduce it AT
  ALL is a structural decision.
- **Authorise VE-C non-arithmetic refusal evidence?** No production
  risk; gives downstream contemplation/ADR work better evidence.

No timelines proposed; this is operator decision input plus dispatch
templates. The PRs ship when the operator says go.
