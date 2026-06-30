# ADR-0049 — Intent Classifier Head-Noun Subject Extraction

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0048](./ADR-0048-pack-grounded-surface.md) added a pack-grounded
surface for cold-start DEFINITION / RECALL turns where the subject lemma
is in `en_core_cognition_v1`.  The eval lift was real but partial.
Investigating the misses showed they were not pack gaps — the pack
*does* carry the lemmas — they were **subject-extraction gaps** in
`generate/intent.py`:

| Prompt                          | Pre-0049 `subject`            | Reason for miss            |
|---------------------------------|-------------------------------|----------------------------|
| `What is a procedure?`          | `"a procedure"`               | Article not stripped        |
| `What is a relation?`           | `"a relation"`                | Article not stripped        |
| `Why does light exist?`         | `"does light exist"`          | Aux verb + tail not stripped|
| `Why does knowledge require evidence?` | `"does knowledge require evidence"` | Aux verb + tail not stripped|
| `Does memory require recall?`   | `"Does memory require recall?"` | Whole prompt; rule matched full string |
| `Is light a wave?`              | `"Is light a wave?"`          | Whole prompt; rule matched full string |

The `_RULES` table in `generate/intent.py` was producing **subject
spans**, not **subject lemmas**.  Downstream consumers
(`graph_planner.graph_from_intent`, ADR-0048
`_maybe_pack_grounded_surface`, future teaching-store inference) need
the lemma — they cannot match a noun phrase like `"a procedure"`
against a lexicon keyed on `procedure`, and they cannot key a graph
node off `"does light exist"` cleanly.

The cleanest fix is at the classifier boundary: produce a clean
lemma in `DialogueIntent.subject` so every consumer benefits without
each implementing its own article-stripping heuristic.

---

## Decision

Add a deterministic, pack-agnostic post-processor
`_normalize_subject(phrase, tag)` in `generate/intent.py` that runs
after the rule table fires and rewrites the subject span according
to its intent's syntactic shape.

### Behaviour by intent

| Intent                    | Transform                                              |
|---------------------------|--------------------------------------------------------|
| `DEFINITION` / `RECALL` / `PROCEDURE` | strip trailing punctuation, strip leading articles; preserve multi-word noun phrases (e.g. `"artificial intelligence"`) |
| `CAUSE` / `VERIFICATION`              | strip trailing punctuation, strip leading aux verbs (`is`, `are`, `does`, `do`, `can`, `could`, …), strip leading articles, return the **head noun** (first remaining token) |
| `CORRECTION`              | strip trailing punctuation, strip leading articles      |
| `UNKNOWN`                 | bypass (preserve raw input for debugging)              |
| `COMPARISON` / `TRANSITIVE_QUERY` / `FRAME_TRANSFER` | already captured by their own named-group regexes; not routed through `_RULES` |

### Aux-verb and article sets

Frozen sets in `generate/intent.py`:

```python
_ARTICLES = frozenset({"a", "an", "the"})
_AUX_VERBS = frozenset({
    "is", "are", "am", "was", "were", "be", "been", "being",
    "does", "do", "did",
    "has", "have", "had",
    "can", "could", "would", "should", "shall", "will",
    "might", "may", "must",
})
```

These are **closed** word lists.  The normalizer does not depend on
the cognition pack, the language pack manifold, or any external state
— it is a pure syntactic transform.

### Fallback

If stripping aux verbs and articles would empty the subject (e.g.
`"What is the?"`), the normalizer returns the cleaned original phrase
rather than producing an empty subject.  Downstream consumers
(`_maybe_pack_grounded_surface`) already handle empty subjects
correctly (return `None`), but preserving a non-empty subject keeps
debugging output and trace surfaces readable.

---

## Why this is doctrine-aligned

CLAUDE.md prohibits *opaque LLM fallbacks, stochastic sampling, hidden
normalisation*.  This ADR:

- **Is not opaque.**  Both word sets are static frozen Python sets,
  visible at module scope.  Every transformation rule is explicit.
- **Is not stochastic.**  Identical input produces byte-identical
  `DialogueIntent` (`test_normalization_is_deterministic`).
- **Is not hidden normalisation of the algebra.**  The normalizer
  rewrites a *typed dataclass field*, not a versor, not a manifold,
  not a field state.  No hot-path math is touched.  No
  `versor_condition` invariant is in scope.
- **Is not coupled to a specific pack.**  The aux-verb / article
  lists are English syntactic categories, not pack vocabulary.  The
  ADR-0048 pack lookup remains the *consumer* of the cleaner lemma;
  the classifier itself does not load any pack.

The trust-boundary discipline is preserved: user-controlled text is
still escaped at all log/display sites by their respective handlers;
this ADR changes only the in-process classification output.

---

## Characterisation — `core eval cognition`

A/B run on the 13-case public cognition split, identical
`RuntimeConfig` except for the merge of this ADR:

| Metric                    | Pre-ADR-0049 | Post-ADR-0049 | Δ           |
|---------------------------|--------------|---------------|-------------|
| `intent_accuracy`         | 100.0 %      | 100.0 %       | 0           |
| `surface_groundedness`    | 46.2 %       | **61.5 %**    | **+15.3 pp**|
| `term_capture_rate`       | 33.3 %       | **50.0 %**    | **+16.7 pp**|
| `versor_closure_rate`     | 100.0 %      | 100.0 %       | 0           |
| `versor_condition < 1e-6` | preserved    | preserved     | invariant   |

The two cases that lift through the pack-grounded path
(`definition_procedure_023` and `definition_relation_026`) carry the
article-stripping flow:

```text
"What is a procedure?"  -> intent.subject == "procedure"
"What is a relation?"   -> intent.subject == "relation"
```

Both then match the cognition pack lexicon and emit a pack-grounded
surface via ADR-0048.

The CAUSE / VERIFICATION head-noun extraction (`"Why does light
exist?"` → `"light"`, `"Does memory require recall?"` → `"memory"`)
does not directly move the eval on this split because CAUSE and
VERIFICATION intents are scope-excluded from ADR-0048's pack path.
That work is **foundational for the next ADRs**: a future
COMPARISON / CAUSE / VERIFICATION pack path or teaching-store
inference will inherit clean lemmas without re-implementing the
extraction.

---

## Consequences

### What changes

- `generate/intent.py` gains the `_normalize_subject` post-processor
  and two closed-set frozen sets (`_ARTICLES`, `_AUX_VERBS`).
- `DialogueIntent.subject` is now a clean lemma (or noun phrase) for
  every intent that routes through `_RULES`.
- ADR-0048 pack-grounded surface coverage broadens from
  4 → 6 of 13 cognition-eval cases.

### What does not change

- `IntentTag` enum is unchanged.
- The rule table (`_RULES`) is unchanged — the post-processor runs
  after a rule fires.
- COMPARISON, TRANSITIVE_QUERY, FRAME_TRANSFER, and BELONG_QUERY
  paths use their own named-group regexes and were already producing
  clean subjects; they are not routed through `_normalize_subject`.
- `UnknownDomainGate` semantics are unchanged.
- `versor_condition(F) < 1e-6` invariant — no algebra is touched.

### Scope limits

- English only.  The aux-verb / article lists are English; a future
  multilingual cognition pack ADR would extend the sets or move them
  into the language pack itself.
- The PROCEDURE intent's `"How can I VERB ARTICLE NOUN"` shape
  (`"How can I correct an error?"`) is not handled: stripping the
  verb requires either part-of-speech tagging or a closed list of
  imperative verbs.  Out of scope here.  The case
  `procedure_correct_035` has empty `expected_surface_contains` in
  the eval anyway, so it does not affect surface_groundedness.
- Multi-word noun phrases for DEFINITION / RECALL (e.g.
  `"artificial intelligence"`) are preserved as-is.  Pack lookup
  matches on the cleaned phrase; if the pack carries the multi-word
  lemma, it lifts; if not, it falls through to the universal
  disclosure.  This is the doctrinally correct behaviour.

---

## Cross-References

- [ADR-0018](./ADR-0018-tool-use-scope.md) — defines
  `DialogueIntent` and the `_RULES` table this ADR post-processes.
- [ADR-0048](./ADR-0048-pack-grounded-surface.md) — the consumer
  whose pack-lookup gap this ADR closes by producing clean lemmas.
- [ADR-0046](./ADR-0046-forward-graph-constraint.md) /
  [ADR-0047](./ADR-0047-wire-forward-graph-constraint.md) — the
  forward-graph-constraint pipeline that consumes `intent.subject`
  via `graph_planner.graph_from_intent`; cleaner subjects make
  graph nodes single-lemma rather than noun-phrase, increasing the
  chance the AdmissibilityRegion's CGA neighbourhood intersects the
  walk's candidate pool.

---

## Verification

```
tests/test_intent_subject_extraction.py           — 30 tests, all green
tests/test_intent_proposition_graph.py            — pre-existing tests still green
tests/test_pack_grounding.py                      — pre-existing tests still green
tests/test_semantic_realizer_integration.py       — pre-existing tests still green

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed

core eval cognition (pre → post):
  intent_accuracy        100.0% → 100.0%   (=)
  surface_groundedness    46.2% →  61.5%   (+15.3 pp)
  term_capture_rate       33.3% →  50.0%   (+16.7 pp)
  versor_closure_rate    100.0% → 100.0%   (=)
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`) is
preserved: this ADR touches a typed dataclass field, no algebra.
