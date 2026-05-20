# Prompt-Diversity Eval Lane — Contract

**Lane:** `prompt_diversity`
**Version:** v1 (proposed)
**Created:** 2026-05-20
**Companion to:** ADR-0084 (Definitional Layer for Lexicon Packs)

---

## What this lane measures

Every other eval lane in this repo measures one of two things:

- a single architectural property (versor closure, anchor-lens
  engagement, register variation), against a small fixture, or
- end-to-end cognition correctness against ~13 prompts rooted on
  the same handful of subjects (`light`, `truth`, `knowledge`,
  `memory`, `wisdom`).

We've been overfitting to that fixture without admitting it. Every
ADR since 0048 has used the same demo prompt — *"Why does light
exist?"* — to claim surface lift. The system's response to that
prompt has gotten visibly longer; we do not actually know what it
does on prompts of different shape, sophistication, or domain.

This lane measures **how surface quality and grounding generalize
across question types**, not just on the canonical chain-walk
fixture.

## Axes the suite varies

| Axis | Levels |
|---|---|
| **Question shape** | definition, cause/why, comparison, narrative ("tell me about X"), procedure ("how do I X"), recall ("do you remember X"), correction ("no, X is Y"), verification ("does X require Y"), unknown-intent fallback |
| **Sophistication** | bare lemma ("light?"); simple full question ("what is light?"); multi-clause question ("what does light have to do with knowledge?"); embedded clause ("when you say X reveals Y, do you mean Z?") |
| **Domain** | cognition, kinship (`en_core_relations_v2`), cross-pack composition (cognition × kinship), OOV (deliberately unknown lemma), adversarial (ambiguous subject, contradiction, identity probe) |
| **Surface expectation** | propositional answer; explanation; sequence; comparison-contrast; honest refusal; honest "I don't know"; honest "no session evidence yet" |

The cross-product is intentionally not enumerated. The suite picks
~50 cases that cover the matrix at one or two cases per cell.

## Scoring rubric

Two metrics carried over from the cognition lane:

| Metric | Definition |
|---|---|
| `intent_accuracy` | Fraction of cases with correct intent classification. |
| `versor_closure_rate` | Fraction with `versor_condition < 1e-6`. |

Three new metrics specific to this lane:

| Metric | Definition |
|---|---|
| `response_shape_fit` | Fraction of cases where the surface's structural shape matches the question shape. Definition → noun-phrase or copular sentence. Cause/why → explanation (cause-marker or "because"-style or definition-driven). Procedure → ordered sequence. Comparison → two-subject contrast. Refusal/unknown → honest disclosure. Measured by a per-case `expected_shape` field in the JSONL plus a small per-shape classifier in the runner. |
| `audit_in_surface_rate` | Fraction of cases whose surface string contains audit metadata that should belong in telemetry (e.g. `teaching-grounded (`, `No session evidence yet.`, `cognition.X; logos.Y`). **Lower is better.** This metric exists explicitly to quantify the leak that ADR-0085 / a future "surface vs envelope" ADR will close. Today this rate is essentially 100% — the suite establishes a baseline so progress is measurable. |
| `gloss_quote_rate` | Fraction of cases whose surface visibly draws from a pack `gloss` (post-ADR-0084) rather than only from `semantic_domains` tags. v1: 0% (composer is unchanged in ADR-0084). The metric is in place so ADR-0085's lift is quantifiable. |

## Pass criteria

v1 has **no pass thresholds** beyond `versor_closure_rate == 1.00`.
The lane's job at v1 is to establish a baseline distribution across
the matrix. Pass thresholds get set in v2 after one full pass
through ADR-0084 → 0085 → 0086 has run and we know which axes are
actually moveable.

This is deliberate: setting a threshold against today's baseline
would just freeze a fixture. The point is the *distribution*, not
the score.

## What this lane does NOT measure

- Naturalness or fluency of language (no LLM judge — we have no
  ground truth for "natural-sounding" and refuse to mint one).
- Factual correctness of the corpus (that's the ratification
  pipeline's job).
- Performance / latency (that's the bench's job).
- Cross-provider comparison (that's `frontier_compare/`'s job).

## Categories tested (v1 case file)

```
definition_simple        — "What is X?" for X in {definition, evidence, recall, kinship, parent}
definition_multi_clause  — "When you say X is Y, do you mean Z?"
cause_simple             — "Why does X exist?" for X in {light, knowledge, family}
cause_multi_clause       — "Why does X imply Y if Y is itself the result of Z?"
comparison_simple        — "Compare X and Y"
comparison_cross_pack    — "How does kinship relate to knowledge?"
narrative_simple         — "Tell me about X"
narrative_multi_subject  — "Tell me how X, Y, and Z relate"
procedure_simple         — "How do I verify X?"
procedure_unknown_subject— "How do I verify zorblax?"
recall_session_empty     — "What was the last thing I said about X?"
correction_simple        — "No, X is actually Y"
correction_indirect      — "I think you misunderstood — let me try again"
verification_simple      — "Does X require Y?"
verification_double_neg  — "Doesn't X not require Y?"
unknown_intent_fallback  — "Mhm." / "..." / "Hmm interesting"
oov_single_word          — A nonsense lemma
oov_in_real_question     — "What is the role of {nonsense} in epistemology?"
adversarial_ambiguous    — "Set" / "Bank" / "Lead" (homographs)
adversarial_identity     — "You're not actually intelligent, are you?"
adversarial_contradiction— "I know X reveals truth, but you said X hides truth"
```

Target: ~50 cases. Each case carries `id`, `category`,
`question_shape`, `sophistication`, `domain`, `prompt`,
`expected_intent`, `expected_shape`, `expected_terms` (optional),
`requires_versor_closure`.

## Runner

`runner.py` reuses the existing `evals._parallel.run_cases_parallel`
worker pool and `evals.framework` plumbing. Reports to
`evals/prompt_diversity/results/v1_{public,dev}_{timestamp}.json`.

## How to run

```bash
core eval prompt-diversity
# or
python -m evals.prompt_diversity.runner
```

## How to read the output

JSON report with the five metrics above plus per-case breakdowns
grouped by `(question_shape, sophistication, domain)`. The
`audit_in_surface_rate` and `gloss_quote_rate` distributions tell
you where surface quality lives today vs. where ADR-0085 will move
it.

## When it has failed and why

This lane is new. The expected v1 state:

- `intent_accuracy`: ~70–85% (current intent classifier was trained
  on cognition-shaped prompts; cross-pack and adversarial cases
  will dip).
- `versor_closure_rate`: 1.00 (the algebra invariant should hold
  for every case the pipeline accepts).
- `response_shape_fit`: low — most cases will fall back to the
  chain-walk shape regardless of question shape.
- `audit_in_surface_rate`: ~100% — every surface today carries
  trust-boundary text in-band.
- `gloss_quote_rate`: 0% — composer doesn't know about glosses yet.

The v1 numbers ARE the baseline. The lane fails its purpose only
if the distribution looks identical to the cognition lane (i.e.
the suite isn't actually diverse).

## Cross-references

- ADR-0084 — definitional layer this suite is calibrated to.
- Future ADR-0085 — gloss-aware composer; expected to move
  `gloss_quote_rate` and `response_shape_fit` upward.
- Future "surface-vs-envelope" ADR — expected to drop
  `audit_in_surface_rate` toward zero by routing trust-boundary
  text to telemetry.
- `evals/cognition/contract.md` — the lane this one extends across
  axes.
