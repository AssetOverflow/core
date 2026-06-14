# Finding: the speculative epistemic ceiling does NOT blunt learning

**Date:** 2026-06-14
**Status:** substrate finding (refutes a compelling-but-wrong intuition; corrects
the "B1 coherent-promotion" plan). Method: 7-agent architecture audit + adversarial
verification (run `wf_f7c37d46-16f`).
**TL;DR:** All cognition/logos pack entries are `speculative`, and the engine's
`determine` path can never label a conclusion `verified` — but **neither fact
blunts learning**. The speculative state is an *honesty/disclosure* mechanism, by
design, and the reasoning/learning loop is blind to it. The plan to "promote
entries to coherent so the model can learn" is unwarranted; the lexicon variant is
purely cosmetic and the fact variant risks manufacturing false `verified`.

## The question

Audit found 25/28 packs have no `epistemic_status` (→ default `speculative`), and
`generate/determine/determine.py::_basis` only returns `"verified"` when every
ground is `coherent`. Hypothesis: this caps the model and is why it underperforms
at learning from contemplation/practice. **Tested rigorously. Refuted.**

## What is actually true (verified, high confidence)

### Axis A — promoting a *lexicon* entry to coherent is compile-and-display-only
- `language_packs/compiler.py:75-92` maps a `coherent` lexical row → `EpistemicState.DECODED`,
  stored per-surface on the manifold (`compiler.py:357` → `vocab/manifold.py:114`).
- **No reasoning/recall/realize/learning path reads that tag.** The only non-test
  reads (`compiler.py:406`, `:559`) merely copy it forward; `workbench/logos.py`
  reads it for the Studio audit badge (display).
- The runtime's per-turn epistemic state comes from **`grounding_source`**, not the
  lexical row: any pack-resolved lemma → `grounding_source="pack"`
  (`chat/pack_grounding.py:461,489`) → `DECODED`
  (`core/epistemic_state.py:133-144`). So a `speculative` and a `coherent` pack
  lemma are **runtime-indistinguishable.** *(Adversarially upheld; no counterexample.)*

### Axis B — every realized fact is `SPECULATIVE` by construction
- Told facts: `generate/realize/realize.py:217` (`status = EpistemicStatus.SPECULATIVE`,
  "COHERENT is never a default (ADR-0021)"). Derived facts: `realize.py:372`. Also
  `generate/proposition.py:264`, `generate/realize/quantitative.py:108`.
- `determine._basis` (`determine.py:88-91`) gates `verified` on those `RealizedRecord`
  grounds — never the lexicon. So lexicon promotion can never reach it.

### Axis C — three coherence-promoters exist; all are dormant at runtime
1. **Proof-carrying (ADR-0218):** `teaching/proof_promotion.certify_promotion` +
   `vault/store.py:417,486-507 apply_certified_promotion` (flips `COHERENT` at :507).
   **Built, sound, independently-re-verified, fail-closed — zero runtime callers**
   (only tests + `demos/proof_carrying_promotion`).
2. **Energy-policy (ADR-0148):** `vault/store.py:361 promote_eligible_entries`,
   wired into the live turn boundary (`chat/runtime.py:2324,2509`) but
   **default-off** (`config.vault_promotion_enabled = False`). Promotes on energy
   cooling, not coherence/entailment.
3. **Curator review:** `teaching/review.py:274` runs live on correction turns but its
   `epistemic_status` is a passed-in param defaulting `SPECULATIVE`; the live call
   sets no status. Computes no coherence.
- So `verified` is genuinely unreachable at runtime — **by deliberate conservatism,
  not a bug.** `pipeline.py:379`'s `COHERENT` proposal branch is dead relative to the
  live path.

### Axis D — the learning loop is blind to `epistemic_status` (decisive)
- `generate/realize/recall.py:19-62 recall_realized` **ignores `epistemic_status`
  entirely.** `SPECULATIVE` consolidated facts are immediately re-readable as
  premises, so deductive closure **climbs to fixed point with the speculative
  ceiling fully in place.** The ceiling does **not** impede chaining or learning.
- The `verified`/`as_told` distinction is **observational only** — it selects a
  surface string (`render.py:31`) and gates nothing else.
- Intentional and sound: `consolidate.py:22`, `realize.py:331-334` — "a sound
  inference never upgrades the standing of its speculative premises." `idle_tick`
  and contemplation are proposal-only/SPECULATIVE by construction
  (`consolidate.py:21-22`, `runtime.py:871`).

## Conclusion

- **The all-speculative state is not why the model struggles.** The learning loop
  works (monotone climb to deductive closure) regardless of it. The real learning
  wall is elsewhere (recognizer/coverage), not epistemics.
- **Do not promote entries to coherent "to help learning."** The lexicon variant is
  cosmetic (no runtime consumer); the fact variant would make speculative content
  admissible-as-evidence — a **wrong=0 hazard** (false `verified`) — for zero
  learning benefit.
- The **only genuine epistemic lever** is wiring the proof-carrying promotion path
  (Axis C #1) so a deductively-proven derived fact can become coherent → the engine
  could honestly emit `verified` for what it *proved* (vs. was told). That is a real
  honesty/capability upgrade and it is wrong=0-safe (fail-closed, independently
  re-verified) — but it was **deliberately left unwired**, so turning it on is a
  ratified-decision, scoped separately in
  `docs/handoff/proof-carrying-wiring-scope-2026-06-14.md`.

## Cross-references
ADR-0021 (epistemic status = revision position), ADR-0218 (proof-carrying
promotion), ADR-0148 (energy-policy promotion), ADR-0206 (epistemic disclosure),
`docs/issues/proof-carrying-coherence-promotion.md`, and the parallel honesty
finding `docs/analysis/holonomy-resonance-proof-not-robust-2026-06-14.md`.
