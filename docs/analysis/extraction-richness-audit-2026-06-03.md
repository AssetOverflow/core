<!-- analysis | extraction-richness-audit | 2026-06-03 | read-only, no code -->

# Extraction-Richness Audit — ADR-0179 named cases, reconciled to the shipped tree

**Status:** Analysis only. No serving, eval, or code edits. Every claim below
reproduced live against `origin/main` @ `2cb0922` via read-only
`extract_quantities` / derivation-composer / `parse_and_solve` probes.

**Scope.** Open [ADR-0179 — Extraction Richness](../decisions/ADR-0179-extraction-richness.md),
read the exact cases its §Context table names as starved by the thin
`(\d+(?:\.\d+)?)\s+([a-z]+)` extractor, and verify for each — *against the tree* —
whether it actually refuses at the **extraction** layer (`generate/derivation/extract.py`)
or **downstream** (`clauses` / `compose` / `multistep` / `search` / `verify`). Then map
the minimal productions the **derivation/** composer still needs. Per the brief, this is
the audit feeding ADR-0207's "ADR-0179 extraction richness" execution lever; it touches
no code.

> **Reader-disjointness caveat (load-bearing).** ADR-0179 enriches the **sealed,
> practice-only derivation reader** (`generate/derivation/*`). `chat/` does not import it,
> so none of this moves the serving metric. The serving `6/44/0` comes from the **disjoint
> candidate-graph reader** (`generate/math_candidate_graph.py`). A case can be
> serving-correct and derivation-starved at once (0003, 0024 below). This audit is about
> the derivation reader, as Task 3 specifies.

---

## 1. The headline: ADR-0179's §Context table is stale

ADR-0179 (dated 2026-05-28, when serving was `3/47/0`) diagnoses a thin extractor. The
tree has moved. `generate/derivation/extract.py`'s own module docstring + live probes
confirm the following are **already integrated**:

| ADR-0179 sub-phase | In tree? | Evidence (live) |
|---|---|---|
| **EX-1** word-numbers (`three` → 3.0, hyphen compounds) | **LANDED** | `_WORD_QTY_RE`; `0024` extracts `(3.0,'times','three')` |
| **EX-2** currency/decimal + **bare-decimal grounding** | **LANDED** | `math_roundtrip.py:362` "ADR-0179 EX-2"; `_value_grounds("0.75")` → `True`; `0003` extracts `(0.75,'','0.75')` |
| **EX-4** list-unit inheritance (trailing unit) | **LANDED** | `_LIST_WITH_TRAILING_UNIT_RE` |
| **EX-5** sentence-final / unit-less number | **LANDED** | `_FINAL_NUMBER_RE` |
| **EX-6** hyphen-bonded number-unit (`25-foot`) | **LANDED** | `_HYPHEN_QTY_RE` (ADR-0163-F2) |
| Unit hygiene (function-word filter: `$0.75 each`→blank, not `each`) | **LANDED** | `_NON_UNIT_WORDS`; `0003`/`0024` blank the adjunct unit |
| **EX-3** multi-word units (`jumping jacks`, `stop signs`) | **DEFERRED** | `TestEX3StillDeferred` pins two documented traps (below) |

So **EX-3 (multi-word units) is the only open extraction production.** It was deferred
deliberately, not overlooked — see §3. ADR-0207 should cite ADR-0179 with this
reconciliation, not the stale §Context framing.

---

## 2. Per-case verification — extraction layer vs downstream

Live extraction (`extract_quantities`) and end-to-end derivation composer
(`search_multiplicative` / `compose_sequential` / `search_chain`) at HEAD:

### 0003 — `$0.75` erasers (gold 864) — **extraction CLOSED; ADR-0179's diagnosis is stale**
- Extracts `(48,'boxes')`, `(24,'erasers')`, `(0.75,'')` — the decimal **grounds** (EX-2).
- Derivation `search_chain` → **864.0 = gold.** The case the ADR says "refuses" now **solves**
  in derivation. (Serving also correct, fast-path.)
- **Residual: none.** This case is a positive proof EX-2 landed and works end-to-end.

### 0024 — Sidney jumping jacks (gold 438) — **purely extraction-blocked (EX-3 + head inherit)**
- Extracts `(20,'jumping')`, `(36,'')`, `(40,'')`, `(50,'')`, `(3.0,'times','three')`.
  EX-1 caught `three`; but `"jumping jacks"` → `"jumping"` (multi-word truncation), and the
  list states its unit **once at the head** (`"20 jumping jacks on Monday, 36 on Tuesday…"`),
  so the trailing-unit EX-4 rule does not fire. Units are non-uniform (`jumping` vs `''`).
- Derivation: all composers → **None** (GB-2 same-unit list-sum never fires).
- **Residual: extraction** — a *head*-unit list-inheritance production + a bounded multi-word
  unit. (Serving solves 0024 independently; this gap is derivation-only.)

### 0016 — Rudolph stop signs (gold 2) — **both layers**
- Extracts `(2,'')`, `(5,'miles')`, `(3,'')`, `(17,'stop')` — `"stop signs"` → `"stop"`
  (EX-3 truncation), and `"2 more than 5"` / `"3 less than 17"` are extracted as **separate
  bare numbers**, not composed operands.
- Derivation `search_chain` → 510.0 (≠ gold 2); the self-verify gate refuses it (no wrong
  commit — wrong=0 holds). The raw 510 is a non-committed candidate.
- **Residual: extraction (EX-3 `stop signs`) AND downstream** — word-arithmetic derived
  operand (`N more/less than M`) and a `"per X"` division question target. Extraction alone
  will not solve 0016.

### 0033 — Rachel's father's age (gold 60) — **purely downstream**
- Extracts `(12,'years')`, `(7.0,'times','7')`, `(5,'years')`, `(25,'years')` — **complete.**
  `"Rachel is 12 years old"` grounded cleanly (the `years old` postmodifier did not corrupt
  it: only the first content word `years` is taken).
- Derivation: all composers → **None**. The block is the multi-step age chain
  (grandfather = 7×12 = 84; mother = ½·84 = 42; father = 42+5 = 47) plus the **temporal
  offset** `"when she is 25"` (Rachel +13 → father 60).
- **Residual: downstream only** (compose/multistep). Extraction needs nothing here.

### Summary table

| Case | Serving | Derivation @ HEAD | Block locus | Genuine residual |
|---|---|---|---|---|
| 0003 | correct | **solves 864** | — | none (EX-2 closed it) |
| 0024 | correct (438) | refuses | **extraction** | EX-3 multi-word + head-unit inheritance |
| 0016 | refused | gate-refused (raw 510) | **both** | EX-3 + word-arithmetic operand + division target |
| 0033 | refused | refuses | **downstream** | multi-step chain + temporal offset |

**Of the four cases ADR-0179 names as extraction-starved, exactly one (0024) is purely an
extraction problem today.** 0003 is already solved, 0033 is purely downstream, 0016 needs
both. This is the single most important correction the audit surfaces: extraction richness
is largely *shipped*; the remaining derivation coverage is now mostly a **composition**
problem, not an extraction one.

---

## 3. Why EX-3 was deferred (the two traps — preserved, not re-litigated)

`extract.py`'s docstring + `TestEX3StillDeferred` (`tests/test_adr_0179_extract.py`) pin two
failure modes that defeat the tightest lookahead rule the ADR-0165 lexeme constraint admits:

1. **Connective-crossing.** A greedy lowercase unit span eats the connective:
   `"6 apples and 4 apples"` → unit `"apples and"`, regressing GB-2 same-unit detection.
2. **Postmodifier-adjective tails.** Even `digit + word + word + (?=terminator)` fires on
   `"25 years old?"` → `"years old"` instead of `"years"`, regressing
   `test_adr_0176_ms1_question_target`. Endemic across 0006/0033 and MS2 chain tests.

Any EX-3 proposal must clear both without regressing those pinned tests.

---

## 4. Minimal productions proposed (analysis only — no code)

Ordered by leverage / safety. All are lexeme-level (ADR-0165), refuse-preferring
(over-extraction can only cost a *refusal* through the self-verify gate, never a wrong
commit), and each is independently shippable behind the existing derivation gate.

### P1 — Head-unit list inheritance (unblocks 0024; sidesteps both EX-3 traps)
Symmetric to the landed trailing-unit EX-4, but for the unit stated **once at the list
head**: `"<n0> <UNIT-PHRASE> <adjunct>, <n1> <adjunct>, … <nk> <adjunct>"` → attach
`<UNIT-PHRASE>` to the unit-blank members `n1…nk`. Bound the head `<UNIT-PHRASE>` on the
right by a **closed adjunct stop set** `{on, at, in, per, each, of, and}` — so
`"20 jumping jacks on Monday"` yields unit `"jumping jacks"`, stopping cleanly before `on`.
This makes 0024 a uniform-unit list → GB-2 list-sum fires, **without** general multi-word
capture, so neither §3 trap is touched. Highest leverage, lowest risk.

### P2 — Bounded 2-word content unit with a closed measurement-postmodifier stop list
The general `"stop signs"` shape (0016 extraction half). Allow exactly two content words
**only when** the second is not in a closed stop list of measurement postmodifiers
`{old, tall, long, wide, deep, high, away, apart, ago, …}` **and** not a connective. This is
the production the Track-C brief judged "too open-ended"; the audit's position is that the
stop set is *enumerable and closed* if scoped to measurement postmodifiers, and must ship
with `TestEX3StillDeferred` converted to a positive/negative matrix (the two traps become
must-refuse rows). Medium leverage, medium risk — gate it behind P1.

### P3 — (explicitly **not** extraction — flagged, out of Task-3 scope)
0016's `"N more/less than M"` word-arithmetic operand and `"per X"` division question
target, and 0033's multi-step age chain + temporal `"when she is 25"` offset, are
**composition** concerns for `compose.py` / `multistep.py` / `search.py`, not `extract.py`.
The audit names them so they are not mistaken for extraction work: feeding richer quantities
will not solve 0016/0033 without these downstream productions.

---

## 5. Bottom line for ADR-0207

- ADR-0179's "extraction is too thin" framing is **mostly resolved in-tree** (EX-1/2/4/5/6 +
  unit hygiene landed). Cite the reconciled state, not the stale §Context table.
- The one open extraction lever is **EX-3**, and its highest-value, lowest-risk slice is
  **P1 (head-unit list inheritance)** — it unblocks 0024 in derivation with no EX-3-trap
  exposure.
- The broader Phase-5b coverage wall is now **composition** (P3), not extraction. ADR-0207's
  two diagnosed levers (ADR-0179 extraction richness + ADR-0164 lexicon expansion) should be
  read with this correction: extraction richness is near-complete; the residual lift is in
  the comprehension/derivation composer, gated by self-verification (wrong=0 preserved).

**Invariants observed by this audit:** read-only; train_sample reproduced live `6/44/0`;
no serving code touched; the no-ref `<N>×` hazard remains refused (untouched).
