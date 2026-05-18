# Curriculum Unit — Cognition Pack Saturation v2

**Date:** 2026-05-18
**Author:** Shay
**Active corpus:** 21 chains (was 14; +7 this unit).
**Lift:** cognition lane metrics unchanged (already at architectural ceiling); **saturation lift** is in the live-prompt grounding surface — 7 new prompts that previously fell through to vault/disclosure now route to teaching-grounded surfaces deterministically.

---

## Premise

The first curriculum unit
([`epistemology_v1.md`](epistemology_v1.md)) targeted the
corpus-fixable holdout misses. ADR-0060 and ADR-0061 closed the
architectural holdout misses (correction template, procedure
routing). After those three pieces, the cognition-lane public
split is at 100/100/91.7/100 and holdout at 100/100/83.3/100 —
both at the **architectural ceiling** of the current pack +
surface composition.

The remaining 4/24 holdout term misses are concentrated on
`UNKNOWN`-intent cases that need a distinct selector (out of
scope for this unit).

This unit is **not** about lifting eval metrics. It's about
**saturating the cognition pack's chain coverage** so that more
of the pack's 78 lemmas have reviewed `(subject, intent)` cells
to route through teaching-grounded surfaces. Lift is observable
at the live-prompt level, not in the public/holdout eval splits
(which test a fixed 13/19 cases).

---

## What this unit teaches

Seven new chains across three coherent clusters:

### Cluster A — Cognition-source chains

The cognitive act produces meaning; questions produce
understanding-gap exposure; recall produces awareness of memory.

| Chain | Defensible claim |
|---|---|
| `cause_thought_reveals_meaning` | Thought is the cognitive act through which meaning emerges. |
| `cause_question_reveals_understanding` | Socratic: questions reveal where understanding is incomplete. |
| `cause_recall_reveals_memory` | Recall is the mechanism that brings memory into awareness. |

### Cluster B — Conceptual structure chains

Definitions ground concepts; concepts require definitions
(bidirectional grounding).

| Chain | Defensible claim |
|---|---|
| `cause_definition_grounds_concept` | To define X is to ground the concept X. |
| `verification_concept_requires_definition` | A concept must be definable to count as a concept. |

### Cluster C — Semantic-content chains

Meaning underlies understanding; analogies reveal relations.

| Chain | Defensible claim |
|---|---|
| `cause_meaning_grounds_understanding` | Semantic content underlies understanding. |
| `cause_analogy_reveals_relation` | Analogies reveal hidden structural relations. |

All seven are pack-consistent (`subject` and `object` both in
`en_core_cognition_v1`), use canonical predicates (`reveals`,
`grounds`, `requires`), and open previously-empty
`(subject, intent)` cells.

---

## Lift profile

### Cognition lane (fixed 13/19 cases)

| Split | Pre-v2 | Post-v2 | Δ |
|---|---|---|---|
| public  | 100 / 100 / 91.7 / 100 | 100 / 100 / 91.7 / 100 | byte-identical |
| holdout | 100 / 100 / 83.3 / 100 | 100 / 100 / 83.3 / 100 | byte-identical |

No movement — expected. The 19 holdout cases don't include any
of the subjects this unit teaches. Saturation isn't visible at
the canonical-eval level.

### Live-prompt lift

Seven prompts that previously fell through to the universal
disclosure (or to a vault recall that may or may not return a
coherent surface) now route to deterministic teaching-grounded
surfaces:

```
Why does thought exist?            → [teaching] thought reveals meaning (...)
Why does a question exist?         → [teaching] question reveals understanding (...)
Why does definition exist?         → [teaching] definition grounds concept (...)
Why does meaning exist?            → [teaching] meaning grounds understanding (...)
Why does an analogy exist?         → [teaching] analogy reveals relation (...)
Does a concept require definition? → [teaching] concept requires definition (...)
Why does recall exist?             → [teaching] recall reveals memory (...)
```

Each emits a surface containing the subject, the humanised
connective, the object, and the relevant pack `semantic_domains`
strings — pack-grounded discipline preserved.

### Why saturation matters even when eval numbers don't move

The eval splits test 32 fixed cases (13 public + 19 holdout).
The cognition pack has 78 lemmas; pack-consistent
`(subject, intent)` cells across `{cause, verification}` number
in the hundreds. Today's 21 chains cover ~21 of those cells —
roughly 12% saturation.

Without saturation, **every prompt outside the 32 eval cases is
a coin flip** between vault recall (session-stateful, may return
incoherent surface) and the universal disclosure (no grounding).
Saturation moves the marginal prompt from "coin flip" to
"deterministic teaching-grounded surface."

This is the foundation the composed-surface ADR will sit on:
chain-of-chains composition only produces fluent surfaces when
the constituent chains exist. v2 builds the constituent surface.

---

## Process notes — operator wall-time

Total operator wall-time for this unit, end-to-end:

- Candidate authoring (7 JSONL files): ~3 minutes (mostly typing).
- Proposals (7 × `core teaching propose`): ~13 seconds each — the
  replay gate runs the full cognition lane on each. ~90s total.
- Accepts (7 × `core teaching review --accept`): sub-second each.
- Eval + audit + lane regression check: ~45 seconds.

**Total: ~5 minutes of operator wall-time for 7 reviewed chains.**
The replay-equivalence gate is the dominant cost. Worth the cost:
every accepted chain has a CI-grade no-regression guarantee at the
moment of admission.

---

## Cumulative corpus state

| Phase | Chains active | Cumulative additions |
|---|---|---|
| Pre-curriculum (2026-05-18 morning) | 10 | — |
| After epistemology v1 | 14 | +4 (1 supersede) |
| After cognition saturation v2 | **21** | **+7** |

Now-covered subjects: light, knowledge, memory, correction, creation,
truth, wisdom, understanding, judgment, evidence, inference, thought,
question, definition, meaning, analogy, concept, recall.

Pack-resident subjects still without any teaching chain (~60+
lemmas): account, answer, ask, beginning, belong, cause, compare,
comparison, contrast, context, define, discourse, distinction,
distinguish, explain, figure, follow, ground, identity, image,
infer, learn, life, mean, metaphor, narrative, order, person,
precede, principle, procedure, reason, register, relate, relation,
remember, reveal, rhetoric, simile, spirit, story, style, support,
symbol, teach, tone, verify, voice, word.

The next saturation pass could target a verb-noun balance
(`compare`, `contrast`, `distinguish`, `relate`, `explain`,
`teach`, `learn`) — useful for procedure-intent prompts after the
ADR-0061 path landed.

---

## Cross-References

- [Curriculum: epistemology v1](epistemology_v1.md) — the first
  unit; chain selection rationale and operator workflow.
- [ADR-0057](../decisions/ADR-0057-teaching-chain-proposal-review.md)
  — the propose/review/accept surface.
- [ADR-0060](../decisions/ADR-0060-correction-acknowledgment-topic-lemma.md)
  + [ADR-0061](../decisions/ADR-0061-procedure-intent-pack-grounded-surface.md)
  — architectural surface composition fixes that close the
  remaining-fixable holdout misses.
- Next: composed-surface ADR (chain-of-chains realization) — the
  fluency surface that saturation v2 unlocks.
