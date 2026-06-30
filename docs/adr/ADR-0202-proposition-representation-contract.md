# ADR-0202 — Proposition Representation Contract (`proof_chain`)

**Status:** Accepted (normative contract — single source for the canonicalizer and the proof corpus)
**Date:** 2026-06-02
**Relates to:** ADR-0201 (propositional canonicalizer — the formula layer's implementation),
ADR-0144 (PropositionGraph epistemic carrier — the atom layer's home),
ADR-0143/0142 (recognition outcome / epistemic state taxonomy),
ADR-0132 (binding-graph data model — the proof DAG substrate),
ADR-0131.3 (bounded-grammar word-problem lane — the eval-case shape this slots into).

---

## Why this document exists

`proof_chain` introduces propositional formulas to CORE. Two producers must agree
on **one** representation or they diverge: the canonicalizer
(`generate/logic_canonical.py`) and the proof corpus authored in parallel.

CORE already carries four "proposition"-named structures — the articulation
`Proposition`/`PropositionGraph` (`generate/`), the ADR-0144 epistemic carrier
(`recognition/`), and the ADR-0132 symbolic-math binding graph. **None** is a
truth-functional propositional-logic formula representation. So the formula
language is net-new; but its *atoms* must ground to the existing epistemic carrier,
not float free — otherwise `proof_chain` becomes a fifth, disconnected proposition
dialect, the exact fragmentation ADR-0144 was created to resolve.

This contract is that single source. **The canonicalizer is authoritative for the
formula grammar**; any grammar change updates this doc in the *same* PR (mirroring
the `docs/runtime_contracts.md` discipline).

The representation is **two layers**:

- **Atom layer** (authoritative, existing) — atoms are declared stable symbol ids
  that bind to ADR-0144 `EpistemicNode`/`FeatureBundle` carriers.
- **Formula layer** (net-new — ADR-0201) — truth-functional formulas over those
  atoms, canonicalized to ROBDD identity.

---

## 1. Formula layer — grammar (exact, from `generate/logic_canonical.py`)

### 1.1 Tokens

- **Atom:** an identifier — first char `[A-Za-z_]`, subsequent `[A-Za-z0-9_]`.
  Atom ids are **case-sensitive** (`P` ≠ `p`). Reserved keywords (below) are not atoms.
- **Constants:** `true`, `false` (keywords, case-insensitive).
- **Operators** — each kind has multiple accepted spellings (ASCII, doubled,
  unicode, keyword). All spellings of a kind are interchangeable and produce the
  identical canonical key:

  | Kind | Spellings |
  |---|---|
  | NOT (unary) | `not`, `~`, `!`, `¬` |
  | AND | `and`, `&`, `&&`, `∧` |
  | OR | `or`, `\|`, `\|\|`, `∨` |
  | IMPLIES | `implies`, `->`, `→`, `⊃` |
  | IFF | `iff`, `<->`, `↔`, `≡` |
  | grouping | `(` … `)` |

  Keyword operators are matched case-insensitively (`AND` = `and`). Whitespace is
  insignificant. Any character outside this grammar is a refusal (§3).

### 1.2 Precedence and associativity

Lowest → highest binding:

```
IFF  <  IMPLIES  <  OR  <  AND  <  NOT  <  atom / ( … )
```

- `IMPLIES` is **right-associative**: `P -> Q -> R` ≡ `P -> (Q -> R)`.
- `IFF`, `OR`, `AND` are left-associative (associativity is semantically
  irrelevant under ROBDD, but the parse is fixed so errors are crisp).
- `NOT` is prefix unary. Parentheses override precedence.

### 1.3 Grammar (EBNF)

```ebnf
formula   = iff ;
iff       = implies , { IFF , implies } ;
implies   = or , [ IMPLIES , implies ] ;          (* right-assoc *)
or        = and , { OR , and } ;
and       = unary , { AND , unary } ;
unary     = NOT , unary | atom ;
atom      = ATOM | "true" | "false" | "(" , iff , ")" ;
```

### 1.4 Canonical form

A formula is canonicalized to a **Reduced Ordered Binary Decision Diagram (ROBDD)**
under the **sorted-atom variable ordering** (the atoms appearing in the formula,
sorted lexicographically). The reduced diagram is serialized to the
`canonical_key` string. Contract:

- **Equivalence = byte-equality** of `canonical_key`. Two formulas are logically
  equivalent **iff** their keys are identical.
- **Tautology → `"T"`**, **contradiction → `"F"`** (every tautology shares the key
  `T` regardless of atoms; likewise `F`).
- **Logically-irrelevant atoms are dropped from the support**: `P` and
  `P ∧ (Q ∨ ¬Q)` produce the same key; `Q` is not in the result's `atoms`.
- The key is **byte-deterministic across processes** (structural serialization —
  no object ids, no hashing, no dict-order dependence), satisfying the
  `trace_hash` discipline. It is human-inspectable, not an opaque digest:
  e.g. `(P→Q)∧(R∨¬S)∧P` → `0:S?F:T;1:R?T:@0;2:Q?@1:F;3:P?@2:F`.

The key is the propositional twin of `BoundEquation.rhs_canonical` (ADR-0132): when
`proof_chain` wires to the binding graph, the canonical key occupies `rhs_canonical`,
the discharged premises occupy `dependencies`, and the inference rule occupies
`operation_kind`.

---

## 2. Atom layer — declared symbol ids that bind to the epistemic carrier

**Atoms are not free-form prose.** Each atom is a declared, stable symbol id
(matching the §1.1 atom grammar) that **will bind** to an ADR-0144 `EpistemicNode`
carrying a recognized `FeatureBundle`. A corpus case declares its atoms explicitly.

### 2.1 Declaration rules

- Atom ids are unique within a case; the same id denotes the same proposition
  throughout that case. Recommended convention: `<Letter>[_<slug>]`, e.g.
  `P_rains`, `Q_ground_wet`.
- Every atom declares a human-readable `gloss`.
- **Where an atom maps to a recognizable fact, the case MUST record the intended
  `FeatureBundle` binding** (the feature name→value mapping per ADR-0143/0144),
  so the corpus is future-compatible with the grounding-half wiring and needs **no
  second pass** when atom-grounding lands. The actual `EpistemicNode.node_id`
  (`teaching_set_id:turn_index`) is assigned at recognition time and is therefore
  **not** authored into the corpus; the binding resolves by matching the recorded
  feature mapping.
- Atoms that are pure logical variables with no recognizable-fact referent (e.g.
  abstract `P`/`Q` in a rule-shape case) record `gloss` only and `binding: null`.
  This is allowed and expected for schematic cases.

### 2.2 Per-case atom block (normative shape)

```json
{
  "atoms": {
    "P_rains": {
      "gloss": "it is raining",
      "binding": {
        "features": { "agent": "sky", "relation": "is", "state": "raining" }
      }
    },
    "Q_ground_wet": {
      "gloss": "the ground is wet",
      "binding": { "features": { "agent": "ground", "relation": "is", "state": "wet" } }
    },
    "R": { "gloss": "an abstract proposition", "binding": null }
  },
  "premises": ["P_rains -> Q_ground_wet", "P_rains"],
  "conclusion": "Q_ground_wet",
  "rule": "modus_ponens",
  "expected": "provable"
}
```

`features` keys are the `FeatureBundle` feature names (ADR-0143 `BoundFeature.name`);
values are their bound values. The bundle's canonical sorted-by-name order is
enforced by `FeatureBundle.__post_init__` at grounding time — authors need not
pre-sort. `premises`/`conclusion`/`rule`/`expected` fields compose with the
ADR-0131.3 bounded-grammar case shape; this contract governs only `atoms` and the
formula strings.

---

## 3. Honesty boundary (binding)

- **Propositional logic only** — finite Boolean atoms. In this regime the ROBDD is
  canonical and equivalence is decidable, so the `wrong == 0` soundness gate
  transfers intact.
- **No predicate / first-order / quantified logic.** Equivalence over quantifiers
  on infinite domains is undecidable; there is no ROBDD-style canonical form.
  **Do NOT claim `wrong == 0` for quantified reasoning.** A formula that requires
  quantifier reasoning is out of regime and must **REFUSE**
  (`out_of_decidable_regime`), not be silently dropped to a weaker check.
  Quantifier-free fragments and specific decidable theories are later,
  separately-scoped work, each with its own honest decidability claim.
- **Refusal-first, no approximation.** The canonicalizer either returns the exact
  canonical key or refuses:
  - out-of-grammar input → `LogicError` → `REFUSED`;
  - ROBDD exceeds the node budget → `LogicBudgetError` (a `LogicError` subclass) →
    `REFUSED` (`canonicalization_budget_exceeded`) — refuse rather than churn.
  Corpus cases that expect refusal must name the typed reason.

---

## 4. Conformance checklist (corpus authors)

A case conforms to this contract iff:

- [ ] every formula uses only the §1 grammar — no invented connectives or spellings;
- [ ] every atom referenced in a formula is declared in the case's `atoms` block;
- [ ] atom ids match the §1.1 atom grammar and are stable within the case;
- [ ] every declared atom carries a `gloss`; recognizable-fact atoms carry an
      intended `FeatureBundle` `binding`, schematic atoms carry `binding: null`;
- [ ] no quantifiers, predicates, or function symbols appear;
- [ ] the expected outcome is one of `provable` / `not_provable` / `refused`
      (with a typed reason for `refused`);
- [ ] equivalence/identity claims rely on the `canonical_key`, never on formula
      surface string equality.

---

## 5. Source-of-truth rule

`generate/logic_canonical.py` is authoritative for the formula grammar and
canonical form. This document is authoritative for the atom layer and the honesty
boundary. Any change to the formula grammar updates §1 of this doc in the **same
PR** as the code change. The proof corpus conforms to this doc; it does not extend
the grammar or the atom convention on its own.

## Governance Cross-Reference (ADR-0225)

This late-corpus ADR is governed by [ADR-0225](./ADR-0225-adr-corpus-hygiene.md):

- Safety boundaries: changes must preserve ADR-0027/0028/0029 identity and safety-pack boundaries; no identity, safety, or policy mutation is implied unless explicitly reviewed.
- Versor closure: runtime field paths must preserve `versor_condition(F) < 1e-6`; this ADR does not authorize hidden normalization or hot-path drift repair.
- Reconstruction-over-storage: evidence must remain reconstructive and content-addressed rather than duplicating opaque state.
- Replay-equivalence: serving, teaching, promotion, or checkpoint changes require a named deterministic replay / byte-equivalence gate.
- Mutation standing: any durable corpus, pack, policy, or epistemic-status mutation remains reviewed, proposal-only until accepted, or proof-carrying as applicable.
