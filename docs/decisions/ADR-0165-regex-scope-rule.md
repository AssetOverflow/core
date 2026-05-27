# ADR-0165 — Regex Scope Rule: Lexemes Only, Never Grammar

**Status:** Proposed
**Date:** 2026-05-26
**Author:** Shay
**Anchor:** [[thesis-decoding-not-generating]]
**Companions:** [ADR-0164 — Incremental Comprehension Reader](./ADR-0164-incremental-comprehension-reader.md), [ADR-0114a — Anti-overfitting proof obligations](./ADR-0114a-anti-overfitting-proof-obligations.md), [ADR-0150 — Autonomous inter-session contemplation](./ADR-0150-autonomous-inter-session-contemplation.md), [ADR-0152 — Learning-arc proof corridor](./ADR-0152-learning-arc-demo.md), [ADR-0161 — HITL async queue](./ADR-0161-hitl-async-queue.md)

---

## Context — where regex creeps in, and why the line matters

CORE's existing front-end parsers (`generate/math_candidate_parser.py`,
`generate/recognizer_match.py`) use regex for two structurally different
jobs that have been collapsed into one:

1. **Recognizing lexemes** — "this token chunk is a currency literal," "this
   is a fraction `\d+/\d+`," "this is a numeric expression." These have
   genuinely closed orthographic rules. Regex is the right primitive.

2. **Matching sentence structure** — "this whole sentence is the shape
   `How much MASS_NOUN does ENTITY VERB ...`." These do not have a closed
   rule, because natural language doesn't have one. Regex here is
   enumeration of memorized shapes, dressed up as grammar.

Mixing the two has been the engine's most consistent source of overfitting.
[ADR-0164](./ADR-0164-incremental-comprehension-reader.md) replaces the
sentence-structure use with an incremental compositional reader. This ADR
locks the *boundary*: a structural invariant that any future code must
respect, independent of which front-end implementation is current.

The rule is in the same spirit as the existing structural invariants —
`versor_condition(F) < 1e-6`, "no normalization outside the gate", "no
approximate vault recall", "no hidden stochastic fallback." It is a typed
boundary, not a guideline.

---

## Rule

> **Regex is permitted only at the lexeme level.** Regex must operate on the
> orthographic shape of one structured token or contiguous token-class run
> whose meaning has a genuinely closed rule. Regex must not match across
> word combination, syntactic role, or sentence structure.

**Test for any regex literal in the runtime path:**

If the regex describes "what this piece of orthographic material looks
like," it is a *lexeme primitive* and is permitted.

If the regex describes "how these words combine to mean X," it is a
*grammar template* and is forbidden.

---

## Legitimate uses (lexeme primitives)

These are the canonical examples. The list is extensible through the
teaching corridor (§Population, below).

| Primitive | Example regex | Extracts | Category emitted |
|---|---|---|---|
| `currency_literal` | `\$(\d+(?:\.\d+)?)` | numeric value | QUANTITY, unit_class=currency |
| `numeric_literal` | `\d+(?:\.\d+)?` | numeric value | QUANTITY (unit pending) |
| `fraction_literal` | `(\d+)\s*/\s*(\d+)` | numerator, denominator | QUANTITY, kind=fraction |
| `percentage_literal` | `(\d+(?:\.\d+)?)\s*%` | numeric value | QUANTITY, unit_class=ratio |
| `time_amount_literal` | `(\d+)[- ]?(hour\|minute\|day\|week\|month\|year)s?` | value, unit | QUANTITY, unit_class=time |
| `mass_noun_token` | `(?:money\|profit\|interest\|...)` | the lexeme | UNIT_CATEGORY_TOKEN |
| `decimal_currency` | `\$\d+\.\d{2}` | value | QUANTITY, unit_class=currency |
| `ordinal_token` | `(?:first\|second\|third\|...)` | rank | ORDINAL |

Each primitive has:

- a **name** (closed registry key),
- a **pattern** (a single, focused regex over orthographic shape),
- an **emission** (the typed category + extracted values it produces),
- a **provenance** (which ADR or teaching ratification introduced it).

Primitives never reach across roles. `currency_literal` recognizes
`$18.00`; it does not recognize `$18.00 an hour` (that composition is the
reader's job, not the primitive's).

---

## Forbidden uses (grammar templates)

These are the patterns ADR-0164 deprecates and this rule forbids
recurring. Each example below is a *grammar template* and would be rejected
in code review under this ADR.

```python
# FORBIDDEN — regex matching question shape:
_Q_MASS_NOUN_RE = re.compile(
    r"^How\s+much\s+"
    rf"(?P<unit>{_MASS_NOUN_PATTERN})"
    r"\s+(?:will|did|does|do|would)\s+"
    rf"(?P<entity>{_Q_ENTITY_OR_PRONOUN})\s+"
    rf"(?:have\s+earned\s+|be\s+able\s+to\s+)?{_PATTERN_A_VERBS}"
    r"(?:\s+.*?)?\??\s*$"
)
```

This is a sentence-structure template. It matches across question stem
("How much"), unit ("money"), auxiliary ("will"), entity ("Tina"), and
verb ("earn"). It claims the conjunction of these elements forms a closed
shape. It doesn't.

```python
# FORBIDDEN — regex matching statement structure:
_INITIAL_HAS_RE = re.compile(
    rf"^(?P<entity>{_ENTITY})\s+has\s+(?P<value>\d+)\s+(?P<unit>\w+)\.?\s*$"
)
```

Same problem: matches across subject, verb, value, unit, and clause
shape. Replace with reader composition rules over the categories
`proper_noun_entity`, `possession_verb`, `numeric_literal`, `count_unit_noun`.

```python
# PERMITTED — regex matching one orthographic shape:
_CURRENCY_LITERAL_RE = re.compile(r"\$(\d+(?:\.\d+)?)")
```

This recognizes the surface form of one token (with the `$` prefix). It
has a closed rule (currency notation). It is the correct use of regex.

---

## Code-review test (apply to every new regex)

When reviewing or writing a regex, answer three questions:

1. **What does the regex match?** If the answer names a *piece of
   orthographic material* (a number, a currency amount, a unit-noun set,
   a date), it's a lexeme primitive. If it names *a way words combine*
   (a question shape, an assertion shape, a clause pattern), it's a
   grammar template.

2. **Could a competent linguist describe the matched class as a closed
   set of orthographic rules?** If yes, the regex is appropriate. If the
   class is "things people sometimes say to mean X," the regex is
   enumerating memorized shapes and is forbidden.

3. **What happens when a novel phrasing of the same underlying meaning
   appears?** A lexeme primitive's domain doesn't depend on the rest of
   the sentence, so novel phrasings around it don't break it. A grammar
   template refuses on every novel phrasing. If a refusal on novel
   phrasing is the expected behavior of the regex, it's a grammar
   template.

A regex that fails any of these three is a grammar template and must be
restructured (typically: extract the closed-set vocabulary as a primitive,
move the structural part into reader composition rules).

---

## Population — how the primitive set grows

The closed registry of lexeme primitives is not static. It grows through
the same contemplation → proposal → review corridor that already grows the
language packs and (under ADR-0164) the operational lexicon. This means:

1. **The reader refuses on an unrecognized token shape** — for example,
   it encounters `"$1.5M"` and no current primitive matches it.
2. The refusal is logged with its token shape and position
   (`evals/discovery/discovery_candidates.jsonl` analog).
3. The contemplation runner (ADR-0150/0155) identifies the shape as a
   candidate new primitive and emits a proposal carrying:
   - the proposed primitive's pattern,
   - its emission category and extracted fields,
   - replay-equivalence evidence (acceptance does not lift `wrong` above
     0 on the active corpus),
   - the originating refused tokens.
4. The proposal lands in the HITL queue (ADR-0161). The operator reviews
   the pattern and emission rule. On acceptance, the primitive enters the
   closed registry with its provenance.
5. The reader picks up the new primitive on next run. No code edit. No
   parser rewrite. The engine has been *taught* a new lexical recognizer.

This matches the user's original framing: regex is a **mental tool** the
engine wields. The toolset is bounded and reviewed, but not hard-wired.
Adding a tool follows the same ratification discipline as adding a lemma
or a category.

Two consequences of this design:

- **Operators do not write production regex.** They review proposed
  regex against typed evidence. This eliminates the failure mode where
  a regex sneaks in to "just unblock GSM8K case 0027."
- **The regex set has a measurable closure curve.** Each ratification
  round either does or doesn't reduce the refused-token count.
  Diminishing returns become visible — the regex set is on the same
  measurement substrate as the lexicon and the recognizer corpus.

The bootstrap primitive set lands as part of the ADR-0164 Phase 1 PR. It
covers the closed orthographic forms already known to be needed from the
existing parser (currency, numeric, fraction, percentage, time-amount,
ordinal). Everything beyond bootstrap enters via the corridor.

---

## Consequences

### Positive

1. **Overfit-by-design becomes structurally impossible at the regex
   layer.** A grammar-template regex cannot land in code review without
   violating this ADR explicitly.
2. **Closed-set vocabulary already collected in the existing parser is
   preserved.** Mass-noun lists, possession-verb lists, name lists — all
   become lexeme primitives or lexicon entries.
3. **One regex toolkit, one lexicon, one composition layer.** Three
   layered concerns with separate population pathways and separate
   review criteria. Maintenance scales linearly, not multiplicatively.
4. **The teaching corridor's purpose generalizes.** Today the corridor
   teaches words, domains, and (per the deprecated path) regex
   recognizers. Under this rule it teaches words, categories, and
   lexeme primitives — three orthogonal kinds of evidence, each with a
   clean review predicate.

### Negative / tradeoffs

1. **Refactoring cost is real.** Removing existing sentence-template
   regexes from `math_candidate_parser.py` and `recognizer_match.py` is
   a substantial edit, even with vocabulary preserved. The transition
   plan in ADR-0164 (coexistence → incremental removal) absorbs this.
2. **Lexeme primitives are an attractive surface for new overfitting.**
   A primitive author could try to smuggle structure ("a number followed
   by a currency word followed by 'an hour'") into a single regex. The
   review criteria above are explicit about this; the corridor enforces
   it.
3. **The reader has to do more work.** Composition that used to live
   inside a regex now lives in update rules. This is the point —
   composition is the engine's job, not the regex's — but it shifts
   complexity from one place to another.

---

## Boundaries — what this ADR does **not** say

1. **It does not forbid regex.** Regex remains a primary tool for lexeme
   recognition. The current `evals/`, `scripts/`, and CLI parsers
   already use regex appropriately for log parsing, file-path matching,
   etc. None of that is affected.
2. **It does not specify the reader.** The reader's design is
   ADR-0164's scope. This ADR only constrains where regex may live
   in whatever front-end is current.
3. **It does not retroactively reject older code wholesale.** ADRs
   ADR-0136.S.1–S.4 and ADR-0163.D.2–D.4 introduced grammar templates
   under previous policy. They are deprecated by ADR-0164 with an
   explicit transition plan. New work follows this rule from acceptance
   of this ADR forward.

---

## Cross-references

- **Sibling ADR**: ADR-0164 — the comprehension reader that occupies the
  space this rule clears.
- **Existing structural invariants** (same spirit, different domain):
  - `versor_condition(F) < 1e-6` (CLAUDE.md §Field Invariant)
  - "Allowed normalization sites" (CLAUDE.md §Normalization Rules)
  - "Exact CGA recall" (CLAUDE.md §Core Primitives)
  - ADR-0114a Anti-overfitting proof obligations
- **Population corridor**: ADR-0150 (contemplation), ADR-0152
  (learning-arc proof), ADR-0155 (CI contemplation runner), ADR-0161
  (HITL async queue).
- **Anchor**: `[[thesis-decoding-not-generating]]` — regex is a
  decoder's tool for recognizing fixed orthographic shapes. It is not a
  generator's tool for hallucinating sentence grammars.
