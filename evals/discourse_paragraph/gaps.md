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

## Status: v2 partially shipped

- **Length scaling (was gap 3 — resolved):** `public/v2` exercises
  10 / 20 / 50-sentence cases.  All three pass at 100% with bit-
  identical replay.  First lane to push paragraph output past five
  sentences.
- **Per-sentence grammaticality (was gap 4 — resolved):** runner adds
  `_check_per_sentence_grammar` gated on `require_per_sentence_grammar`
  case field.  Per case: each emitted sentence must be non-empty,
  contain ≥ 3 whitespace tokens, start with an uppercase letter, and
  (when `align_steps_to_sentences` is set) contain the aligned step's
  subject.  Lane reports `per_sentence_grammar_pass_rate`.

## Remaining v3 gaps

1. **Runtime round-trip — partial (single-sentence only).**  v2
   adds round-trip cases (`mode: "runtime_roundtrip"`) that prime
   the vault, ask a question through `ChatRuntime.chat`, and verify
   the articulation surface is well-formed, capitalized, contains
   an expected token, and is bit-identical across two fresh runtime
   instances.  Three cases pass at 100%.  But the runtime/planner
   currently produces one sentence per turn — the
   multi-sentence-from-runtime claim still requires a planner
   extension (e.g. expanding a single user question into a
   multi-step `ArticulationTarget` via graph traversal).  That is
   the real v3 gap.
2. **No anaphora / pronoun reduction.**  Every sentence carries
   its subject explicitly.  Pronominalisation deferred.
3. **No cross-sentence grammatical_coverage rubric.**  The v2
   per-sentence check is structural (length, capitalization, subject
   alignment); it does not run each sentence through
   `evals/grammatical_coverage`'s constraint rubric.  Reuse should
   be straightforward once a sentence-to-constraint mapping is
   designed.

## Why this lane exists

First lane that exercises paragraph-scale output.  Every previous
fluency lane (Phase 5.1 + 5.4–5.7) operates on 3-word SVO probes.
The structural capability — folding multiple articulation steps
into a coherent paragraph with deterministic discourse markers —
was already in the realizer; this lane makes it measurable.
