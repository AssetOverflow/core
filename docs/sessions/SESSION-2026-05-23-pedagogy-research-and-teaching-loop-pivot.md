# SESSION 2026-05-23 — Pedagogy Research & Teaching-Loop Potential Pivot

**Date:** 2026-05-23
**Status:** Research note; load-bearing for ADR-0129 + ADR-0130
**Trigger:** Operator-supplied review of *Beyond Traditional Pedagogy:
Research-Based and Emergent Techniques for Deep, Durable Learning*
(`/Users/kaizenpro/Downloads/Beyond Traditional Pedagogy ...md`,
2026-05-23)
**Branch:** `docs/pedagogy-review-and-teaching-backlog`

---

## Why this session exists

CORE's mid-2026 work has concentrated on the GSM8K-math substrate arc
(ADRs 0114a → 0119 → 0120 → 0121 → 0122 → 0123 / 0123a / 0123b → 0126
candidate-graph topology → 0127 units pack → 0128 numerics pack). The
last three substrate ADRs each produced **zero sealed-holdout lift**
despite being correct work, leading to an architectural pivot (ADR-0126)
and a substrate-substrate (ADR-0127 / 0128) reframing.

That sequence has been **all about the truth-articulation path** —
parse → graph → solve → verify → realize. The orthogonal axis — how
CORE *learns* from reviewed corrections — has not received the same
load-bearing attention since the ADR-0040-series teaching-substrate
work. The operator surfaced a pedagogy literature review as a sanity
check on whether the teaching loop, considered on its own merits,
has structural gaps that the GSM8K-math focus has been deferring.

This session is the result of that check: the literature review of
the supplied document, follow-up confirmation research on contested
claims, and the resulting two backlog ADRs (0129 and 0130).

---

## The reviewed document

**Title:** *Beyond Traditional Pedagogy: Research-Based and Emergent
Techniques for Deep, Durable Learning*

**Structure:** Executive summary + ~10 themed sections + a
synthesis table + 22 reference URLs. ~300 lines, well-cited within
the established cognitive-psychology / learning-science canon
(Bjork, Roediger & Karpicke, Kapur, Mayer, Collins / Brown / Newman,
Freeman et al., etc.).

**Headline claims:**

1. Active learning > passive lecture (Freeman et al. 2014 PNAS
   meta-analysis as exemplar).
2. Retrieval practice (effortful recall) drives durable learning;
   spacing + interleaving amplify.
3. Productive failure (Kapur) produces larger conceptual gains than
   instruction-first ("3x" rhetoric in some references).
4. Embodied cognition: gesture, manipulation, handwriting matter for
   acquisition.
5. Multimedia learning (Mayer): coordinated verbal + visual channels
   subject to cognitive-load management.
6. Cognitive apprenticeship (Collins / Brown / Newman): modeling,
   coaching, scaffolding, articulation, reflection, exploration.

**Treatment quality:** sound at the survey level; weak on
calibration of contested findings.

---

## Literature confirmation pass

To avoid uncritical adoption, three areas with known replication
or boundary concerns were searched against 2024–2025 literature:

### 1. Productive failure — calibration of the "3x" rhetoric

**Anchor:** Sinha & Kapur 2021 meta-analysis (166 experimental
comparisons, ~12,000 participants), [SAGE](https://journals.sagepub.com/doi/full/10.3102/00346543211019105).

| Claim | Reality |
|-------|---------|
| "3x conventional gains" | Headline from high-fidelity PF studies; meta-analysis average is **d = 0.36**, rising to **d = 0.58** at high design fidelity. Real but more modest. |
| "Broadly applicable" | **Largely a STEM finding.** Non-STEM evidence scarce; domain-general skill transfer not supported. |
| "Works for all learners" | Better effects for **older students** (secondary onwards); prior knowledge is a strong moderator (PMC 2023 study on prior math achievement). |

**Verdict for CORE:** PF is the doc's most-overstated technique.
The structural analog inside CORE (let-attempt-then-review)
already exists in adversarial generation (ADR-0119.5), but with
a different mechanism — adversarial generation is a wrong-answer
*rejection* tool, not a learning-from-attempt tool. Adopting PF
shape inside CORE would mean intentionally allowing the engine
to attempt with knowingly-insufficient grounding and learning
from the gap. **This is the deliberate inverse of CORE's
`wrong==0` doctrine** and would require structural justification
beyond "the literature supports it."

### 2. Retrieval practice — transfer limits

**Anchor:** Pan & Rickard 2018 transfer meta-analysis;
Cognitive Research 2024 follow-up on far-transfer mechanisms,
[Cognitive Research](https://cognitiveresearchjournal.springeropen.com/articles/10.1186/s41235-024-00598-y).

| Claim | Reality |
|-------|---------|
| "Retrieval drives transfer" | **Near transfer: yes (d = 0.4). Far transfer: weak/null (Pan & Rickard d = 0.16, n.s.).** |
| "Works for complex material" | Strongest for simple materials learned by rote; complex / educationally relevant materials show smaller, more contingent effects. |
| "Universal mechanism" | Recent work (Cognitive Research 2024): far-transfer benefits appear specifically when **rule-based learning** is the underlying mechanism + after delay. |
| "Lecture-hall ecological validity" | Glaser & Richter 2025 ([Teaching of Psychology](https://journals.sagepub.com/doi/10.1177/00986283231218943)): testing effect transfers poorly to studied-but-not-practiced content. |

**Verdict for CORE:** Retrieval practice IS the most robust
finding *for retention of practiced material*. CORE's vault recall
already encodes the exact-recall ceiling of this technique. The
*spaced-retrieval* extension (spacing across time) is the part
not currently modeled in CORE's teaching loop — see ADR-0129.

### 3. Embodied cognition — replication crisis

**Anchor:** Machery 2024 chapter on the embodied-cognition
replication crisis,
[Routledge Handbook of Replication](https://www.taylorfrancis.com/chapters/edit/10.4324/9781003322511-50/replication-crisis-embodied-cognition-research-edouard-machery);
Frontiers in Education 2026 STEM-learning integrative review,
[Frontiers](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1811569/full).

| Claim | Reality |
|-------|---------|
| Embodied learning effects | **Known replication crisis.** Foundational findings have failed independent replication. |
| Handwriting > typing | Strongest for very early literacy acquisition; broader generalizations are contested. |
| Universal benefit | "Embodiment sometimes facilitates learning and sometimes does not" — boundary conditions matter (Frontiers 2026). |

**Verdict for CORE:** Not applicable directly (no body, no
sensorimotor system). Structural analogs (e.g., the
algebra/field/vault substrate as "grounding in a non-symbolic
representation") exist but the analogy is too weak to load-bear
design decisions.

---

## What the doc missed (frameworks worth knowing)

These should be on the radar even though they weren't in the
reviewed document:

| Framework | Why it matters |
|-----------|----------------|
| **Worked-example effect** (Sweller, Paas, van Merriënboer) | Strong evidence for novice instruction; counter-evidence for experts (see expertise-reversal) |
| **Expertise-reversal effect** | Techniques that help novices actively hurt experts and vice versa. Directly relevant to CORE's `apprentice → audit-passed → expert` promotion contract (ADR-0120) |
| **Cognitive load theory** (Sweller) | Distinct intrinsic / extraneous / germane load distinction. Operationally useful for designing teaching corpora |
| **Deliberate practice** (Ericsson) | Specific goals + immediate feedback + repetition at the edge of capability. Better lens than "active learning" for skill domains |
| **Self-explanation effect** (Chi) | Narrow but strong evidence, particularly for science learning from worked examples |
| **Bloom's 2-sigma problem** (1984) | Unsolved benchmark: 1:1 tutoring delivers ~2 SD gains over conventional instruction. Most "evidence-based" techniques are attempts to approach this asymptote without the staffing cost |
| **Feedback science** (Hattie & Timperley 2007; Wisniewski et al. 2020) | Type / timing / specificity of feedback dominate effect sizes |
| **Pre-testing effect** (Carpenter, Richland) | Testing *before* studying primes attention. Distinct from retrieval practice |

---

## Cross-walk to CORE architecture

This is the load-bearing section: not "what does the literature
say" but "what does the literature say that maps onto a structural
move CORE could make."

| Pedagogy concept | CORE analog | Status |
|------------------|-------------|--------|
| Retrieval practice | `teaching/correction.py` + vault recall | **Structurally aligned.** Every reviewed correction IS a retrieval+strengthen event. Exact-recall ceiling already met. |
| Spaced retrieval | (none) | **Genuine gap.** No deterministic spaced re-verification of past corrections. → ADR-0129 |
| Interleaving | Cross-pack chains (ADR-0064 / 0067) | **Aligned.** Cross-pack chains force discrimination across domains. |
| Metacognition / calibration (prediction vs outcome) | (none at teaching layer; partial at runtime via ADR-0035) | **Genuine gap.** No prediction-vs-outcome capture in teaching loop. → ADR-0130 |
| Cognitive apprenticeship | Ratified packs as articulated expert ontology | **Strong analog.** Packs ARE the encoded expert representation; ratification IS the "fade scaffolding" step. |
| Worked examples → fading | Teaching corpora → unsupervised generation | **Partial.** Corpora encode correct answers; less so the reasoning chain that produced them. Could be more first-class. |
| Productive failure | Adversarial generation (ADR-0119.5) | **Different mechanism.** Adversarial generation is rejection; PF would mean attempt-before-grounding. Inverse of `wrong==0`. Not recommended for direct port. |
| Pre-testing | (none) | Genuine gap. CORE always grounds before articulating; never the reverse. Adopting would conflict with `wrong==0`; not recommended. |
| Self-explanation | `SolutionTrace` provenance chain | **Structurally present.** Every answer has its derivation. Could be more first-class in teaching-store records. |
| Cognitive load theory | Substrate hierarchy: algebra → field → vault → realizer | **Implicit alignment.** CORE's layering matches CLT separation of intrinsic structure from extraneous load. |
| Expertise reversal | Pack-tier promotion (ADR-0120) | **Already encoded.** The `apprentice / audit-passed / expert` contract already knows that what helps an apprentice can ossify an expert. |
| Desirable difficulties | `wrong == 0` discipline | **Inverse mapping.** CORE refuses *undesirable* difficulty (confabulation under uncertainty). A teaching-side concept of *desirable* difficulty (challenging-but-not-impossible curriculum sequencing) is not yet first-class. |
| Feedback science | `teaching/review.py` | **Partially aligned.** Reviewed corrections ARE structured feedback. Timing / specificity dimensions could be more first-class. |

---

## The two structural gaps worth addressing

Distilled from the cross-walk, two design moves are both
*pedagogically supported by robust literature* AND *consistent
with CORE's existing determinism + provenance discipline*:

### Gap 1 — Spaced reviewed-correction replay
**Mapped to:** retrieval-with-spacing literature (most robust
finding).
**ADR:** [ADR-0129](../decisions/ADR-0129-spaced-correction-replay-deferred.md)
**Status:** Deferred.
**Summary:** Periodic deterministic re-run of past reviewed
corrections to verify they still produce intended outcomes
under current state. Defense against silent regression as the
correction store and pack set evolves.

### Gap 2 — Pre-articulation calibration logging
**Mapped to:** metacognitive calibration / prediction-outcome
comparison literature.
**ADR:** [ADR-0130](../decisions/ADR-0130-pre-articulation-calibration-deferred.md)
**Status:** Deferred.
**Summary:** When a correction is proposed, log CORE's
pre-correction prediction; on acceptance, emit the gap.
Provides empirical answer to "is CORE actually getting better"
across pack-version cohorts; supports operator triage.

---

## What is NOT proposed (and why)

| Considered | Rejected because |
|------------|------------------|
| Adopt productive-failure mechanism inside CORE | Inverse of `wrong==0`; would require structural justification beyond pedagogy literature. Adversarial generation (ADR-0119.5) covers the related "wrong-answer rejection" use case without the conceptual conflict. |
| Adopt pre-testing in articulation | Same conflict with `wrong==0`. CORE grounds before articulating by design. |
| Add embodied / sensorimotor layer | No body. The structural analogy (substrate as "grounding") is too weak to load-bear. |
| Add peer-learning multi-agent loop | Out of scope. Multi-agent coordination is a separate architectural question; not driven by this pedagogy review. |
| Adopt cognitive-load-theory load-balancing in realizer | Already implicit in the substrate hierarchy. Making it more explicit risks decoration without integration. |

---

## Why both ADRs are deferred, not accepted

Both ADR-0129 and ADR-0130 are **proposed but deferred**, following
the established ADR-0121 / ADR-0122-deferred pattern. The deferral
reasons compose:

1. **Path-B uncertainty.** The active GSM8K-math arc
   (ADR-0126 / 0127 / 0128) may resolve to a benchmark
   re-targeting. If so, the correction-store population
   characteristics change, and the right cadence (ADR-0129) /
   cohort structure (ADR-0130) may differ.
2. **No observed incident.** Neither ADR has a triggering
   incident. They're defensive infrastructure — useful if a
   regression occurs (0129) or calibration drift develops (0130),
   but speculative without that evidence.
3. **Cost/benefit unmeasured.** Both add telemetry volume and
   operator review surface. Worth it only if the signal proves
   load-bearing.
4. **Composition argument.** If either is un-deferred, the other
   should be re-evaluated jointly — spaced-replay events
   naturally yield calibration evidence; the two share
   infrastructure. Deferring both together preserves that
   composition.

The exit criteria for un-deferral are documented in each ADR's
"Exit criteria for un-deferral" section.

---

## Sequencing recommendation

1. Land ADR-0126 (PR #161) — architecture.
2. Land ADR-0127 (Gemini in flight) — units pack.
3. Land ADR-0128 (Opus #2 in flight) — numerics pack.
4. Re-run train sample with both packs mounted → real Path-A vs
   Path-B verdict.
5. If Path A: continue along the math expert promotion path.
   ADR-0129 / 0130 remain deferred until an incident or
   bandwidth pressure surfaces them.
6. If Path B: benchmark re-targeting becomes the work; ADR-0129 /
   0130 may become more relevant if the new benchmark's
   correction-store characteristics are different enough to
   warrant proactive verification.

---

## Reference list (additional to the original document)

- Sinha, T. & Kapur, M. (2021). When Problem Solving Followed by
  Instruction Works: Evidence for Productive Failure.
  [SAGE](https://journals.sagepub.com/doi/full/10.3102/00346543211019105)
- Pan, S. C. & Rickard, T. C. (2018). Transfer of test-enhanced
  learning: meta-analytic review and synthesis. *Psychological Bulletin*.
- Glaser, J. & Richter, T. (2025). The Testing Effect in the
  Lecture Hall: Does it Transfer to Content Studied but Not
  Practiced? [Teaching of Psychology](https://journals.sagepub.com/doi/10.1177/00986283231218943)
- Cognitive Research: Principles and Implications (2024). Far
  transfer of retrieval-practice benefits: rule-based learning
  as the underlying mechanism.
  [Springer](https://cognitiveresearchjournal.springeropen.com/articles/10.1186/s41235-024-00598-y)
- Machery, E. (2024). The Replication Crisis in Embodied Cognition
  Research. *Routledge Handbook of Replication*.
  [Taylor & Francis](https://www.taylorfrancis.com/chapters/edit/10.4324/9781003322511-50/replication-crisis-embodied-cognition-research-edouard-machery)
- Frontiers in Education (2026). Embodied cognition in STEM
  learning: an integrative review.
  [Frontiers](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2026.1811569/full)
- Sinha & Kapur (2023). Prior math achievement and inventive
  production predict learning from productive failure.
  [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10185511/)
- Bloom, B. S. (1984). The 2 Sigma Problem.
  *Educational Researcher 13(6)*.
- Hattie, J. & Timperley, H. (2007). The Power of Feedback.
  *Review of Educational Research 77(1)*.
- Wisniewski, B., Zierer, K., Hattie, J. (2020). The Power of
  Feedback Revisited: A Meta-Analysis.
- Ericsson, K. A., et al. (1993). The Role of Deliberate Practice
  in the Acquisition of Expert Performance.
  *Psychological Review 100(3)*.
- Sweller, J., van Merriënboer, J. J. G., Paas, F. G. W. C. (1998).
  Cognitive Architecture and Instructional Design.

---

## Open questions surfaced (not resolved this session)

These are noted for future sessions; not items I'm advocating
for action:

1. **Should teaching-corpus records carry "why" structure, not
   just "what"?** Self-explanation literature suggests reasoning
   chains in corpora may be more useful than answers alone.
   `SolutionTrace` already exposes provenance; pushing this into
   teaching corpora is a separate question.
2. **Is there a deliberate-practice analog at the curriculum
   level?** ADR-0120's promotion contract already encodes
   "stretch-but-pass" structure (correct_rate ≥ 0.60 floor).
   Whether sub-curricula should also encode this is open.
3. **Could the pack-mutation-proposal pathway adopt a worked-
   example pattern?** When a pack mutation is proposed, today
   the operator sees the diff; could they also see a small
   worked example showing the behavioral implication?
   Speculative.
4. **Is Bloom's 2-sigma a meaningful target for CORE?** A
   deterministic engine with exact recall has structural
   properties that may exceed 1:1 tutoring on some axes
   (consistency, replay) while underperforming on others
   (adaptation, social affordances). Whether to claim this
   target is an architectural framing question, not a
   technical one.

---

## End-of-session state

- **ADRs added:** 0129 (deferred), 0130 (deferred).
- **Session note:** this file.
- **Branch:** `docs/pedagogy-review-and-teaching-backlog`.
- **PR plan:** single docs-only PR for the three files; lands
  independently of the in-flight ADR-0126 / 0127 / 0128 chain.
- **No code changes.** No regression risk.
