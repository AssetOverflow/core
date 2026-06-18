# GSM8K Workstream A Gate A2a — unit partition / chunking primitive ratification

**Date:** 2026-06-17
**Workstream:** A (GSM8K typed-operation ladder)
**Gate:** A2a — first partition/chunking injection slice (roadmap Gate A2 family)
**Status:** Ratified for implementation (BEFORE any code changes)
**Scope lock:** Fixed-size unit chunking with source-grounded total + chunk size, exact integer quotient, statement-only v1. One narrow recognizer-injector bridge mirroring Inc3 rate and Gate A1 comparative discipline.

**Prerequisites (met on main @ e134e53c):**
- PR #801: Inc3 evidence closure (`rate_with_currency` `recognized_no_injection` = 0 on live runner).
- PR #803/#805: Gate A1 multiplicative comparative ratification + implementation (`comparative_with_unit` no-injection = 0).
- PR #806: Post-Gate-A1 frontier microscope (`docs/analysis/gsm8k-post-gate-a1-frontier-microscope-2026-06-17.md`).
- PR #807: Lane-SHA hygiene (no GSM8K serving change).

**Implementation branch (future):** `feat/gsm8k-workstream-a-gate-a2a-unit-partition-injection`

**Gate naming (fixed — do not conflate):**

| Name | Meaning |
|---|---|
| **Gate A2 (roadmap)** | Partition / chunking family |
| **Gate A2a (this doc)** | Narrow v1: total measure → fixed-size chunks → chunk count |
| **Gate A1b / Comparative-A2** | Additive comparative — **not** roadmap Gate A2 |
| **PR-6d aggregate partition** | Combine facts → split equally into **N containers** — **distinct primitive**, already landed off-serving |

---

## 1. What exact Gate A2a slice is selected?

**Unit partition / chunking:** a **total continuous (or count-measure) quantity** is split into **fixed-size chunks** with an explicit unit on the chunk size, producing an **exact integer chunk count**.

The deliverable is a **recognizer-anchor injector** for a ratified serving category `ShapeCategory.UNIT_PARTITION` (taxonomy label exists today; **not** a live `_MATCHERS` / `_INJECTORS` entry) that emits a typed partition operation when a closed v1 template matches and all slots are source-grounded. The slice closes the **recognizer matched but produced no injection** frontier for the one confirmed DCS misroute (`dcs_misroute_unit_partition` on case **0002**), without widening discrete-count injection.

**Confirmed code facts:**
- `ShapeCategory.UNIT_PARTITION` and `_is_unit_partition` exist in `evals/refusal_taxonomy/shape_categories.py` (taxonomy only).
- EX-6 hyphen-bonded unit extraction (`25-foot`) is landed in `generate/derivation/extract.py`.
- `VALID_OPERATION_KINDS` in `generate/math_problem_graph.py` has **no** `unit_partition` today; bare `divide` apply stores quotient under **divisor unit**, which is **unsafe** for feet÷feet→sections without a `result_unit` contract.
- PR-6d `_Partition` in `generate/quantitative_comprehension.py` is **aggregate-then-divide into N equal containers** — different semantics from fixed chunk size (see §5).

This is **first partition subfamily only** — not full Gate A2 (inverse residual, yield questions, fractional partition, composition wall).

---

## 2. Lead exemplar

**Case `gsm8k-train-sample-v1-0002`** (canonical seed pin in `tests/test_gsm8k_post_gate_a1_frontier_microscope.py`).

**Full problem:**
> Jan buys 1000 feet of cable. She splits it up into 25-foot sections. She gives 1/4 of that to a friend. She then puts half of the rest in storage. How much does she keep on hand? → **15**

**Gate A2a v1 owns only the partition statement:**
> *She splits it up into 25-foot sections.*

**Prior total (separate statement, must be in graph state before partition inject):**
> *Jan buys 1000 feet of cable.*

**Gold partition step:** `1000 ÷ 25 = 40` sections.

**Live refusal (pinned proxy):**
> `candidate_graph: recognizer matched but produced no injection for statement: 'She splits it up into 25-foot sections.' (category=discrete_count_statement)`

**Microscope classification:** `dcs_misroute_unit_partition` → candidate primitive `unit_partition` → movement `downstream_reclassification`.

**Exemplar seed (mis-route documentation):** `teaching/admissibility_exemplars/discrete_count_statement_v1.jsonl` (`dcs-v1-0021`, `train_case_id: gsm8k-train-sample-v1-0002`).

**Confuser spine:** `evals/gsm8k_math/confusers/v1/cases.jsonl` `confuser-v1-0007` — canonical 0002 misfire (pseudo-accumulation → 996 if partition read as Initial(25) only).

---

## 3. What is v1 in scope?

### Closed template (statement-only)

| Requirement | Rule |
|-------------|------|
| **Partition verb** | `split`, `cut`, `divide`, `separate`, or ratified synonym ∈ `DIVIDE_VERBS` (mirror existing divide lexicon; no broadening in v1) |
| **Chunk size** | Hyphenated or explicit measure: `<N>-<unit>` (EX-6) or equivalent ratified span, e.g. `25-foot sections`, `20-inch pieces` |
| **Total quantity** | Prior statement in the same problem must ground `(actor, total_unit)` with value ≥ chunk size; partition stmt does **not** carry total |
| **Unit compatibility** | Dividend unit == chunk-size unit (same canonical unit); no implicit conversion |
| **Quotient** | `total % chunk_size == 0`; exact positive integer chunk count |
| **Output** | Emit typed **`unit_partition`** operation (§5) writing **chunk count** under a dimensionless or explicit count-noun unit (`section`, `piece`, … from counted noun in chunk phrase) |
| **Actor** | Same actor chain as prior total statement (v1: same-sentence subject or ratified narrow antecedent — **no** cross-sentence pronoun binding beyond existing session rules) |
| **Injection target** | **Statements only** — not question surfaces (mirror Gate A1) |
| **DCS yield** | Partition-bearing stmt must **not** match `discrete_count_statement` first / must not emit `Initial(chunk_size, material_unit)` misread |

### Positive admission surfaces (v1)

| ID | Pattern | Notes |
|----|---------|-------|
| A01 | `1000 feet` … `splits into 25-foot sections` | Canonical 0002 pair |
| A02 | `800 inches` … `cuts into 20-inch pieces` | Paraphrase (confuser-v1-0005 first clause) |
| A04 | `12 feet` rope `cut into 4-foot sections` → 3 | Clean single-pair toy |

### Expected v1 deliverable (implementation PR)

- `unit_partition` (or ratified equivalent) on serving recognizer/injector path
- Live bucket: **`unit_partition` recognized_no_injection = 0** (mirror Inc3/Gate A1 closure)
- Case **0002** partition stmt: reclassification off DCS misroute (not guaranteed end-to-end solve)

---

## 4. What is explicitly out of v1?

| Case / surface | Deferral reason |
|----------------|-----------------|
| **0002 full problem** (¼ give, half of rest, "keep on hand") | Fraction + rest-state + question binding — composition follow-up; confuser-v1-0007 must stay **refuse** until separately ratified |
| **0007** inverse residual ("how many more boxes") | Question-parser slot; box capacity derivation — not stmt-level chunk partition |
| **0008** yield ("50 beads per bracelet, how many bracelets") | Production/yield question frame; needs inventory aggregate first |
| **0004** nested fraction partition | `Half of the kids…` — fractional subset-of-set, not fixed chunk size |
| **0025** peer-pick ("three friends pick the same amount") | Multiplicative peer partition question — not measure chunking |
| **0047** equal pack into N bags | Equal distribution into **N containers** (divisor = bag count), not **M-unit chunks**; taxonomy `discrete_count_statement` |
| **0030** `2-hour drive` | Duration descriptor; taxonomy false positive via hyphen — must **refuse** |
| **Non-integer quotient** | e.g. `1000 feet` → `30-foot sections` — refuse (no floor/ceil) |
| **Missing total** | Partition stmt alone: `She splits it into 25-foot sections` — refuse |
| **Missing chunk size** | `equal sections`, `into 40 sections` (count without unit size) — refuse |
| **"Split into N groups/boxes"** | PR-6d / enumeration — divisor is **group count**, not chunk measure |
| **Rate / per-unit** | `per hour`, `per kg`, `$2 for one cup` — Inc3/Gate A1 closed buckets |
| **Broad DCS composition wall** | 14× `dcs_composition_wall` — forbidden without `derivation_composer` ratification |
| **Affine equation / graph_planner** | Out of Workstream A injector ladder |
| **Cross-sentence pronoun reference** | ADR-0138 — not proven safe |
| **Remainder / subtract-after-partition** | Needs gain/loss chaining beyond v1 injector |

**Widening discrete-count injector** to emit partition ops is **explicitly forbidden** (metric-inert / wrong=0 hazard per question-layer survey).

---

## 5. What typed primitive is required?

### Ratified choice: **`unit_partition`** (new `Operation.kind`)

**Not safe to reuse bare `divide` without extension** because:
1. `_apply_divide` stores quotient under **divisor unit** (`feet`), not chunk count (`sections`).
2. Existing `divide` encodes **equal N-way split** (`groups` dimensionless + material unit tag) — different from **fixed chunk size**.
3. Candidate-graph parser does not emit serving `divide` today; partition requires a **new injector**, not parser reuse alone.

**Not the same as PR-6d `_Partition`:** aggregate-then-divide into **N equal containers** with `perquery` pairing (`generate/quantitative_comprehension.py`). Gate A2a is **total ÷ fixed chunk measure → count**.

### Minimal operation shape (conceptual — implementation must match or re-ratify)

```python
Operation(
    actor=<subject>,
    kind="unit_partition",
    operand=Quantity(value=<chunk_size>, unit=<chunk_unit>),  # e.g. 25, foot
    # implementation must also carry result_unit=<count_noun> or dimensionless count
)
```

**Apply rule (wrong=0):**
- Read `(actor, dividend_unit)` from prior grounded state.
- Require `dividend_unit == chunk_unit` (after canonicalization).
- Require `total % chunk_size == 0`.
- Write `(actor, result_unit) = total // chunk_size` where `result_unit` is explicit count noun or dimensionless count — **not** dividend unit.

**Stop/re-ratify trigger:** If implementation discovers the substrate can only safely use `divide` + mandatory `result_unit` fields without a new kind, implementation PR must cite this doc and either (a) prove equivalence in tests or (b) open amendment PR before merge.

**Rejected names:** `unitize` (versor algebra collision); `partition_count` alone (ambiguous with PR-6d and equal-N split).

---

## 6. Grounding rules

| Slot | Rule |
|------|------|
| **total_quantity** | From **prior statement** quantity anchor; literal span grounded; actor key matches partition subject |
| **chunk_size** | From partition statement hyphenated or explicit measure token; literal substring in `matched_*_token` fields |
| **chunk_unit** | Canonical unit from EX-6 / `_canonicalize_unit`; must match total unit |
| **partition_verb** | Literal verb ∈ ratified divide verb set |
| **counted_noun** | Optional: `sections`, `pieces` — drives `result_unit` label |
| **source_span** | Full partition statement byte-identical to input |
| **No inferred totals** | Partition stmt without prior total state → injector returns `()` or downstream refuse |
| **No implicit conversion** | `feet` vs `inches` → refuse unless conversion ratified elsewhere |
| **No LLM / heuristic fill** | Every slot maps to a literal substring (Inc2/Gate A1 doctrine) |

### Matcher category and `parsed_anchors` (implementation PR)

| Anchor key | Semantics |
|------------|-----------|
| `actor_token` | Partition statement subject |
| `chunk_size_token` | Numeric chunk magnitude (e.g. `25`) |
| `chunk_unit_token` | Unit phrase (e.g. `foot`) |
| `counted_noun_token` | Plural noun after chunk phrase if present (`sections`) |
| `partition_verb_token` | Matched split/cut verb |
| `source_span` | Full statement |

---

## 7. wrong=0 guard

| Condition | Behavior |
|-----------|----------|
| Ambiguous partition (two chunk sizes, competing interpretations) | **Refuse** — no injection |
| Incompatible units (feet vs inches) | **Refuse** |
| Non-exact division (`total % chunk_size != 0`) | **Refuse** at solve/verify — never floor |
| Missing total or missing chunk size | **Refuse** — injector `()` |
| Partition stmt matches DCS only | **Refuse** mis-injection — must not emit `Initial(N, material_unit)` |
| Multiple partition cues in one sentence | **Refuse** |
| Downstream composition (fractions, rest, question) | **Refuse** on serving until composition ratified — partial graph must not verify as full gold |
| Numeric answer without verifier | **Forbidden** — `math_verifier.verify` must pass before `correct` (`evals/gsm8k_math/runner.py`) |

**Architectural boundaries (INV-30 / INV-31):**
- No `determine()`, no `answer=False`, no `FrameVerdict`, no CLOSE interaction on this path.
- No `core.reliability_gate` as substitute for verifier replay on serving.

**Serving path:** `parse_and_solve` → `solve` → `math_verifier.verify` → gold compare; `wrong == 0` hard.

---

## 8. Confusers future implementation must prove

### Hard refuses (30+ structural — minimum bar in implementation PR)

| ID | Surface class | Example | Expected |
|----|---------------|---------|----------|
| C01–C02 | Non-integer chunk | `1000 feet` → `7-foot` / `2.5-meter` | refuse |
| C03–C06 | Missing total or chunk | stmt-only `25-foot sections`; `equal sections` | refuse |
| C07 | Unit mismatch | `1000 feet` → `25-inch sections` | refuse |
| C08 | Discrete packing | `48 cookies` → `boxes of 6` | refuse |
| C09–C11 | N groups vs M-unit chunks | `equally into 4 bags`; `Half of the kids` | refuse |
| C12 | Inverse residual (0007) | `how many more boxes` | refuse |
| C13 | Yield (0008) | `50 beads per bracelet, how many…` | refuse |
| C14–C16 | Fraction/rest follow-up | full 0002; `gives 1/4`; subtract sections | refuse |
| C17 | Non-exact total | `999 feet` → `25-foot` | refuse |
| C18–C20 | Rate/per-unit | `$18/hour`, `$20 per kg`, `$2 per cup` | refuse |
| C21–C22 | Duration false positive | `2-hour drive`; `10 oysters in 5 minutes` | refuse |
| C23–C26 | DCS / composition wall | routes, multi-entity lists, comparatives, fraction-of-prior | refuse |
| C27 | Pseudo-accumulation twin | ribbon 800 + cut + give ¼ | refuse |
| C28 | Additive comparative (0016) | `2 more than 5 miles` | refuse |
| C29–C30 | Peer-pick / product each | 0025 question; `24 erasers each` | refuse |

**Critical discrimination pairs:**
- `1000 feet split into 25-foot sections` (**admit** partition inject) vs stmt-only `25-foot sections` (**refuse**)
- `1000 feet split into 25 sections` (count divisor, no unit size) — **refuse**
- `1000 feet split into bags` (missing chunk measure) — **refuse**

### Admission tests (5 minimum)

| ID | Proves |
|----|--------|
| A01–A02 | Canonical inject on 0002 / ribbon paraphrase |
| A03 | Pair consistency: paired total+chunk vs stmt-only |
| A05 | Category `unit_partition`, **not** `discrete_count_statement` |

**Graduation rule (ADR-0163-F2):** Confusers graduate to solve only when a **general** composition mechanism is ratified and proven — not by regex widening.

---

## 9. Partition-adjacent cases (frontier evidence)

| case_id | Relevance | v1 |
|---------|-----------|-----|
| **0002** | **Lead** — `dcs_misroute_unit_partition` | **IN** (partition stmt inject) |
| **0007** | Inverse box residual — question layer | **OUT** |
| **0008** | Beads-per-bracelet yield — question + aggregate | **OUT** |
| **0004** | Nested fraction subset | **OUT** |
| **0025** | Peer-pick multiplication question | **OUT** |
| **0047** | Equal pack into 4 bags — container count divisor | **OUT** |

Only **0002** has confirmed `unit_partition` DCS misroute on live serving (`recognized_no_injection` subfamily count = 1).

---

## 10. Expected metric movement

**Live ephemeral runner (main @ e134e53c):** 6 correct / 44 refused / 0 wrong; `rate_with_currency` and `comparative_with_unit` no-injection = **0**.

**Expected after Gate A2a implementation:**

| Metric | Expected |
|--------|----------|
| `wrong` | **0** (hard) |
| `correct` | **≥ 6** (monotonic); **not guaranteed lift** |
| `refused` | **≤ 44** (monotonic) |
| **0002** | **Reclassification** — partition stmt moves off DCS no-injection; full 15 solve still refused until composition ratified |
| `discrete_count_statement` no-injection | Likely **−1** (19→18) |
| `unit_partition` no-injection | Target **0** on live runner |
| Pinned `report.json` | **Unchanged** unless separate rebaseline PR |

**Do not claim** aggregate correct-count lift in implementation PR body without per-case ephemeral evidence.

---

## 11. Explicit non-goals

- **No implementation** in this ratification PR (docs only).
- No `report.json` rebaseline.
- No additive comparative (Gate A1b / Comparative-A2).
- No Inc4 rate denom-state.
- No broad DCS widening / `derivation_composer` without separate ratification.
- No affine equation frame / `graph_planner.py` changes.
- No sealed-lane / `scripts/verify_lane_shas.py` pin movement (unless accidental — revert).
- No corpus / pack / policy / identity mutation.
- No `determine()` / `FrameVerdict` / CLOSE / idle consolidation (**INV-30 / INV-31**).
- No `answer=False` on open-world paths.
- No LLM / stochastic generation.
- No promotion of taxonomy `_HYPHENATED_UNIT_RE` alone into matcher (0030 hazard).
- No conflation with PR-6d aggregate-partition template.
- No full Gate A2 family in one PR.

---

## 12. Implementation touch list (future PR — not this PR)

| File | Change |
|------|--------|
| `generate/math_problem_graph.py` | Add `unit_partition` to `VALID_OPERATION_KINDS` (if new kind) |
| `generate/math_solver.py` | `_apply_unit_partition` with `result_unit` contract |
| `generate/recognizer_match.py` | `_match_unit_partition`, `_MATCHERS` registration |
| `generate/recognizer_anchor_inject.py` | `inject_unit_partition`, `_INJECTORS`; DCS yield guard |
| `generate/math_verifier.py` / `math_roundtrip.py` | Roundtrip + verify hooks for new kind |
| `teaching/admissibility_exemplars/` | `unit_partition_v1.jsonl` (Phase C corridor) |
| `tests/test_recognizer_unit_partition_inject.py` | **new** — ≥15 unit tests |
| `tests/test_math_candidate_graph_unit_partition_injection.py` | **new** — ≥8 graph tests |
| `tests/test_gsm8k_frontier_report.py` | live `unit_partition` bucket closure |
| `tests/test_candidate_graph_recognizer_wiring.py` | wrong=0 replay |
| `tests/test_candidate_graph_completeness_guard.py` | pseudo-accumulation regressions |
| `tests/test_adr_0163_f2_confusers.py` | confuser-v1-0005/0007/0008 |

**Read-only unless proven necessary:** `generate/derivation/*` (off-serving), `core/reliability_gate/*`, `graph_planner.py`.

---

## 13. Validation obligations (implementation PR — not this PR)

```bash
.venv/bin/python -m pytest tests/test_recognizer_unit_partition_inject.py -q
.venv/bin/python -m pytest tests/test_math_candidate_graph_unit_partition_injection.py -q
.venv/bin/python -m pytest tests/test_gsm8k_frontier_report.py -q
.venv/bin/python -m pytest tests/test_gsm8k_post_gate_a1_frontier_microscope.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_recognizer_wiring.py -q
.venv/bin/python -m pytest tests/test_candidate_graph_completeness_guard.py -q
.venv/bin/python -m pytest tests/test_adr_0163_f2_confusers.py -q
.venv/bin/python -m pytest tests/test_adr_0175_phase2_practice_lane.py -q
.venv/bin/python -m pytest tests/test_architectural_invariants.py -q -k "INV_30 or INV_31"
.venv/bin/python scripts/verify_lane_shas.py
.venv/bin/core test --suite smoke -q
# Ephemeral only — do not commit unless ratified:
# build_report(cases) → wrong==0
```

---

## 14. Validation obligations (this ratification PR — docs only)

```bash
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
```

Expected: single added file `docs/analysis/gsm8k-workstream-a-gate-a2a-unit-partition-ratification-2026-06-17.md`.

---

## 15. Open risks (honest)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Over-recognition on any `\d+-(foot\|hour\|…)` | **Critical** | Closed verb+chunk template; 0030/0014 confusers; refuse duration |
| DCS wins match race on 0002 | **High** | Explicit DCS yield guard + matcher priority tests |
| Bare `divide` quotient unit bug | **Critical** | Ratify `unit_partition` + `result_unit`; never store 40 under `feet` |
| PR-6d conflation | **High** | Refuse `into N bags` / `perquery` shapes in v1 |
| Pseudo-accumulation 996 misfire | **Critical** | confuser-v1-0007 green; completeness guard |
| Claiming 0002 full solve | **High** | Doc + tests: injector closure only |
| Composition pressure (fractions/rest) | **Medium** | Explicit out-of-v1; separate ratification |
| No guaranteed correct lift | **Low** (expected) | PR body documents reclassification only |
| `result_unit` noun ambiguity (`sections` vs dimensionless) | **Medium** | Resolve in implementation tests; amend if dual |

---

## 16. Arena reconciliation summary

| Agent | Key finding |
|-------|-------------|
| **Partition substrate mapper** | Bare `divide` unsafe; PR-6d distinct; ratify new `unit_partition` kind with `result_unit`; EX-6 + taxonomy landed, injector missing |
| **Frontier evidence auditor** | 0002 lead exemplar confirmed; 0007/0008/0004/0025/0047 OUT of v1; reclassification-only metric |
| **Over-recognition adversary** | 30 hard refuses + 5 admission tests; duration/rate/DCS wall highest risk |
| **Truth-boundary auditor** | INV-30/31; verifier before correct; no determine/FrameVerdict/CLOSE |
| **Test-plan auditor** | Inc2/Gate A1 ladder mirror; 15+8 unit/graph tests; frontier bucket closure; this PR docs-only |

This ratification closes the docs-first gate. Implementation may proceed only after this document merges to `main`.