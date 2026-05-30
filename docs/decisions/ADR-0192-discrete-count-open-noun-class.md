# ADR-0192 — Open the discrete_count counted-noun class (firewall-backed)

**Status:** Proposed (implemented in this PR). Widens the
[ADR-0163.D.2](./ADR-0163-recognizer-storage.md) discrete_count matcher.
Builds directly on [ADR-0191](./ADR-0191-candidate-graph-completeness-guard.md)
— the completeness firewall is the precondition that makes this safe.
**Substrate PR: 0 metric delta by design; the value is 8× more statements
parsing into solver state, wrong=0-proven on the full real corpus.**

> **One line.** The discrete_count matcher gated the counted noun against a
> CLOSED ratified set (`observed_counted_nouns`): "Betty has 24 marbles"
> matched only because "marbles" was ratified, while "Randy has 60 mango
> trees" / "Sam has 12 red apples" produced no anchor purely because the noun
> was unseen. This opens the single-anchor possession/acquisition path to an
> open noun phrase, keeping every other narrowness layer. Wrong=0 is held
> downstream by the ADR-0191 completeness guard + round-trip + branch
> disagreement — not by the curated noun list.

---

## 1. The gap (microscope finding, 2026-05-30)

The full-corpus microscope (`scripts/gsm8k_microscope.py`) ranked the serving
reader's refusals across all 7,473 real GSM8K train questions.
**`discrete_count_statement` is the dominant wall: 3,850 first-wall refusals**
("recognizer matched but produced no injection"). Dissecting *why* the matcher
emits no anchor:

| sub-shape | count | extractable? |
|-----------|------:|--------------|
| `subj verb N <multi-word / adj+noun>` ("Randy has 60 **mango trees**") | ~1,004 | **yes — matcher too narrow** |
| count on a prepositional object ("sold clips **to 48** friends") | ~550 | no — correctly conservative |
| attributive number ("a **120-page** book") | ~120 | no — verb not possession/acquisition |
| number is a unit (rate/currency/time) | ~380 | no — different category |
| relational / "other" | ~1,400 | no — needs composition |

Pinned blocker: the matcher only extracts when the counted noun is in
`spec.observed_counted_nouns` (a closed ratified set). `"Betty has 24
marbles"` matched (ratified); `"Randy has 60 mango trees"` / `"Sam has 12 red
apples"` / `"Randy has 60 trees on his farm"` all emitted **anchors=0** solely
because the noun (or noun phrase) was unseen — not because of the trailing PP
(the regex already allowed trailing content) and not because the shape was
ambiguous.

## 2. Decision

Open the counted-noun slot of the **single-anchor** discrete_count extractor
(`_extract_discrete_count_re_open` in `generate/recognizer_match.py`):

- The noun slot matches either a ratified `observed_counted_nouns` entry
  (closed branch — preserves casing canonicalization and capitalized
  compounds like "Pokemon cards") **OR** an OPEN lowercase noun phrase:
  1–3 consecutive lowercase word tokens, none a boundary/stop word
  (prepositions, conjunctions, determiners, comparatives).
- `(?-i:...)` makes the open branch lowercase-only so it never captures a
  following proper noun; the stop-word lookahead bounds the phrase so it
  never swallows a trailing prepositional phrase ("mango trees on his farm"
  → "mango trees").
- **Every other narrowness layer is unchanged**: proper-noun subject,
  possession/acquisition verb whitelist, single numeric token, no
  clause-split. The compound-enumeration path stays closed.

### Why this is safe (the firewall is the precondition)

The closed noun set existed to prevent open-vocabulary mis-parses from
reaching the solver. ADR-0191 moved that guarantee downstream: an open-vocab
mis-parse now hits the **completeness guard** (every source quantity must be
consumed), the **round-trip filter** (every slot must ground in source), and
**branch-disagreement** refusal. So wrong=0 is held by the firewall, not by
the noun list. The dangerous shapes are still refused *before* the open noun
even applies — `"is reading a 120-page book"` refuses because "is" is not a
possession/acquisition verb; `"has many apples"` refuses on the count token;
`"has 60 apples and 30 oranges"` refuses on the single-count / clause-split
layers.

## 3. Evidence

- **Substrate gain: 61 → 494** discrete_count anchors extracted+injected over
  the full real corpus (8×), all clean.
- **wrong=0 holds** on the full 7,473-question corpus — 494 statements parse,
  **zero confabulations**. This is the direct proof that open-vocabulary
  recognition is safe under the ADR-0191 firewall.
- **0 metric delta** (`train_sample` byte-identical **4/46/0**; full-corpus
  correct unchanged at 4). The widening makes *statements* parse; the
  *problems* still refuse downstream at the composition wall (multi-statement
  chaining + question-target). This is expected: statement parsing is
  necessary, not sufficient. Refusal families shift accordingly — problems
  advance from the discrete_count first-wall to later walls.
- **Tests:** new `tests/test_discrete_count_open_noun_class.py` (open-vocab
  now extracts; noun phrase stops before prepositions; dangerous shapes still
  refuse). The one closed-contract assertion
  (`test_unobserved_counted_noun_refused`) is updated to the new open
  contract. All other discrete_count narrowness tests unchanged and passing.

## 4. Consequences

- This is **substrate**, deliberately landed with no metric movement. Its
  value is (a) the foundation every discrete_count composition will consume —
  a statement cannot be composed before it parses — and (b) the empirical
  proof that the firewall makes open-vocabulary recognition wrong=0-safe,
  retiring the closed-set constraint for the simple possession/acquisition
  shape.
- The remaining discrete_count walls (prepositional-object counts,
  attributive numbers, rate/currency) are correctly still refused — they are
  *not* simple possession and must not be admitted by this path.
- The next layer is composition (multi-statement same-unit aggregate +
  question-target parsing) which now has parsing statements to consume.

## 5. Follow-ups

- Re-run `scripts/gsm8k_microscope.py --corpus <train.jsonl>` after the
  composition layer lands to confirm wrong=0 holds *and* the metric moves.
- Compound-enumeration ("N1 noun1 and N2 noun2") noun class remains closed;
  open it only after the single-anchor open path is proven in serving.
