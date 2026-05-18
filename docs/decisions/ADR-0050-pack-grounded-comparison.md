# ADR-0050 — Pack-Grounded Surface for Cold-Start COMPARISON

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay

---

## Context

[ADR-0048](./ADR-0048-pack-grounded-surface.md) added a pack-grounded
surface for cold-start DEFINITION / RECALL intents — a deterministic,
verbatim composition of the cognition pack's `semantic_domains`
for a single subject lemma.  [ADR-0049](./ADR-0049-intent-subject-extraction.md)
then tightened intent classifier subject extraction so that prompts
like `"What is a procedure?"` produce a clean lemma the pack can
match.

The cognition lane's COMPARISON case
(`comparison_memory_recall_030` — `"Compare memory and recall"`)
still missed.  Investigation:

- Intent classifier correctly tags the prompt `COMPARISON`,
  `subject="memory"`, `secondary_subject="recall"`.
- Both lemmas are in `en_core_cognition_v1` with curated
  `semantic_domains`:
  - `memory` → `("cognition.memory", "memory.semantic", ...)`
  - `recall` → `("operation.recall", "cognition.memory", ...)`
- `_maybe_pack_grounded_surface` was scoped to DEFINITION / RECALL
  only; COMPARISON fell through to the universal disclosure.

The structure is exactly the situation ADR-0048's pattern was
designed for: two pack-known lemmas, no session evidence, deterministic
surface compositable entirely from pack atoms.  The doctrinally
clean fix is a sibling pack-path branch for COMPARISON, with the
same trust-boundary discipline.

---

## Decision

Add a deterministic COMPARISON-shaped pack-grounded surface as a
second branch of `_maybe_pack_grounded_surface`, identical guardrails
to the DEFINITION / RECALL branch.

### Surface format

```text
{a} ({d_a1}; {d_a2}) contrasts with {b} ({d_b1}; {d_b2}) — pack-grounded ({pack_id}). No session evidence yet.
```

Up to two `semantic_domains` per side are emitted to keep the surface
compact.  Every visible non-template token is either one of the two
lemmas or a verbatim pack `semantic_domains` string.

The connective `"contrasts with"` is a fixed-template constant —
identical to the human-readable form of the `contrasts_with` relation
predicate already produced by
`generate/semantic_templates.py:humanize_predicate("contrasts_with")`.
The COMPARISON intent's downstream graph node already uses this
predicate (`graph_planner.graph_from_intent` builds a
`Relation.CONTRAST` edge), so this ADR preserves the existing
COMPARISON connective vocabulary rather than introducing a new one.

### Engagement conditions

`pack_grounded_comparison_surface(a, b)` returns a non-`None` surface
**only** when **all** hold:

- both `a` and `b` are non-empty strings,
- both `a` and `b` are pack lemmas (with `semantic_domains`),
- `a ≠ b` after lowercasing.

`_maybe_pack_grounded_surface` invokes this path **only** when **all**
hold:

- gate fired with `source="empty_vault"` (cold-start session),
- `config.output_language == "en"`,
- intent is `COMPARISON`,
- both `intent.subject` and `intent.secondary_subject` are non-empty.

Any other condition returns `None` and the runtime falls through to
the universal disclosure unchanged.  Safety / ethics refusal still
takes priority above this branch.

### Identical-lemma defer

`pack_grounded_comparison_surface("memory", "memory")` returns `None`.
A comparison between a term and itself carries no contrastive
evidence; the universal disclosure is the correct surface in that
case.  Callers that want a single-lemma surface for `"X"` should use
`pack_grounded_surface("X")` directly via the DEFINITION / RECALL
path.

### Order sensitivity

The COMPARISON surface is **order-sensitive** by design:
`compare(a, b)` and `compare(b, a)` produce distinct surfaces because
the `"contrasts with"` connective is directional.  This matches the
graph-layer behaviour where `Relation.CONTRAST(a → b)` and
`Relation.CONTRAST(b → a)` are distinct edges.

---

## Why this is doctrine-aligned

CLAUDE.md prohibits *opaque LLM fallbacks, stochastic sampling,
hidden normalisation, hot-path repair, and approximate recall*.  This
ADR is:

- **Not opaque.**  Every visible atom is either a lemma supplied by
  the intent classifier or a verbatim pack `semantic_domains` string.
  Pack ID is named in the surface.
- **Not stochastic.**  Deterministic JSONL read, deterministic string
  composition; identical input produces byte-identical output
  (`test_comparison_surface_is_deterministic`).
- **Not hidden normalisation.**  The pack lookup is a separate source
  of grounding, not a normalisation step inside an existing operator.
  No versor, no manifold, no field state touched.
- **Not hot-path repair.**  `UnknownDomainGate` semantics are
  unchanged — the gate still fires; this ADR only broadens what the
  stub-path emits *after* the gate fires, in a narrow intent-typed
  branch.
- **Not approximate recall.**  Exact dictionary lookup on the pack
  lexicon by lemma.  No metric, no neighbourhood, no threshold.

The fundamental architectural move is the same as ADR-0048: the
cognition pack contributes a second source of grounding alongside
the session vault, with provenance preserved end-to-end.  This ADR
extends that contribution from the DEFINITION / RECALL shape to the
COMPARISON shape.

---

## Characterisation — `core eval cognition`

A/B run on the 13-case public cognition split, identical
`RuntimeConfig` except for the merge of this ADR (build on top of
ADR-0049's article-stripping):

| Metric                    | Pre-ADR-0050 | Post-ADR-0050 | Δ           |
|---------------------------|--------------|---------------|-------------|
| `intent_accuracy`         | 100.0 %      | 100.0 %       | 0           |
| `surface_groundedness`    | 61.5 %       | **69.2 %**    | **+7.7 pp** |
| `term_capture_rate`       | 50.0 %       | **58.3 %**    | **+8.3 pp** |
| `versor_closure_rate`     | 100.0 %      | 100.0 %       | 0           |
| `versor_condition < 1e-6` | preserved    | preserved     | invariant   |

The case that lifts is exactly `comparison_memory_recall_030`:

```text
"Compare memory and recall"
  -> intent.tag = COMPARISON, subject="memory", secondary_subject="recall"
  -> both pack lemmas
  -> "memory (cognition.memory; memory.semantic) contrasts with
     recall (operation.recall; cognition.memory) — pack-grounded
     (en_core_cognition_v1). No session evidence yet."
  -> grounding_source = "pack"
```

The remaining unlift cases (CAUSE × 2, VERIFICATION × 1,
CORRECTION × 1) need either teaching-store chains (ADR-0018) or
operator-driven inference — pack lookup cannot supply causal
explanations, verifications, or corrections without fabrication.

---

## Consequences

### What changes

- `chat/pack_grounding.py` gains
  `pack_grounded_comparison_surface(lemma_a, lemma_b) -> str | None`.
- `chat/runtime.py:_maybe_pack_grounded_surface` gains a COMPARISON
  branch that runs before the DEFINITION / RECALL check.
- One new case lifts in the cognition eval.

### What does not change

- `_UNKNOWN_DOMAIN_SURFACE` constant retained; non-pack-lemma,
  non-English, non-DEFINITION/RECALL/COMPARISON paths still return
  the universal disclosure unchanged.
- `UnknownDomainGate` semantics unchanged.
- `ChatResponse.grounding_source` / `TurnEvent.grounding_source`
  enum unchanged — COMPARISON pack-grounded surfaces carry the same
  `"pack"` tag as single-lemma pack-grounded surfaces.  Downstream
  audit consumers do not need a new value to filter on; they already
  distinguish via the surface contents if needed.
- Safety / ethics refusal still takes priority above pack grounding.
- `versor_condition(F) < 1e-6` invariant unaffected (no algebra
  changes).

### Scope limits

- English only (`en_core_cognition_v1`).  Same constraint as
  ADR-0048; multilingual extension is a separate ADR.
- Exactly two operands.  ``"Compare a, b, and c"`` is not yet
  supported by the COMPARISON regex in `generate/intent.py` and is
  out of scope here.
- Connective is fixed to `"contrasts with"` — matching the
  `contrasts_with` predicate already in the relation vocabulary.
  Other comparison flavours (`similar to`, `differs from`, `is like`)
  are not modelled; they would need their own predicates in the
  pack.
- Identical-lemma comparison defers to disclosure.  Callers wanting
  a single-lemma surface should use the DEFINITION / RECALL path.

---

## Cross-References

- [ADR-0018](./ADR-0018-tool-use-scope.md) — `DialogueIntent` and the
  COMPARISON regex this ADR consumes.
- [ADR-0048](./ADR-0048-pack-grounded-surface.md) — the
  DEFINITION / RECALL pack-grounded surface this ADR mirrors for
  COMPARISON; same trust-boundary discipline, same `grounding_source`
  tag.
- [ADR-0049](./ADR-0049-intent-subject-extraction.md) — clean
  subject extraction the COMPARISON path inherits (though COMPARISON
  uses its own named-group regex, not the post-processor;
  ``"memory"`` and ``"recall"`` are already clean from the
  ``_COMPARE_RE`` capture).
- [ADR-0029](./ADR-0029-safety-packs.md) /
  [ADR-0033](./ADR-0033-ethics-packs.md) — sibling-pack-grounded
  contributor pattern this ADR continues to extend from verdict
  surfaces to the answer surface.

---

## Verification

```
tests/test_pack_grounded_comparison.py           — 15 tests, all green
tests/test_pack_grounding.py                     — 18 pre-existing tests still green
tests/test_intent_subject_extraction.py          — 30 pre-existing tests still green
tests/test_semantic_realizer_integration.py      — pre-existing tests still green

Lanes (all green on this branch):
  core test --suite smoke         67 passed
  core test --suite cognition    121 passed
  core test --suite runtime       19 passed
  core test --suite packs          6 passed

core eval cognition (pre → post):
  intent_accuracy        100.0% → 100.0%   (=)
  surface_groundedness    61.5% →  69.2%   (+7.7 pp)
  term_capture_rate       50.0% →  58.3%   (+8.3 pp)
  versor_closure_rate    100.0% → 100.0%   (=)
```

The non-negotiable field invariant (`versor_condition(F) < 1e-6`) is
preserved: this ADR adds a surface-construction branch on the
existing stub path — no algebra changes, no rotor construction, no
field update.
