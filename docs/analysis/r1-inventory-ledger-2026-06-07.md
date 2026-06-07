# R1 comprehension inventory ledger

**As of:** PR-7b / C0 (inverse reader frame), on `main @ 0e6a7f9a` (post-#619) + this branch
**Lane state:** R1 setup **7 / 0 / 3** · R1 answers **7 / 0 / 3** (`setup_wrong 0`, `gold_error 0`) · 15-case setup **15 / 0 / 0**

This is a decision artifact, not a capability claim. It records exactly which
`evals/setup_oracle/r1_gold.jsonl` fixtures the typed comprehension organ now
*reads and answers*, which it *refuses*, and — for each refusal — the semantic
family that blocks it and whether that refusal is a coverage gap or a load-bearing
wrong=0 boundary that **should stay refused**. It exists so the next slice moves
only the cases whose semantics are already supported, and never mistakes a correct
refusal for a gap.

> **History.** This ledger opened at **4 / 0 / 6** (`main @ 5ada1392`, post-PR-6d).
> The additive aggregate-query slice (#618) flipped `r1-03`/`r1-04` → **6 / 0 / 4**;
> the inverse reader frame (PR-7b / C0) flips `r1-07` → **7 / 0 / 3**. With that, R1
> is **closed**: the three remaining refusals are correct wrong=0 boundaries, not gaps.

## Reproduce

```bash
.venv/bin/python -m evals.setup_oracle r1          # setup lane  -> 7/0/3
.venv/bin/python -m evals.setup_oracle r1-answers  # answer lane -> 7/0/3, setup_wrong 0, gold_error 0
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
| `r1-03-more-total` | `Evan = Finn(10)+5; ask total **altogether**` | ✅ correct | `25` | additive aggregate + aggregate-query phrasing | — | **admitted** |
| `r1-04-fewer-total` | `Hank = Gail(20)−6; ask total **in total**` | ✅ correct | `34` | additive aggregate + aggregate-query phrasing | — | **admitted** |
| `r1-07-inverse` | `Nia(15) = Omar + 9; ask Omar` | ✅ correct | `6` | inverse target (ask the *base* of a relation) | — | **admitted** |
| `r1-08-ambiguous-referent` | `He has 3 more than her; ask she` | ⛔ refused | ⛔ refused | unresolved pronoun referent | `unreadable_quantity_clause` | **correct refusal** |
| `r1-09-missing-base` | `Quinn = 2×Rosa; Rosa never given` | ⛔ refused | ⛔ refused | ungrounded base (no grounded fact) | `no_single_quantity_query` | **correct refusal** |
| `r1-10-distractor` | `Sam has 7 pencils **and 3 erasers**; ask Tom` | ⛔ refused | ⛔ refused | distractor in a compound clause | `unreadable_quantity_clause` | **correct refusal** |

## The 7 admitted families and the invariant protecting each

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
| additive aggregate (query-phrasing) | `r1-03`, `r1-04` | the trailing-qualifier recognizer (`altogether` / `in total`) is honored **only** for the multi-part `sumquery` form; an ungrounded or unit-incompatible part is refused downstream at admissibility (`unit_unbound` / `unit_mismatch`). No new arithmetic, no new relation kind (#618). |
| inverse target | `r1-07` | inverse frame (PR-7b): a `more`/`fewer`-than whose **subject is a known fact** and whose **referent is the otherwise-ungrounded query target** binds the base's unit **from the relation** so the equation is admissible; the answer oracle reverse-solves it (PR-7a). Bounded — single base == query target (no chains), known subject value, base not otherwise grounded, ≤1 inverse (`multiple_inverse_bases` else), never over times/divide. |
| all admitted | — | setup oracle: `reader_rel == gold_rel ∧ reader_units == gold_units ∧ reader_unk == gold_unk` (any drift → `setup_wrong`). Answer oracle: forward-substitution + one narrow reverse-solve + exact integer arithmetic (any mis-value → `wrong`/`gold_error`). |

## The 3 refusals, classified — all correct wrong=0 boundaries

The headline: **of 3 remaining refusals, 0 are gaps; all 3 are correct wrong=0
boundaries that must stay refused.** Admitting any would breach wrong=0; they are
the refusal boundary working, not coverage gaps:

- **`r1-08` (pronoun):** `"He has 3 more than her"` has no grounded base for `her`/`she`; binding a guessed referent would fabricate. `unreadable_quantity_clause`.
- **`r1-09` (ungrounded base):** `Quinn = 2×Rosa` with Rosa never given is underdetermined; the `not facts` guard refuses with `no_single_quantity_query`. A "twice as many" with no grounded anchor must refuse. (Note: distinct from `r1-07` — there the *subject* `Nia` is a known fact and only the *base* is unknown, so the inverse frame can solve it; here *nothing* is grounded.)
- **`r1-10` (distractor):** `"Sam has 7 pencils and 3 erasers"` is a compound clause the `X has N unit` template intentionally cannot parse; mis-binding the distractor (`3 erasers`) would corrupt the reading. `unreadable_quantity_clause`. Only an intentionally-designed compound-clause parser would move this — and only with a wrong=0 hazard audit first.

## Decision and trajectory

**R1 is closed at 7 / 0 / 3.** Every fixture whose semantics the typed organ can
honestly read is admitted; the three remaining refusals are load-bearing wrong=0
boundaries (pronoun resolution, ungrounded base, distractor parsing) — each would
need an *intentionally designed* capability with its own hazard audit, and none is
the next priority.

The next capability axis is **not** another R1 slice. It is **R2: finite integer
linear-constraint systems** (two-category problems — buses/seats, chickens/legs,
tickets/prices, coins/values) built as a parallel off-serving organ on the same
disciplined ladder (gold → setup oracle → solver → answer verifier → reader). R1
stays frozen at 7 / 0 / 3 as that work proceeds; the invariant carried forward is
the same one this ledger tracks: **move only cases whose semantics are already
supported, leave the refusal boundary intact, never produce a `setup_wrong`.**
