# SESSION 2026-05-27 — Tier 3 sequencing, eval-surface discipline, the ADR-0166 principle

**Participants:** Shay, Claude (orchestrator), an earlier strategic-analysis agent (external)
**Outputs:** [ADR-0166 — Measurement-Capability Sequencing Discipline](./ADR-0166-measurement-capability-sequencing.md)
**Anchor:** [[thesis-decoding-not-generating]]

---

## What triggered the session

The operator shared a substantive strategic analysis from another
agent. That analysis surveyed CORE's current eval surface, identified
that the Tier 3 learning-curve lanes (`multi_step_reasoning`,
`symbolic_logic`, `cross_domain_transfer`,
`zero_code_domain_acquisition`, `compositionality`,
`inference_closure`) are all TBD, and proposed a four-phase plan to
advance general capability:

1. **Phase 1 (immediate):** Run all existing Tier 3 lanes; populate
   the TBD rows.
2. **Phase 2 (architectural):** Build the missing structural-pattern
   recognizer + cross-subdomain transfer operator named in
   `evals/cross_domain_transfer/gaps.md`.
3. **Phase 3 (parallel to Phase 2):** Expand the OOD eval surface
   (chemistry, propositional logic data, historical sequence,
   geometry, multi-step causal, analogical).
4. **Phase 4:** External benchmarks (ARC, BBH subset, GPQA-Diamond).

The analysis declared its single most impactful next commit:
**"run all Tier 3 lanes and fill the TBD rows."**

The operator's question: where does this go — ADR, scope doc, or
something else?

## What the analysis got right

Three load-bearing instincts:

1. **Don't skip to MMLU-Pro or GSM8K-MATH.** Sequence respects
   CORE's actual architecture; harder math comes later, after
   structural reasoning is in place.

2. **Geometry-first as strategic bet.** CGA gives CORE a structural
   advantage in spatial reasoning that no transformer has.
   Author the operator that produces the advantage, and chase the
   moat instead of the leaderboard. This was the sharpest call.

3. **TBD rows are data debt.** A measurement table full of TBD
   plateaus the entire diagnostic surface. They need numbers.

## What the analysis missed

Two blind spots, one of them load-bearing.

### Blind spot #1 — GSM8K-math treated as solved

The analysis lists `gsm8k_math` matter-of-factly alongside the OOD
lanes, as if the lane has a real, healthy capability behind it. It
does not. At session start (post #331):

```
gsm8k_math/train_sample/v1:  correct=3  refused=47  wrong=0
exit_criterion:              correct_min=10  →  not passed
```

The comprehension-reader Phase 1 wiring landed (ADR-0164 / #326 /
#331). The measurement confirmed: question-only reader scope cannot
move correct off the baseline because every question-refused case
also has statement-side barriers. Phase 2 (Brief 10, statement-frame
reader) is the load-bearing next dispatch.

Against that backdrop, "the single most impactful next commit is to
run all Tier 3 lanes" reads differently. It is measurement of a
capability surface that has not yet cleared its first gate. The
Tier 3 lanes will refuse uniformly until the math substrate handles
its training set; their TBD rows would be filled with zeros that
don't distinguish "the lane is hard" from "the engine isn't
finished."

### Blind spot #2 — the comprehension-reader pivot isn't in the analysis

ADR-0164 / 0165 landed mid-session. The analysis's call for a
"structural-pattern recognizer" is in significant part what the
comprehension reader's update-rule tables *become* when their
composition generalizes beyond math. The Phase 2 statement reader is
the structural-pattern recognizer — under a different name — that
the cross-domain gaps.md asks for. Authoring a separate
"structural-pattern recognizer" component without checking whether
the reader already is it (or will be, with Phase 2 + Phase 3) risks
duplicating work.

This isn't the analysis's fault — it didn't have the in-session
context. But it means the proposed Phase 2 ("build the missing
component") and the actual in-flight Phase 2 (Brief 10) collide.
The correct read is that Brief 10 IS the cross-domain step the
analysis names, embedded in the comprehension-reader architecture.

## Mid-session finding that sharpened the diagnostic further

While drafting this log, PR #332 (a wrong=0 guard + adapter
hardening pass over the Phase 1 reader) landed its measurement and
produced a deeper diagnostic than the Phase 1 result alone:

> All 47 refused cases either have **incomplete graphs**
> (recognized-but-not-injected statements — ADR-0163 recognizers
> flag the shape but the injector produces structurally incomplete
> output) or **question structures beyond Phase 1 scope** (aggregate
> "they", numeric target values, hypernym units).

The bottleneck is not statement *parsing* per se — it's the
ADR-0163 recognizer **injectors** emitting incomplete data, which
the reader correctly refuses to admit (wrong=0 by construction via
the new guard). Two paths now open:

- **Brief 10 (Phase 2 reader)** — bypass the inadequate injectors
  by replacing statement parsing with the reader's compositional
  rules. This is the long-term destination per ADR-0164.3 §Phase 3.
- **ADR-0163 Phase E injector fixes** — fix the existing recognizer
  pipeline to emit complete graphs. Shorter-term win, but doesn't
  reduce the regex sentence-template surface (ADR-0165 and ADR-0164
  call for eventual deletion).

Brief 10 dominates here. Phase 2 reader fixes the structural
problem; injector patches fix the symptom.

## The honest re-sequence

```
NOW              Brief 10 (Phase 2 statement-frame reader)
                   ↓ measure on gsm8k_math train_sample
                 If correct ≥ 25: architecture proven at scale.
                 If 4–24: name the specific gap → Phase 2.1 sub-brief.
                 If 3:    deeper architectural problem; reassess.

PARALLEL         Run existing Tier 3 lanes ONCE as a snapshot.
(cheap)          Populate the TBD rows with whatever they read at
                 today's capability. Re-run after Phase 2 lands.
                 The snapshot is diagnostic, not strategic.

NEXT             Cross-domain transfer operator (per gaps.md).
                 BUT first verify whether the comprehension reader's
                 Phase 2 / Phase 3 update rules already are this,
                 under a different name. Don't duplicate work that
                 is in flight.

THEN             Geometry path:
                   1. Build CGA → spatial-inference operators.
                   2. Author spatial_geometry_ood.
                   3. Run, measure.
                 In that order. Lane after operator, per ADR-0166.

LAST             External benchmarks (ARC, BBH, GPQA-Diamond).
                 After the reader is genuinely domain-general — not
                 just math — these become reachable targets.
```

## The principle being formalized

The fourth governing principle that came out of this exchange:

> **Build the mechanism, measure the mechanism, then expand scope.**
> Don't expand the eval surface ahead of the capability that
> produces signal on it. Lanes that refuse uniformly generate
> noise, not data — and noise drowns the signal you actually want
> to diagnose by.

This is now ADR-0166 (Measurement-Capability Sequencing Discipline),
sitting alongside ADR-0114a (anti-overfitting) and ADR-0165 (regex
scope rule) as a structural invariant the project enforces by
convention rather than by case-by-case judgment.

The ADR's three-question test mechanizes the principle: every new
eval lane PR answers "does the capability exist?", "has at least one
case admitted?", "will the lane distinguish presence from absence?"
A "no" on any of the three defers the lane until the capability
lands.

## What this session did not decide

- **Which lane authoring follows Phase 2 measurement.** That depends
  on the measurement outcome. If Phase 2 lifts correct ≥ 25, the OOD
  expansion can begin. If not, Phase 2.1 narrows the gap first.
- **Whether the ADR-0163 Phase E injector path is worth doing at
  all.** Brief 10 makes it largely obsolete; the question is whether
  there's enough short-term value to do it in parallel. Defer until
  Brief 10's measurement.
- **The structural-pattern recognizer's exact relationship to the
  comprehension reader.** Audit recommended after Brief 10. If the
  reader IS the recognizer in a different idiom, the
  `cross_domain_transfer/gaps.md` text gets amended; if not, a
  separate component is authored *after* the reader stabilizes.
- **Geometry timeline.** Strategic bet, no timeline. Worth doing
  when the operators are an obvious next move under existing
  architecture; not worth forcing.

## Closing observation

The most useful thing the external analysis did was *not* its
recommended action (run all Tier 3 lanes). It was the question its
existence forced: where is signal, where is noise, where is data
debt, where is wishlist? Sorting those four categories is the
work. Once they're sorted, the next commit is mechanical: build
the next mechanism the data actually needs, in the order the
architecture supports.

The other useful thing — almost incidental — was that the analysis
was unaware of the comprehension-reader pivot. That gap forced us
to articulate why the pivot supersedes a strict reading of the
analysis's Phase 2. ADR-0166 codifies that articulation so it
survives this conversation: capability before measurement,
measurement before expansion, no lane authored ahead of its
operator.

The analysis itself was substantive and worth engaging. The
amendments it required are documented here in the spirit of "we
read it, we adopted what was right, we corrected what assumed
unbuilt capabilities were built." That spirit is what ADR-0166
preserves going forward.
