# ADR-0060 — CORRECTION Acknowledgement Carries the Corrected-Topic Lemma

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0053](./ADR-0053-cognition-lane-closure.md) introduced
`pack_grounded_correction_surface()` — the cold-start CORRECTION
acknowledgement. When a user begins a session with a meta-cognitive
correction utterance (`"No, that's wrong"`, `"Actually, X means Y"`),
there is no prior turn to apply the correction to, so the runtime
emits a deterministic pack-grounded surface stating that fact:

```
correction received — pack-grounded (en_core_cognition_v1):
cognition.correction; teaching.review; dialogue.repair.
No prior turn in this session to correct yet.
```

This surface was honest but **topic-blind**: a user who said
`"Actually, truth requires evidence"` got a response that referenced
`correction` but never `truth`. The holdout case
`correction_truth_040` expected `["truth"]` in `expected_terms` and
missed — contributing one of the 5 term-capture misses on the
holdout split.

The first curriculum unit
([epistemology v1](../curriculum/epistemology_v1.md), `2acf71f`)
closed one corpus-fixable miss (`verification_wisdom_036`). Three of
the remaining four were architectural; `correction_truth_040` was the
cleanest to address.

---

## Decision

Extend `pack_grounded_correction_surface` to accept an optional
`text: str | None` argument. When supplied, the surface composer
extracts the **first pack-resident topical lemma** from the utterance
(left-to-right token order, excluding the meta-cognition lemma
`correction` itself and dialogue fillers `be` / `have`) and weaves it
into a fixed template:

```
correction received — pack-grounded ({pack_id}):
{correction_domains}. Noted topic: {lemma} ({lemma_domains}).
No prior turn in this session to correct yet.
```

When no topical lemma is found (or `text` is `None`), the surface
degrades to the ADR-0053 topic-less template byte-identically.

### Trust-boundary invariants preserved

- **Every visible non-template token** is still either the lemma
  `correction`, the topical lemma, or a verbatim `semantic_domains`
  string from the ratified pack. No inference, no rewording.
- **Determinism.** Same `text` → same surface bytes. The selector is
  left-to-right token order; no scoring, no NLP heuristic, no LLM.
- **Backward compatibility.**
  `pack_grounded_correction_surface()` with no argument returns the
  ADR-0053 template byte-identically. Existing 15 tests in
  `tests/test_pack_grounded_correction.py` continue to pass.
- **The "No prior turn in this session to correct yet."
  trust-boundary label** — distinguishing this cold-start surface
  from the post-correction teaching-repair path
  (`teaching/correction.py`) — is preserved in both variants.

### Stopword selection

Two stopword classes are excluded from topic-lemma selection:

1. **The meta-cognition lemma itself** (`correction`, `correct`) —
   echoing it as the topic would be circular; it's already the
   subject of the acknowledgement template.
2. **Dialogue fillers** (`be`, `have`) — pack-resident lemmas that
   classify but carry no topical signal in a correction utterance.

This stopword set is deliberately tiny. Expanding it requires an
amendment to this ADR — pack-resident lemmas that survive both the
"have semantic_domains" gate and the natural-language flow of a
correction utterance are real topic candidates by default.

### Token normalization

Tokens are lowercased and stripped of attached punctuation
(`,.;:!?"'()[]{}`) before pack-lookup. This handles common surface
forms like `"truth."`, `'truth'`, `truth,` without requiring a full
tokenizer.

---

## Why text-level extraction, not intent.subject

`intent.subject` after ADR-0049 head-noun extraction returns
`", truth requires evidence"` for the prompt
`"Actually, truth requires evidence"` — the correction intent's
subject extractor preserves the post-marker tail rather than
extracting a single head noun. Using `intent.subject` would require
either:

1. Extending ADR-0049's head-noun normalization to the CORRECTION
   intent — substantial change to upstream classification logic.
2. Re-parsing `intent.subject` at the surface composer — equivalent
   work to parsing the raw text.

Parsing the raw text at the surface layer is cleaner: it isolates
the fix, doesn't perturb upstream classification, and lets the
correction acknowledgement own its own topic-extraction policy.

---

## Verification

```
tests/test_correction_topic_lemma.py        14 passed
  - extraction: first lemma / skips correction / skips fillers /
    None on empty / strips punctuation / case-insensitive
  - surface: contains corrected lemma / contains topic domains /
    degrades to ADR-0053 / preserves trust label / deterministic /
    correct pack_id
  - end-to-end: correction_truth_040 emits 'truth' / no-pack-lemma
    still grounds

tests/test_pack_grounded_correction.py      15 passed   (ADR-0053; backward compat)

Lanes (regression check):
  core test --suite smoke           67 passed
  core test --suite cognition      121 passed
  core test --suite teaching        17 passed
```

### Cognition lane lift

| Split | Metric | Pre-ADR-0060 | Post-ADR-0060 |
|---|---|---|---|
| **public** | intent / surface / term / versor | 100 / 100 / 91.7 / 100 | **100 / 100 / 91.7 / 100** (unchanged) |
| **holdout** | intent / surface / term / versor | 100 / 94.7 / 75.0 / 100 | **100 / 94.7 / 79.2 / 100** (+4.2pp term_capture) |

The +4.2pp matches the single-case fix: `correction_truth_040` now
captures `truth`. The remaining three holdout misses
(`procedure_define_010`, `unknown_spirit_041`, `unknown_word_018`)
are out of scope for this ADR.

---

## Consequences

### What changes

- `chat/pack_grounding.py` — `_extract_correction_topic_lemma`
  helper and an optional `text` parameter on
  `pack_grounded_correction_surface`.
- `chat/runtime.py` — call site passes `text` through. Single line.

### What does not change

- ADR-0053's contract for the no-text path: byte-identical surface.
- Refusal priority: a `SafetyVerdict` violation still pre-empts the
  acknowledgement (per ADR-0036).
- The pack-grounded discipline: zero LLM-generated tokens in the
  surface; every visible word is either lemma, pack-domain, or
  fixed template constant.
- `versor_condition(F) < 1e-6` invariant: untouched — this ADR
  only changes surface composition.

---

## Scope limits

- **Single topical lemma per surface.** A correction utterance
  containing multiple pack-resident lemmas (`"Actually, truth
  requires evidence"`) currently surfaces only the first
  (`truth`). Extending to "Noted topics: truth, evidence" is a
  reasonable follow-up but expands the trust surface (more
  tokens, more template branches) and was deferred.
- **English path only.** The stopword set and tokenizer are
  English-specific. Non-English correction utterances will not
  match pack lemmas and will degrade to the topic-less template —
  no behaviour change vs ADR-0053.
- **No subject-claim propagation to corpus.** The corrected claim
  (`truth requires evidence`) is acknowledged as a topic, not as
  a candidate teaching chain. Promoting corrections into the
  corpus is the `teaching/correction.py` repair path, which
  engages only once a prior turn exists.

---

## Cross-References

- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the
  CORRECTION acknowledgement contract this ADR extends.
- [ADR-0049](./ADR-0049-intent-subject-extraction.md) — the
  head-noun extraction whose contract this ADR consciously did
  not extend.
- [Curriculum: epistemology v1](../curriculum/epistemology_v1.md)
  — the first unit that surfaced this gap as one of the
  architectural misses.
