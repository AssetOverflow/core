# ADR-0066 — Turn-level composition (Plan Phase 3)

**Status:** Accepted
**Date:** 2026-05-18
**Author:** Shay
**Phase:** Plan Phase 3 (turn-level composition — the articulation gap)
**Builds on:** ADR-0048 / ADR-0052 / ADR-0062 / ADR-0064 / ADR-0065

---

## Context

Phases 1 + 2 closed two flywheels: the chain-gap and OOV-gap signal
streams. The vocabulary and corpus axes both grow under operator
review. But surfaces still felt mechanical — *each turn was freshly
minted from primitives, never referenced backward*.

Three intents were missing from the runtime:

1. **Thread anaphora** — "As we just established, X reveals Y, and
   on this turn..." Conversation reads as a thread, not a series of
   independent grounded surfaces.
2. **NARRATIVE** — "Tell me about X." A multi-clause composer that
   surfaces *everything* the system has reviewed about X, across
   every registered corpus.
3. **EXAMPLE** — "Give me an example of X." The converse of
   NARRATIVE: surfaces chains where X is the *object*, inverting
   the typical chain access pattern.

Phase 3 adds all three deterministically — no prose generation, no
content synthesis.

---

## Decision

### P3.1 — Session-thread context (`chat/thread_context.py`)

A bounded FIFO of `TurnSummary` records, owned by `ChatRuntime`.
Each turn appends one summary (intent_tag, subject, grounding_source,
chain_id, corpus_id) via the runtime's internal `_push_thread_summary`.
The cold-start path classifies intent up-front unconditionally so
the summary captures the subject even when no sink is attached
(previously gated on sink attachment — now gated only on
`gate_decision.source == "empty_vault"` + English output).

Default capacity 8 (`MAX_THREAD_TURNS`). Oldest summaries evict in
FIFO order. Frozen `TurnSummary` dataclass; never mutated post-push.

### P3.2 — Anaphora composer (`chat/anaphora.py`)

`thread_anaphora_prefix(ctx, subject, intent_name, source) → str | None`.
Returns a deterministic backreference when:

- The current turn is pack/teaching grounded.
- A prior pack/teaching turn on the same subject exists in the
  thread context.
- The prior turn's intent differs from the current intent
  (same-intent revisits are redundant; the prior turn IS the
  current surface modulo vault drift).

Prefix shapes (structural-fields-only, no prose):

```
(Recalling turn N: chain <chain_id>.)            # prior was teaching
(Recalling turn N: <subject> grounded pack.)     # prior was pack
```

Opt-in via `RuntimeConfig.thread_anaphora=False`. Default off
preserves every pre-P3.2 surface byte-identically.

### P3.3 — NARRATIVE intent (`chat/narrative_surface.py`)

New `IntentTag.NARRATIVE`. Classifier patterns:

```
^tell\s+me\s+about\s+
^describe\s+
^what\s+(?:can|do)\s+you\s+(?:say|know)\s+about\s+
```

Registered BEFORE `^what\s+(?:is|are)\s+` so the more specific
patterns win.

Composer: `narrative_grounded_surface(subject_lemma, max_clauses=4)`.
Walks every reviewed chain rooted on X across all registered teaching
corpora, dedupes by (connective, object), sorts by (intent, connective,
object) for replay stability, emits up to `max_clauses` clauses.

Surface format:

```
"{X} — narrative-grounded ({corpus_ids}): {dX1}; {dX2}.
 {X} {conn1} {O1} ({dO1}); {X} {conn2} {O2} ({dO2}). No session
 evidence yet."
```

Tagged `grounding_source="teaching"` — narrative surfaces are
reviewed-corpus content, same provenance tier as
`teaching_grounded_surface`.

### P3.4 — EXAMPLE intent (`chat/example_surface.py`)

New `IntentTag.EXAMPLE`. Classifier patterns:

```
^(?:give|show)\s+(?:me\s+)?an?\s+(?:example|instance)\s+of\s+
^example\s+of\s+
```

Composer: `example_grounded_surface(object_lemma, max_examples=3)`.
Reverse-chain access: walks chains where X is the **object**, not
the subject. Dedupes by subject. Sorts by (intent, subject,
connective).

Surface format:

```
"{X} — example-grounded ({corpus_ids}): {dX1}; {dX2}.
 Example: {subject1} {conn1} {X}; {subject2} {conn2} {X}. No
 session evidence yet."
```

### Cross-cutting

- NARRATIVE + EXAMPLE both fall through to the OOV invitation
  (P2.1) when the subject is unknown — same gradient discipline as
  Phase 2.
- Both composers consult the cross-corpus aggregator from ADR-0064;
  no new ratification required.
- No new pack mutation. No new corpus. Phase 3 is pure surface +
  thread-state work over the Phase 1/2 substrate.

---

## Consequences

### Capability unlocked

| Intent | Pre-Phase-3 | Post-Phase-3 |
|---|---|---|
| `"Tell me about X"` | universal disclosure | multi-clause narrative across corpora |
| `"Give me an example of X"` | universal disclosure | reverse-chain example surface |
| Subject-anaphora across turns | none | opt-in deterministic backreference |

### Live verification

```
> Tell me about truth.
  [teaching] truth — narrative-grounded (cognition_chains_v1):
  cognition.truth; logos.core. truth grounds knowledge (cognition.knowledge);
  truth requires evidence (cognition.evidence). No session evidence yet.

> Give me an example of knowledge.
  [teaching] knowledge — example-grounded (cognition_chains_v1):
  cognition.knowledge. Example: truth grounds knowledge;
  understanding requires knowledge; evidence grounds knowledge.
  No session evidence yet.

> Tell me about mother.
  [teaching] mother — narrative-grounded (relations_chains_v2):
  kinship.parent.female; kinship.parent. mother precedes daughter
  (kinship.child.female). No session evidence yet.

# With thread_anaphora=True, after a teaching turn on "light":
> What is light?
  [pack] (Recalling turn 0: chain cause_light_reveals_truth.)
  light — pack-grounded (en_core_cognition_v1):
  cognition.illumination; logos.core; perception.clarity.
```

### Cognition lane: byte-identical

Phase 3 is additive — every existing intent classifier rule and
composer behaviour preserved.

```
public:  intent 100% / surface 100% / term 91.7% / closure 100%
holdout: intent 100% / surface 100% / term 83.3% / closure 100%
```

---

## Trust boundaries

- **No prose generation.** The anaphora prefix is structural fields
  only (turn_index + chain_id or grounding tier). NARRATIVE and
  EXAMPLE composers emit only pack atoms, chain content, and fixed
  template strings.
- **No new mutation surfaces.** Phase 3 reads the reviewed corpora;
  it never writes.
- **Anaphora is opt-in.** Default `thread_anaphora=False` keeps
  surfaces byte-identical to pre-P3.2.
- **Bounded.** Thread context capped at 8 turns; NARRATIVE capped
  at 4 clauses; EXAMPLE capped at 3 examples. All defaults
  configurable.

---

## Files changed

```
chat/thread_context.py                                   NEW (~165 lines)
chat/anaphora.py                                         NEW (~90 lines)
chat/narrative_surface.py                                NEW (~165 lines)
chat/example_surface.py                                  NEW (~115 lines)
chat/oov_surface.py                                      added NARRATIVE/EXAMPLE
chat/runtime.py                                          wired all three composers + thread push
core/config.py                                           thread_anaphora flag
generate/intent.py                                       NARRATIVE / EXAMPLE enum + patterns
tests/test_thread_context.py                             NEW (20 tests)
tests/test_anaphora.py                                   NEW (12 tests)
tests/test_narrative_example_intents.py                  NEW (30 tests)
docs/decisions/ADR-0066-turn-level-composition.md        NEW (this file)
docs/decisions/README.md                                 ADR-0066 index entry
```

---

## Verification

```
tests/test_thread_context.py                             20 passed
tests/test_anaphora.py                                   12 passed
tests/test_narrative_example_intents.py                  30 passed
Curated lanes (all green):
  smoke 67 / cognition 121 / teaching 17 / packs 6 / runtime 19 / algebra 132
Cognition eval byte-identical.
```

---

## Future ADRs unlocked

- **Anaphora on the walk path.** Today thread anaphora fires only
  when both turns are pack/teaching tier. Extending to vault-path
  turns (the typical mid-session surface) needs a parallel hook
  in the walk return path. Natural follow-up.
- **Multi-intent NARRATIVE composition.** Current NARRATIVE walks
  one corpus dimension. Future work: extend composed-surface
  (ADR-0062) to operate on the NARRATIVE clause set, producing
  "narrative-of-narratives" surfaces.
- **EXAMPLE with hypothetical counterexamples.** Today EXAMPLE
  surfaces only positive corpus chains. Future: when the corpus
  contains contradicting/superseded chains, EXAMPLE can show
  contrast.
