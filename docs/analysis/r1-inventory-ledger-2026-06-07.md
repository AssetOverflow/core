# R1 comprehension inventory ledger

**As of:** `main @ 5ada1392` (post-#616, PR-6d landed)
**Lane state:** R1 setup **4 / 0 / 6** · R1 answers **4 / 0 / 6** (`setup_wrong 0`, `gold_error 0`) · 15-case setup **15 / 0 / 0**

This is a baseline decision artifact, not a capability claim. It records exactly
which `evals/setup_oracle/r1_gold.jsonl` fixtures the typed comprehension organ
now *reads and answers*, which it *refuses*, and — for each refusal — the
semantic family that blocks it and whether that refusal is a coverage gap or a
load-bearing wrong=0 boundary that **should stay refused**. It exists so the next
slice moves only the cases whose semantics are already supported, and never
mistakes a correct refusal for a gap.

## Reproduce

```bash
.venv/bin/python -m evals.setup_oracle r1          # setup lane  -> 4/0/6
.venv/bin/python -m evals.setup_oracle r1-answers  # answer lane -> 4/0/6, setup_wrong 0, gold_error 0
.venv/bin/python -m evals.setup_oracle             # 15-case setup gold -> 15/0/0
```

The answer lane grades both halves: the *reading* against independent setup gold
(`setup_wrong`) and the *value* against an independent answer oracle (`wrong`,
`gold_error`). A refused fixture refuses in both halves; no fixture is read but
mis-valued.

## Per-fixture ledger (10 fixtures)

| Fixture | Prose gist | Setup | Answer | Semantic family | Refusal code | Class |
|---|---|---|---|---|---|---|
| `r1-01-twice` | `Bella has twice as many … as Anna (6)` | ✅ correct | `12` | multiplicative (`twice`) | — | **admitted** |
| `r1-02-half` | `Dora has half as many … as Carl (8)` | ✅ correct | `4` | divisive (`half`) | — | **admitted** |
| `r1-05-chain` | `Jon = 3×Ivy(4); Kim = Jon + 2` | ✅ correct | `14` | multi-step chain (mul → add) | — | **admitted** |
| `r1-06-subtotal-reused` | `total = Lee(5)+Mae(7); per_box = total/3` | ✅ correct | `4` | aggregate-then-divide partition | — | **admitted** |
| `r1-03-more-total` | `Evan = Finn(10)+5; ask total **altogether**` | ⛔ refused | ⛔ refused | additive aggregate + aggregate-query phrasing | `unreadable_quantity_query` | **gap (phrasing)** |
| `r1-04-fewer-total` | `Hank = Gail(20)−6; ask total **in total**` | ⛔ refused | ⛔ refused | additive aggregate + aggregate-query phrasing | `unreadable_quantity_query` | **gap (phrasing)** |
| `r1-07-inverse` | `Nia(15) = Omar + 9; ask Omar` | ⛔ refused | ⛔ refused | inverse target (ask the *base* of a relation) | `admissibility_refused` | **gap (real capability)** |
| `r1-08-ambiguous-referent` | `He has 3 more than her; ask she` | ⛔ refused | ⛔ refused | unresolved pronoun referent | `unreadable_quantity_clause` | **correct refusal** |
| `r1-09-missing-base` | `Quinn = 2×Rosa; Rosa never given` | ⛔ refused | ⛔ refused | ungrounded base (no grounded fact) | `no_single_quantity_query` | **correct refusal** |
| `r1-10-distractor` | `Sam has 7 pencils **and 3 erasers**; ask Tom` | ⛔ refused | ⛔ refused | distractor in a compound clause | `unreadable_quantity_clause` | **correct refusal** |

## The 4 admitted families and the invariant protecting each

Each admitted family is protected by a specific projection/admissibility gate AND
the two independent oracles. A family is "admitted" only because a violation of
its gate would fail loudly (`setup_wrong` or `wrong`/`gold_error` > 0), never
silently.

| Family | Fixtures | Protecting invariant |
|---|---|---|
| multiplicative | `r1-01`, `r1-05` (middle step) | scalar-only projection: `Mul(Symbol, Literal)` is the **only** multiplicative `to_relation`; `count × dimensionless = count`; single-dep multiply admissibility (PR-6a). A `Literal` is dimensionless by construction. |
| divisive | `r1-02` | divisor-only projection: `Div(Symbol, Literal)` is the **only** divisive `to_relation`; single-dep divide admissibility, symmetric with multiply (PR-6c); oracle **exact-divisibility** gate `base % divisor == 0` — an odd base refuses, never rounds. |
| multi-step chain | `r1-05` | composition of the above two gates over a derived intermediate; the whole reading refuses if any step's projection/admissibility fails (no partial chain). |
| aggregate-then-divide partition | `r1-06` | partition/query coherence guard (`partition ⇔ perquery`, else `partition_query_mismatch`; container match else `partition_container_mismatch`); reuses `SumOf` + `Div` with **no new relation kind**; exact-divisibility gates the answer over a *derived* total (PR-6d). |
| all admitted | — | setup oracle: `reader_rel == gold_rel ∧ reader_units == gold_units ∧ reader_unk == gold_unk` (any drift → `setup_wrong`). Answer oracle: forward-substitution + exact integer arithmetic (any mis-value → `wrong`/`gold_error`). |

## The 6 refusals, classified

The headline: **of 6 refusals, only 2 are pure phrasing gaps; 1 is a real missing
capability; 3 are correct wrong=0 boundaries that must stay refused.**

### Gaps — phrasing only (2): `r1-03`, `r1-04`

Structurally **fully supported** — fact + `more_than`/`fewer_than` + `sum_of` are
all admitted families. The *only* blocker is the query template at
`generate/quantitative_comprehension.py:254` requiring `toks[-1] == "have"`:

- `"… do Evan and Finn have altogether?"` → `toks[-1] == "altogether"` → falls through to `unreadable_quantity_query` (`:262`).
- `"… do Gail and Hank have in total?"` → `toks[-1] == "total"` → same.

A trailing aggregate adverb (`altogether`) or qualifier (`in total`) defeats the
`have`-terminal check. This is the **next safe slice**: widen the aggregate-query
recognizer to accept the trailing qualifier when all named parts are already
grounded and unit-compatible. No new arithmetic, no new relation kind. Expected
post-slice: **R1 6 / 0 / 4**.

### Gap — real capability (1): `r1-07`

`Nia(15) = Omar + 9; ask Omar` is an **inverse** problem: the asked entity `Omar`
appears as a *dependency* of a grounded lhs (`Nia`), not as a derivable lhs with
its own equation. The reader can read the structure honestly, but forward
substitution + forward admissibility cannot invert (`Omar = Nia − 9`); `Omar` has
no grounded unit as a bare ref, so `check_admissibility` raises and the build
returns `admissibility_refused` (`:464`). Closing this needs a genuine
reverse-solve contract, not a phrasing tweak — **defer**. Until then the refusal
is the correct wrong=0 behavior (the gold note pins: setup_correct OR refuse,
**never** setup_wrong).

### Correct refusals — must stay refused (3): `r1-08`, `r1-09`, `r1-10`

Admitting any of these would breach wrong=0. They are the refusal boundary
working, not coverage gaps:

- **`r1-08` (pronoun):** `"He has 3 more than her"` has no grounded base for `her`/`she`; binding a guessed referent would fabricate. `unreadable_quantity_clause`.
- **`r1-09` (ungrounded base):** `Quinn = 2×Rosa` with Rosa never given is underdetermined; the `not facts` guard (`:342`) refuses with `no_single_quantity_query`. A "twice as many" with no grounded anchor must refuse.
- **`r1-10` (distractor):** `"Sam has 7 pencils and 3 erasers"` is a compound clause the `X has N unit` template intentionally cannot parse; mis-binding the distractor (`3 erasers`) would corrupt the reading. `unreadable_quantity_clause`. Only an intentionally-designed compound-clause parser would move this — and only with a wrong=0 hazard audit first.

## Decision and trajectory

Next capability slice (per pinned scope): **additive aggregate query variants** —
`"… have altogether?"` and `"… have in total?"` — flipping `r1-03` and `r1-04`
only. Constraints: no new arithmetic, no new relation kind, no inverse solving, no
distractor handling, no pronoun resolution; widen the aggregate-query recognizer
**only** when all named parts are already grounded and unit-compatible.

Expected after that slice:

```text
R1 setup:   6 correct / 0 wrong / 4 refused
R1 answers: 6 correct / 0 wrong / 4 refused / setup_wrong 0 / gold_error 0
```

Remaining 4 refusals after the slice:

- `r1-07-inverse` — real reverse-solve capability, deferred.
- `r1-08`, `r1-09`, `r1-10` — correct wrong=0 refusals; stay refused unless a
  compound-clause/pronoun/inverse capability is *intentionally designed* with its
  own wrong=0 hazard audit.

This keeps the trajectory clean: move only cases whose semantics are already
supported, and leave the refusal boundary intact.
