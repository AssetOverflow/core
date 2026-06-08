# Combined-rate comprehension organ (R4) — v1 capability ledger

**As of:** `main` @ `3381e031` (after CMB-a…CMB-d, #650–#656). This artifact
**closes and freezes** the R4 combined-rate v1 claim. It is **docs only — no
behavior change.** Nothing here adds, widens, or re-enables capability; it
records exactly what shipped, the lane that proves each piece, and — at least as
load-bearing — what R4 deliberately does **not** do (§8).

R4 was built down the same fixed ladder as R1/R2/R3, off the sealed serving
path: gold (ruler) → setup oracle → solver → reader → router/contemplation. No
rung started before the one below it was green, and the reader was built **last**
(CMB-c), against an already-proven solver and oracle — never reader-first.

---

## 1. The v1 capability claim (frozen)

> **R4 v1 comprehends and solves a two-rate, single-compound-unit, exact-integer
> combined-rate problem.** Concretely: two explicit rates each stated as
> `<N> <plural> per <singular>` over **one shared compound unit**, combined by an
> **explicitly cued** mode — **sum** (a cooperation cue: *together / combined /
> both*) or **difference** (an opposing-flow cue: *fills … removes / drains*) —
> after which it answers exactly one of {**net rate**, **accumulated quantity**,
> **elapsed time**}, and **only when that answer is an exact positive integer.**
>
> Every input outside that envelope is **refused with a typed, closed-set
> reason — never guessed.** Breadth is never bought with a wrong answer.

**Safety claim (the reason this is allowed to exist).** R4 adds **no** capability
to the served GSM8K path. The organ and its router/contemplation wiring import
**neither** `generate.derivation` **nor** `core.reliability_gate` — checked by an
AST import guard, not asserted (§9). It therefore *cannot, by construction*,
change a single served answer or perturb the pinned eval-lane SHAs. `answer_wrong
== 0` on R4's gold lane is held the same way every other organ holds it: by
refusing everything outside §1, not by widening.

**The envelope, precisely.** A problem is in R4's domain iff a 2-dimensional
(rate-count × cue) gate admits it:

| rates present | combination cue | outcome |
|---|---|---|
| two, same unit | clear sum/difference cue | **solved** (or a solver boundary, §3) |
| two, same unit | no cue | refuse `combine_mode_ambiguous` (§4) |
| one rate | combination cue present | refuse `missing_second_rate` (§4) |
| one rate / foreign | no cue | **step aside** `not_combined_rate_shaped` (→ R3, §7) |

Two same-unit rates make it R4's domain *even with no cue* (the missing direction
is then the refusal); a single rate needs a combination cue to be R4's
substantive domain rather than R3's single-rate domain.

---

## 2. Supported solved families

The 6 `solved` gold fixtures are the **complete** `combine_mode × query` grid —
both modes against all three derived slots — so "solved" means the whole grid, not
a lucky cell:

| query | sum (cooperation) | difference (opposing flow) |
|---|---|---|
| **net rate** (`effective_rate`) | cmb-06 hoses `6+4 = 10` | cmb-05 tank `9-4 = 5` |
| **quantity** (`eff × time`) | cmb-01 paint `(3+2)×4 = 20` | cmb-02 tank `(5-2)×6 = 18` |
| **time** (`quantity ÷ eff`) | cmb-03 paint `20÷(3+2) = 4` | cmb-04 tank `18÷(5-2) = 6` |

The algebra is pure integer (`generate/combined_rate_comprehension/solver.py`):

```text
effective_rate = rate_a + rate_b           (combine_mode == "sum")
effective_rate = rate_a - rate_b           (combine_mode == "difference")
quantity       = effective_rate × time     (query == "quantity")
time           = quantity ÷ effective_rate (query == "time", exact-int or refuse)
effective_rate                              (query == "effective_rate")
```

**Model input contract** (`model.py`, the CMB-b wrong=0 fix): `rate_a`, `rate_b`,
and any *known* time/quantity are **positive ints** — a non-positive input is
unrepresentable, so the solver can never receive a path that yields a negative
answer. The *net* rate, by contrast, **may** be `≤ 0` (difference mode with
`rate_a ≤ rate_b`); that is a derived property and the **solver's** boundary
(§3), not a malformed setup.

---

## 3. Solver boundaries (refuse, never guess)

The solver (`solver.py`) has exactly **two** refusals — both `must_remain_refused`
hard boundaries, both pure-integer, no float / no `Fraction`:

- **`non_positive_net_rate`** — a `quantity` or `time` query whose net rate is
  `≤ 0` cannot accumulate or finish; the solver refuses **before** dividing, so the
  `eff == 0` time query never divides by zero, and the `eff < 0` quantity query
  never returns a negative quantity. The `effective_rate` query is *exempt*: the
  net rate is a well-defined answer even when `≤ 0` (cmb-05 returns the net
  directly). Proven across all four cells by cmb-07 (`eff=0`/quantity),
  cmb-07b (`eff<0`/quantity), cmb-07c (`eff=0`/time), cmb-07d (`eff<0`/time).
- **`non_integer_solution`** — a `time` query that does not divide exactly
  (cmb-08: `12 ÷ 5`); never rounds.

Namespaced for the registry as `cmb_non_positive_net` / `cmb_non_integer` (§6).
Both reach `REFUSED_KNOWN_BOUNDARY` in contemplation and — critically — **never a
proposal**: the prose was understood, the math is simply outside v1, so it is a
terminal boundary, not a coverage gap.

---

## 4. Reader boundaries (refuse, never guess)

The reader (`reader.py`) emits a **closed** taxonomy of 8 refusal reasons. Two are
non-substantive **step-asides**; three are **substantive boundaries that must stay
refused**; three are **deferred capabilities** (§5).

**Step-aside → `input_shape` (not-my-domain; cedes, never blocks):**

- `empty`
- `not_combined_rate_shaped` — a single explicit rate with no second rate and no
  combination cue (R3 territory, cmb-15), **or** two same-unit rates whose query
  attributes the answer to a *single agent* (cmb-16, "how many words does **Alice**
  type"). R4 must step aside, never claim a substantive boundary on these.

**Substantive boundaries (`must_remain_refused`):**

- **`rate_unit_mismatch`** (cmb-09: rooms/hour vs liters/minute) → family
  `cmb_unit_mismatch`. **Must remain refused UNTIL a dimension registry exists —
  *not forever.*** R4 v1 has no representation of dimension, so it cannot
  distinguish a *convertible* pair (gallons/min vs gallons/hour) from a
  *dimensionally-incompatible* one; a "try conversion" proposal would be
  wrong=0-unsafe. A convertible-unit split is named future work, not an
  impossibility.
- **`combine_mode_ambiguous`** (cmb-10: two same-unit rates, no licensed cue) →
  `cmb_combine_ambiguous`. An **ambiguity**, not a coverage gap: no fixture can
  teach which direction the text intended. Direction is never inferred from vibes.
- **`missing_second_rate`** (cmb-11: cooperation cue but only one rate) →
  `cmb_underdetermined`. An **under-specified input**, not a coverage gap: no
  reader enhancement can invent the unstated rate.

The boundary between §4-substantive and §5-deferred is deliberate and was
operator-ratified: **proposals are for structural capability gaps, not for
ambiguous or under-specified inputs.** `combine_mode_ambiguous` and
`missing_second_rate` are *inputs the world cannot make well-formed*, so they stay
refused with no growth signal.

---

## 5. Proposal-allowed deferrals (the only growth surfaces)

Exactly **three** reader reasons are growth surfaces. They are emitted **only
after positive combined-rate recognition** (two real rate clauses + a real
combination shape), so they are always combined-rate-like — never arbitrary text.
Each maps to a `proposal_allowed` family targeting `cmb_gold_fixture`:

| reader reason | family | deferred capability |
|---|---|---|
| `three_or_more_rates` (cmb-12) | `cmb_unsupported_rate_count` | ≥3 contributing rates; v1 combines exactly two |
| `reciprocal_work_rate_deferred` (cmb-13) | `cmb_unsupported_reciprocal` | "paint a house in 3 h" → `1/(1/3+1/6)`; reciprocal rates + rational arithmetic |
| `clock_interval_deferred` (cmb-14) | `cmb_unsupported_clock_interval` | elapsed clock time ("2 pm to 5 pm"); the CMB twin of R3's `temporal_state` |

A proposal here is **proposal-only**: `mounted:false`, `requires_review:true`,
content-addressed, routed through the existing `teaching/*` HITL flywheel — never
self-installed, never a parallel correction path.

---

## 6. Router / contemplation integration (CMB-d)

R4 joined the deterministic multi-organ machinery in `core/comprehension_attempt/`:

- **Router** (`route_setup`) now collects **four** attempts (r1 / r2 / r3 / r4)
  and selects the unique `setup_correct`.
- **Reason namespacing** (`classify.py::cmb_reason`): the failure registry is keyed
  by reason-string alone (a partition), so R4's bare reasons are namespaced `cmb_*`
  **before** the registry sees them. This stops R4 boundaries from inheriting
  R2/R3 families for the same bare string (R3 `rate_unit_mismatch` → growth;
  R2/R3 `non_integer_solution` → other owners). The two bare step-aside reasons
  (`not_combined_rate_shaped`, `empty`) stay bare → the cross `input_shape` family.
- **Contemplation** (`generate/contemplation/pass_manager.py`) routes a selected
  R4 organ through `_solve_and_verify_cmb` and lands on a closed terminal:
  `SOLVED_VERIFIED` · `REFUSED_KNOWN_BOUNDARY` (solver boundary or substantive
  reader refusal) · `PROPOSAL_EMITTED` (a §5 deferral only).
- **Router-organ hygiene.** R4 is pinned as an *organ* against R1/R2/R3 foreign
  gold: on foreign text it must step aside as `input_shape`, never a substantive
  boundary. (R4 is deliberately **not** in the hygiene test's `_GOLD` set, because
  a combined-rate problem is *not foreign* to R3 — R3 genuinely co-recognizes the
  rate clauses. That asymmetry is governed by §7, not by the strict hygiene rule.)

---

## 7. Domain-precedence adjudication (named precedent)

> **A `setup_correct` from a broader organ is not automatically admissible if a
> more specific organ positively recognizes load-bearing structure that the
> broader organ would drop.**
>
> **Current concrete rule (`router.py::cmb_is_authoritative`):** when R4
> *positively recognizes* combined-rate shape — either a combined setup, or a
> *substantive* `cmb_*` refusal (a reason starting `cmb_`) — R4's recognition
> **beats** R3's single-rate recognition of the same text, for **both** routing
> (veto R3's `setup_correct`) **and** family attribution (suppress R3 so R4's
> diagnosis owns the terminal/proposal). The one exception: if R4 merely stepped
> aside as `input_shape` (`not_combined_rate_shaped`), it cedes and R3 proceeds.

This is the first concrete router adjudication precedent in the comprehension
stack. It generalizes to any specific↔broad organ pair (geometry+arithmetic,
unit-conversion+rate, multi-equation+simple-arithmetic): the organ that recognized
the load-bearing structure adjudicates over the organ that would answer by
dropping it. R3 itself is **unchanged** — the adjudication lives entirely at the
router/contemplation layer.

**Proof cases** (pinned in `tests/test_cmb_router_contemplation.py`):

- **cmb-11** (`missing_second_rate`) — a cooperation-cued, one-rate problem. R3
  would over-read it as a single rate and **solve it wrong (12)**. R4's substantive
  `cmb_missing_second_rate` recognition **vetoes** R3 → terminal
  `REFUSED_KNOWN_BOUNDARY` (`cmb_underdetermined`), **never a wrong 12**, and — an
  under-specified input — **no proposal**.
- **cmb-15** (`not_combined_rate_shaped`) — a genuine single-rate problem
  (`60 mph for 3 hours`). R4 merely steps aside (`input_shape`), so it **cedes**;
  R3 solves the real answer **180**.
- **cmb-12 / cmb-13 / cmb-14** — combined-rate text R4 positively recognizes but
  defers (§5). R4 **owns** the proposal attribution; R3's broader single-rate
  over-read is suppressed so the growth signal is filed under the correct
  combined-rate family, not a misattributed R3 family. (A safe terminal with the
  *wrong owner* is still a bad growth signal — hence attribution precedence, kept
  narrow to R4-positive-recognized text only.)

---

## 8. Non-claims (read this before extending R4)

**R4 v1 does NOT do any of the following.** Each is a hard edge, and "combined
rate" must never be read more broadly than §1. If a future need touches one of
these, it is a *new, scoped rung* — not an R4 v1 behavior:

- ❌ **No reciprocal work-rate.** "Paint a house in 3 hours" → `1/(1/3 + 1/6)` is
  **deferred** (cmb-13), not solved. v1 reads explicit per-unit rates only.
- ❌ **No three-or-more rates.** v1 combines **exactly two**; ≥3 is deferred
  (cmb-12).
- ❌ **No mixed-unit / cross-dimension combination.** Two rates must share one
  compound unit; incompatible units are **refused** (cmb-09). No unit conversion
  exists in v1 (`time_unit` always equals the rate denominator).
- ❌ **No clock-time intervals.** "From 2 pm to 5 pm" is **deferred** (cmb-14); v1
  takes an explicit integer duration only.
- ❌ **No sequential / phased segments.** No "works alone for 2 h, then together";
  v1 is a single combined regime over one duration.
- ❌ **No decimal or fractional rates / answers.** Pure integer in, exact-integer
  out, or **refuse** (cmb-08). No rounding, ever.
- ❌ **No arbitrary prose.** v1 recognizes the two explicit-rate shapes and their
  cues; anything it does not positively recognize is **refused / stepped aside**,
  not best-effort parsed.
- ❌ **No single-agent attribution over two rates.** "How many words does *Alice*
  type" with a distractor second rate **steps aside** (cmb-16) — a single-rate
  question, not a combined query.
- ❌ **No serving-path change.** R4 imports no `generate.derivation` and no
  `core.reliability_gate`; it touches **zero** served answers and the pinned-SHA
  lanes are unaffected.

---

## 9. Verification lanes

| lane | command | state |
|---|---|---|
| gold ruler (oracle) | `python -m evals.combined_rate_oracle` | **19 fixtures: 6 solved / 5 solver_refuses / 8 reader_refuses**, all valid under the non-vacuous `_canonical_outcome` |
| solver | `python -m evals.combined_rate_oracle solver` | 6 solved → gold int; 5 solver_refuses → `Refusal` w/ gold reason; 8 reader_refuses skipped (no setup) |
| reader | `python -m evals.combined_rate_oracle reader` | **11 setup_correct / 0 wrong / 8 refused** (well-formed read to the gold signature; reader_refuses refuse with the gold reason) |
| router + hygiene | `tests/test_setup_router.py`, `tests/test_router_organ_hygiene.py` | green — 4-organ routing, no foreign substantive boundary |
| failure registry | `tests/test_failure_family.py` | green — partition; only the 3 `cmb_unsupported_*` are growth surfaces |
| contemplation matrix | `tests/test_cmb_router_contemplation.py` | green — full terminal matrix + cmb-11 veto + cmb-15 cede + §5 proposal ownership |
| off-serving | AST import guard in the contemplation test + architectural invariants | green — no `generate.derivation` / `core.reliability_gate` |

**Answer-level outcome.** R4 answers **6 / 0 / 13** (6 solved, **0 wrong**, 13
refused = 5 solver boundaries + 8 reader boundaries). The discipline holds: wrong
== 0, breadth never bought with a wrong answer.

**Non-vacuous oracle.** `_canonical_outcome` cross-checks every `solved` gold
against the canonical arithmetic and every `solver_refuses` reason against the
canonical refusal (per the CLAUDE.md proof-obligation rule) — the oracle is a
ruler that fails loudly on its own incoherent gold, not a rubber stamp.

**Honest test accounting.** The R4 dedicated lanes above are all green on the
merged base (re-confirmed for this ledger: oracle 19/19, the seven R4 test files
**93 passed**). The broader comprehension test net was **597 passing** as measured
during CMB-d verification (this docs-only change touches no test code, so that
count stands). There is **1 pre-existing red**,
`tests/test_plan_contemplation_runtime.py::test_findings_reset_between_turns` — a
discourse-contemplation test that is red on clean `origin/main`, **unrelated to
R4**: it imports nothing from `combined_rate_comprehension` /
`comprehension_attempt`, and was confirmed red on a clean base before any CMB
work (one of main's known long-standing reds; `--suite full` only). No R4 lane
depends on it.

---

## Status: v1 frozen

R4 combined-rate v1 is **complete and frozen** at this claim. The next move is
**not** more combined-rate capability — the deferrals in §5 are filed as
proposal-targets, to be picked up only when a real fixture demands one. The
project's next frontier is qualitatively different: the **served-surface
epistemology** (graded disclosure / `VERIFIED`), which is scoped separately before
any code.
