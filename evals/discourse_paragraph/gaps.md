# discourse_paragraph — gaps

## v1 (current)

- Realizer-isolation lane: bypasses runtime grounding so the
  paragraph claim is unconfounded by vault noise.
- Sentence-count window is intentionally generous
  (`max_sentences = min + 2`) to tolerate small wrapping variance
  from compound-clause folding in `realize_target` (CONJUNCTION /
  COMPLEMENT / RELATIVE edges merge two steps into one sentence).
- Subject coverage threshold is 0.75, not 1.0 — exact-coverage
  cases pass that bar comfortably but the slack lets a future
  realizer change ship without rewriting cases.

## Known gaps for v2

1. **No round-trip through the runtime.**  v1 invokes the realizer
   directly with a constructed `ArticulationTarget`.  v2 should
   feed the runtime real text inputs that *produce* the same
   articulation target through `graph_from_intent` +
   `plan_articulation`, end-to-end.
2. **No anaphora / pronoun reduction.**  Every sentence carries
   its subject explicitly.  Pronominalisation deferred.
3. **No length scaling above 5 sentences.**  v2 should push to
   10/20/50 sentences and measure per-sentence determinism.
4. **No grammaticality check per sentence.**  v1 checks subject
   coverage + discourse markers; v2 should run each emitted
   sentence through grammatical_coverage's rubric.

## Why this lane exists

First lane that exercises paragraph-scale output.  Every previous
fluency lane (Phase 5.1 + 5.4–5.7) operates on 3-word SVO probes.
The structural capability — folding multiple articulation steps
into a coherent paragraph with deterministic discourse markers —
was already in the realizer; this lane makes it measurable.
