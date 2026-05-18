# ADR-0061 — PROCEDURE Intent Routes to Pack-Grounded Surface

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

Pre-ADR-0061, the `PROCEDURE` intent (`"How do I X?"`, `"How can I Y?"`)
had no pack-grounded composer. The runtime's
`_maybe_pack_grounded_surface` dispatched on:

- `COMPARISON` → `pack_grounded_comparison_surface`
- `CAUSE` / `VERIFICATION` → `teaching_grounded_surface`
- `CORRECTION` → `pack_grounded_correction_surface`
- `DEFINITION` / `RECALL` → `pack_grounded_surface`

`PROCEDURE` fell through to the universal "insufficient grounding"
disclosure. This was the second architectural holdout miss surfaced
by the [epistemology v1 curriculum unit](../curriculum/epistemology_v1.md):

- `procedure_define_010` — `"How do I define a concept?"` — expected
  `term=["concept"]`. Pre-ADR: universal disclosure → both surface
  and term miss.
- `procedure_verify_034` — `"How do I verify a claim?"` — no
  `expected_terms`, but pre-ADR fell through to disclosure → surface
  miss (though the case had no terms-based fail).

The teaching corpus does not carry procedural chains
(`chat.teaching_grounding._VALID_INTENTS = frozenset({"cause",
"verification"})`); procedural knowledge is fundamentally different
in kind from causal/verifying claims and deserves its own ratification
path (out of scope for this ADR). The pack-grounded surface for
procedures is the **honest cold-start fallback**: ground the topic in
pack semantics, state explicitly that ratified step-by-step guidance
does not exist yet.

---

## Decision

Add `pack_grounded_procedure_surface(subject_text: str) -> str | None`
to `chat/pack_grounding.py` and wire `IntentTag.PROCEDURE` through it
in `_maybe_pack_grounded_surface`.

### Surface format

```
"procedure-grounded ({pack_id}): {lemma} ({d1}; {d2}).
 Step-by-step guidance for {lemma} is not yet ratified
 in this session."
```

Every visible non-template token is either the topical lemma or a
verbatim `semantic_domains` string from the ratified pack. The
trailing clause is the constant trust-boundary label, analogous to
ADR-0053/0060's `"No prior turn in this session to correct yet."`

### Topic-lemma selector: **last** pack-resident lemma

Procedure subjects emerge from the intent classifier as verb
phrases:

| Prompt | `intent.subject` | Pack-resident tokens | Selected |
|---|---|---|---|
| `How do I define a concept?` | `"define a concept"` | `define`, `concept` | `concept` |
| `How can I correct an error?` | `"correct an error"` | `correct` | `correct` |
| `How do I verify a claim?` | `"verify a claim"` | `verify` | `verify` |
| `How do I learn this?` | `"learn this"` | `learn` | `learn` |

The procedure verb tends to be the first pack-resident lemma; the
**topic** of the procedure tends to be the last. Picking the last
captures the user's actual subject of interest without requiring
POS tagging or syntactic analysis.

When the verb is the only pack-resident lemma (object is OOV or a
filler), the verb is the topic by elimination — keeps surface
coverage on procedure utterances with non-pack objects.

### Stopword set

Only `be` and `have` are stopworded — they're pack-resident but
carry no topical signal. Procedure verbs (`define`, `verify`,
`correct`, `learn`) are deliberately NOT stopworded, so the
verb-as-fallback rule fires when the object is OOV.

### Fall-through preserved

When `subject_text` contains **no** pack-resident lemma (`"How do I
do stuff?"`), the composer returns `None` and the runtime falls
through to the universal disclosure. This preserves the honesty
contract from ADR-0053: never fabricate surface from nothing.

---

## Verification

```
tests/test_procedure_surface.py             15 passed
  - extraction: last-wins / verb-by-elimination / skips be/have /
    None on empty / strips punctuation / case-insensitive
  - surface: contains topic lemma / contains topic domains /
    pack_id present / "not yet ratified" trust label preserved /
    None for no pack lemma / deterministic
  - end-to-end: procedure_define_010 emits 'concept' /
    no-pack-lemma falls through to disclosure /
    'verify a claim' grounds with verb

Lanes (regression check):
  core test --suite smoke           67 passed
  core test --suite cognition      121 passed
  core test --suite teaching        17 passed
```

### Cognition lane lift

| Split | Metric | Pre-ADR-0061 | Post-ADR-0061 |
|---|---|---|---|
| **public** | intent / surface / term / versor | 100 / 100 / 91.7 / 100 | **100 / 100 / 91.7 / 100** (unchanged) |
| **holdout** | intent / surface / term / versor | 100 / 94.7 / 79.2 / 100 | **100 / 100.0 / 83.3 / 100** |

Two cases fixed:
- `procedure_define_010`: surface and term (+1/24 = +4.2pp on
  term_capture; +1/19 on surface_groundedness).
- `procedure_verify_034`: surface only (no `expected_terms`;
  contributes the remaining 4.5pp on surface_groundedness).

Combined surface_groundedness lift: **94.7% → 100.0%** on holdout.

### Remaining holdout misses

Two cases still emit the universal disclosure on `UNKNOWN` intent:

- `unknown_spirit_041` — `"spirit wisdom truth"` — expected
  `["wisdom", "truth"]`.
- `unknown_word_018` — `"word beginning truth"` — expected
  `["word", "truth"]`.

`expected_surface_contains` is empty for both (so they pass the
surface_groundedness check trivially via `all([]) == True`), but
the expected terms (4 across the two cases) are not in the
disclosure surface. Closing them requires a pack-grounded
`UNKNOWN` composer that surfaces all pack-resident lemmas in the
utterance — a deliberately-distinct ADR scope (different intent,
different selector semantics, different trust-boundary clause).

---

## Why not extend the teaching corpus to procedural chains

A teaching chain in `cognition_chains_v1.jsonl` carries
`(subject, intent, connective, object)` with
`intent ∈ {cause, verification}`. The schema implies a propositional
claim: "subject {connective} object". Procedural knowledge is
fundamentally different in kind:

- A procedure is a *sequence* (often ordered, often conditional),
  not a binary relation.
- A procedure's correctness depends on the procedural context
  (the user's existing state, tools, prior steps), not on
  alignment with reviewed evidence.
- Promoting "to define X, do A then B then C" into the same
  schema as "knowledge requires evidence" would silently equate
  two different epistemic structures — exactly the kind of hidden
  normalisation CLAUDE.md prohibits.

A future ADR could introduce a parallel `procedure_chains_v1.jsonl`
with its own schema and a reviewed-procedural-knowledge composer.
ADR-0061 is the **honest fallback** for the cold-start case in the
absence of that infrastructure.

---

## Cross-References

- [ADR-0048](./ADR-0048-pack-grounded-surface.md) — the original
  `pack_grounded_surface` for DEFINITION / RECALL intents.
- [ADR-0050](./ADR-0050-pack-grounded-comparison.md) — the
  COMPARISON-shaped sibling.
- [ADR-0053](./ADR-0053-cognition-lane-closure.md) — the
  CORRECTION acknowledgement; ADR-0061 follows the same
  trust-boundary pattern.
- [ADR-0060](./ADR-0060-correction-acknowledgment-topic-lemma.md)
  — the sibling fix that landed the correction topic lemma.
- [Curriculum: epistemology v1](../curriculum/epistemology_v1.md)
  — the unit that surfaced this gap.
