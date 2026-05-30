# ADR-0194 — Labeled-container subject entity shape

**Status:** Proposed (implemented in this PR).
**Extends:** [ADR-0136.S.4](./ADR-0136.S.4-novel-initial-form.md) (sibling-pattern
localisation), [ADR-0123a](./ADR-0123a-inference-shape-synonym.md) (entity slot).
**Composes with:** [ADR-0193](./ADR-0193-aggregate-existential-question-frame.md)
(aggregate question frame).
**Substrate: 0 real-corpus metric flip by design; the value is the entity-shape
generalisation + proven composition with the aggregate question.**

> **One line.** GSM8K labels containers/regions with a trailing single-letter
> or short-numeric label ("Jar A has 28 marbles", "Section G has 10 cars",
> "District 2 has 19 voters"). The initial-possession entity slot
> (`_ENTITY = (?:[A-Z]\w+|[Tt]he\s+\w+)`) captures only "Jar" and then expects
> the possession verb, so the label breaks the match and the statement parses
> to nothing. This adds a separate sibling pattern that REQUIRES a label.

---

## 1. The gap

Both reader paths reject the labeled subject:
- the candidate parser's `_INITIAL_HAS_RE` (`extract_initial_candidates` → 0
  candidates);
- the recognizer's discrete_count anchor (proper-noun single-token subject →
  0 anchors).

"Jamie has 28 marbles" parses (1 candidate); "Jar A has 28 marbles" does not —
purely because of the trailing label.

## 2. Decision

Add `_INITIAL_HAS_LABELED_RE` in `generate/math_candidate_parser.py`, consumed
by a dedicated `_init_has_labeled_candidates` helper wired into
`extract_initial_candidates`:

```
^<Noun> <label> (has|have|had|started) <value> [adj] [unit] [of/in/for/with …]
   label = a single uppercase letter OR 1-2 digits
```

- **Sibling-pattern localisation** (mirrors ADR-0136.S.4's
  `_INITIAL_HAS_INDEF_RE`): the global `_ENTITY` is unchanged for every other
  path (operations, comparisons, questions).
- **The label is required**, so a bare subject ("Jamie has 28 marbles") never
  reaches this pattern and yields no duplicate candidate.
- **The label is bounded by the following possession verb**, so a multi-word
  noun does NOT match: "Jar Apple has 5 marbles" → no candidate ("Apple" is not
  a single-letter label), "Box Set has 12 items" → no candidate.
- Same value/unit tail and money normalisation as `_INITIAL_HAS_RE`.

### Why this is safe (the firewall is the precondition)

The label widening only makes a statement *parse* into an initial possession.
wrong=0 is held downstream by the completeness guard (ADR-0191) + the
round-trip filter + branch disagreement — a mis-parse leaves source quantities
uncovered and refuses. Full-corpus verification: **wrong=0 HOLDS** (7,473 q);
`train_sample` byte-identical **4/46/0**; the synthetic-registry capability-axis
`wrong=0` gate and the G5 aggregate lane both stay green.

## 3. Evidence

- **Composes with ADR-0193:** "Jar A has 28 marbles. Jar B has 12 marbles. How
  many marbles are there in total?" → **40.0**; three-container variant → 10.0.
- **0 real-corpus flip** (honest framing): of the 3 real container-subject
  problems under an aggregate question, the only multi-container aggregate
  ("Jar A has 28 marbles. Jar B has 12 more marbles than jar A. Jar C has twice
  as many as jar B. … altogether?") additionally requires **comparative-additive
  + comparative-multiplicative + lowercase-reference** resolution. This is the
  composition-wall lesson again: an entity-shape widening is necessary, not
  sufficient.
- **Tests:** `tests/test_labeled_container_subject.py` (labeled containers
  parse; bare subjects yield no duplicate; multi-word nouns don't match a
  label; composes with the aggregate question).

## 4. Consequences & follow-ups

- The labeled-container entity shape is banked; it becomes load-bearing the
  moment **comparative reading** (the actual aggregate blocker — ADR-0131.G.2 /
  `core-comparatives`) can compose `compare_additive`/`compare_multiplicative`
  ops into an aggregate answer, and the **lowercase-reference** ("jar A" inside
  a later clause) resolves to the labeled entity.
- Compound enumeration and the recognizer-path labeled subject remain closed;
  open them only if a serving need is proven under the firewall.
