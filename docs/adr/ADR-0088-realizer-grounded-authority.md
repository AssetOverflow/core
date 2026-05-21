# ADR-0088 — Realizer-Grounded Authority (Finding 2 retry)

**Status:** Proposed
**Date:** 2026-05-20
**Author:** Shay
**Supersedes:** none
**Supersedes attempts:** `fix/ground-graph-wiring` (reverted; not landed)
**Related:** ADR-0046 (forward graph constraint), ADR-0047 (wire forward constraint), ADR-0048 (pack-grounded surface), ADR-0085 (gloss content style pass), PR #76 (surface authority resolver)

---

## Context

The 2026-05-20 second-opinion audit identified that `CognitiveTurnPipeline.run()` calls `realize_semantic(target, graph)` on **every turn** but never calls `ground_graph(graph, recalled_words)` first. Every non-COMPARISON, non-CORRECTION node in the `PropositionGraph` is born with `obj = "<pending>"`. The realizer therefore renders surfaces like `"Truth is defined as ..."` which `_is_useful_surface()` correctly rejects.

The graph is structurally sound but never grounded in the hot pipeline path, so the realizer is perpetually firing blanks. The audit's first-response remedy was to wire `ground_graph` in and let the realizer become a real surface authority. The audit's final-draft remedy retreated to a hot-path short-circuit (skip the dead computation when the teaching store has no relevant triple).

**Empirical attempt (`fix/ground-graph-wiring`, 2026-05-20).** The first-response remedy was implemented — `ground_graph` was wired between `runtime.chat` and `realize_semantic`, with recalled words sourced from a new `ChatResponse.recalled_words` field populated from the alphabetic walk-token filter. The change passed `core eval cognition` (byte-identical metrics across all three splits) but broke 23 byte-identical tests in `tests/test_realizer_guard_holdout.py`, `tests/test_register_invariant_grounding.py`, `tests/test_pack_glosses_content.py`, and `tests/test_warmed_session_lane.py`.

Inspection of a single failure reveals the root cause:

| Expected (runtime, post-ADR-0085) | Actual (grounded realizer) |
|---|---|
| `Light is a source of revelation that makes things knowable.` | `Light is a visible medium that **reveal** truth.` |

The grounded realizer **does** produce real content (no `<pending>` / `...` markers) — but its templates lack the runtime path's ADR-0085 gloss content-style pass, so the output carries grammar bugs (subject-verb disagreement here) and weaker phrasing. The realizer wins the surface resolver (introduced in PR #76) because it now passes `_is_useful_surface`, and the user-visible surface regresses.

This is not a wiring bug. It is a **layering inversion**: today the runtime path (`articulate_with_intent` + `pack_grounded_surface` + ADR-0085 fluency) is the only source that has been polished. Making the realizer a real authority before its templates match that fluency standard is a user-visible regression even when groundedness is preserved.

The change was reverted; the branch was never pushed.

---

## Decision

ADR-0088 reframes Finding 2 as a **two-phase rollout** instead of a single wiring change.

### Phase A — Realizer fluency parity (prerequisite, no behavior change)

Before the realizer is allowed to be a surface authority, its templates must produce surfaces that are at least as fluent as the runtime's pack-grounded path. Specifically:

1. **Gloss-aware realizer templates.** `realize_semantic` (and its template library in `generate/templates.py` / `semantic_templates.py`) must consult the same gloss source ADR-0085 wired into the CAUSE composer — `lemma.gloss` from the cognition pack manifest — and prefer gloss-derived phrasing over the current bare-template phrasing when a gloss exists for the subject lemma.
2. **Subject-verb agreement.** The realizer must emit a 3sg verb form when the subject is a 3sg noun. Today's templates leak the lemma form (`reveal` for plural-or-bare) into 3sg subject contexts (`a visible medium that reveal truth`). This is the same fix ADR-0085 / PR #75 made on the content-style pass for glosses; the realizer must inherit it.
3. **Pack-provenance tag parity.** The runtime path appends `pack-grounded (en_core_cognition_v1).` to the surface. The realizer's grounded output must carry the same tag, drawn from `intent.subject`'s resolving pack via the same resolver the runtime path uses.

Phase A is **byte-identical** by construction: it touches realizer templates but the realizer is still gated by `_is_useful_surface` on `<pending>` markers, so its output is still discarded today. No surfaces change.

### Phase B — Ground the graph and let the realizer compete

After Phase A merges and the realizer's standalone fluency is verified (a new lane that runs `realize_semantic` directly on a primed graph and asserts surfaces match the runtime path's grammar / gloss / provenance shape):

1. Add `recalled_words: tuple[str, ...] = ()` to `ChatResponse`, populated from the alphabetic walk-token filter inside `ChatRuntime._chat` (same source `articulate_with_intent` already uses).
2. Reorder `CognitiveTurnPipeline.run()`:
   - keep `graph_from_intent` + `plan_articulation` before `runtime.chat`,
   - call `runtime.chat` next,
   - call `ground_graph(graph, response.recalled_words)` between chat and realization,
   - call `realize_semantic(target, grounded_graph)`,
   - resolver (PR #76) selects among the now-real candidates.
3. Re-baseline the 23 byte-identical tests against the new (fluent) realizer surfaces, and re-pin `test_register_invariant_grounding::test_trace_hash_invariant_across_registers` for the post-grounding trace_hash.

Phase B is **substantive** — surfaces change — but every changed surface must clear a new invariant: "fluency ≥ pre-fix runtime surface on the same prompt." A regression dashboard pairs the pre- and post-grounding surface per case and a reviewer signs off before re-baselining.

### Out of scope

- The audit's final-draft remedy (hot-path short-circuit only) is **rejected**. It delivers no metric lift since `core eval cognition` already scores 100% groundedness across every split, and the dead computation is fast (a few µs per turn). Short-circuiting purely for perf is not load-bearing under CLAUDE.md's "small, load-bearing PRs" doctrine.
- Cross-pack realization (the realizer consulting `en_core_relations_v1` glosses for a `family.parent` proposition) is deferred to a later ADR.

---

## Consequences

- **Realizer becomes a real authority for the first time** (Axiom 3 + Axiom 5 honored — propagation-over-mutation, articulation-from-grounded-propositions).
- **One forward pass, one correction pass** (Axiom 4) — the three-way surface race PR #76 named is fully resolved because both candidates the resolver picks among are now substantively meaningful.
- **Trace-hash invariant moves once** — a single re-baseline at Phase B merge. After that, the post-grounding trace_hash is the new permanent invariant.
- **Realizer template surface area widens** — ADR-0085's content-style pass becomes load-bearing on a second consumer (the realizer), so future content-style work has to update both call sites.

---

## Rejected alternatives

1. **Land Phase B without Phase A.** Empirically attempted on `fix/ground-graph-wiring`; produces user-visible fluency regressions on 23 cases. Rejected.
2. **Land the hot-path short-circuit only** (audit's final draft). Pure perf cleanup, no metric lift, not load-bearing. Rejected.
3. **Gate Phase B behind a `RuntimeConfig.realizer_grounded_authority: bool = False` flag.** Defers the decision rather than resolving it; cognition eval at 100% groundedness means the flag would never flip in practice and the realizer stays a placeholder. Rejected — the right shape is to land Phase A unconditionally and then flip Phase B with a clean re-baseline.

---

## Validation gate

Phase A merge must demonstrate:

- Every existing byte-identical surface test still passes.
- A new lane `tests/test_realizer_fluency_parity.py` runs `realize_semantic` directly on a manually-grounded graph for every cognition eval case and asserts surfaces match `^[A-Z][^<>]+\\.\\s*pack-grounded \\(.*\\)\\.$` (no `<pending>`, no `...`, leading capital, ends with `.`, carries provenance tag, subject-verb agreement).

Phase B merge must demonstrate:

- All three `core eval cognition` splits at ≥ MEMORY baselines.
- The re-baselined 23 surface tests pass with a per-case justification comment naming the new fluency contract.
- A new trace-hash invariant for the post-grounding `register_invariant_grounding` test, with a one-line ADR-0088 reference in the assertion.
